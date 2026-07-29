param(
    [string]$SourceRoot = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ExpectedGraphifyVersion = "0.9.26"
$ExpectedGraphifyPackage = "graphifyy==$ExpectedGraphifyVersion"
$LocalOutputDirName = ".graphify-local"
$LegacyOutputDirName = "graphify-out"
$Utf8NoBomStrict = [System.Text.UTF8Encoding]::new($false, $true)

function Fail($Message) {
    Write-Error $Message
    exit 1
}

if ($MyInvocation.UnboundArguments.Count -gt 0) {
    Fail "Unsupported parameter or retired Graphify publication interface."
}

function Get-RepoRootFrom($Path) {
    $resolved = if ($Path) { $Path } else { "." }
    $root = (& git -C $resolved rev-parse --show-toplevel 2>$null)
    if ($LASTEXITCODE -ne 0 -or -not $root) {
        Fail "SourceRoot must be a Git repository."
    }
    return [System.IO.Path]::GetFullPath($root.Trim())
}

function Get-RelativePath($Path, $Root) {
    $full = [System.IO.Path]::GetFullPath($Path)
    $base = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    $uriBase = [System.Uri]::new($base + [System.IO.Path]::DirectorySeparatorChar)
    $uriFull = [System.Uri]::new($full)
    return [System.Uri]::UnescapeDataString($uriBase.MakeRelativeUri($uriFull).ToString()).Replace("\", "/")
}

function Assert-PathUnderRoot($Root, $Path, $Purpose) {
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    $candidate = [System.IO.Path]::GetFullPath($Path).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    $rootPrefix = $rootFull + [System.IO.Path]::DirectorySeparatorChar
    if ($candidate -ne $rootFull -and -not $candidate.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        Fail "$Purpose escaped the source repository."
    }
    return $candidate
}

function Invoke-GitChecked($Root, $Arguments, $FailureMessage) {
    $output = (& git -C $Root @Arguments 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail $FailureMessage
    }
    return $output
}

function Get-TrackedSnapshot($Root) {
    $pathsRaw = Invoke-GitChecked $Root @("ls-files", "-z") "Unable to list tracked source files."
    $snapshot = @{}
    foreach ($path in ($pathsRaw -split "`0")) {
        if (-not $path) { continue }
        $fullPath = Join-Path $Root $path
        $snapshot[$path] = if (Test-Path -LiteralPath $fullPath -PathType Leaf) {
            [System.IO.File]::ReadAllBytes($fullPath)
        } else {
            $null
        }
    }
    return $snapshot
}

function Restore-TrackedSnapshot($Root, $Snapshot) {
    foreach ($path in $Snapshot.Keys) {
        $fullPath = Join-Path $Root $path
        $parent = Split-Path -Parent $fullPath
        if ($null -eq $Snapshot[$path]) {
            if (Test-Path -LiteralPath $fullPath) {
                Remove-Item -LiteralPath $fullPath -Force
            }
            continue
        }
        if (-not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        [System.IO.File]::WriteAllBytes($fullPath, [byte[]]$Snapshot[$path])
    }
}

function Get-GraphifyVersion {
    $versionText = (& graphify --version 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail "graphify --version failed. Install $ExpectedGraphifyPackage in an isolated tool environment."
    }
    if ($versionText -notmatch "([0-9]+\.[0-9]+\.[0-9]+)") {
        Fail "Unable to parse Graphify version."
    }
    return $Matches[1]
}

function Assert-GraphifyIgnore($Root) {
    $ignorePath = Join-Path $Root ".graphifyignore"
    if (-not (Test-Path -LiteralPath $ignorePath -PathType Leaf)) {
        Fail "Source repository must contain .graphifyignore."
    }
    $text = Get-Content -LiteralPath $ignorePath -Raw -Encoding UTF8
    $required = @(
        ".git/",
        ".agents/",
        ".codex/",
        ".worktrees/",
        ".graphify-local/",
        "graphify-out/",
        "node_modules/",
        "__pycache__/",
        "credentials.local",
        "equipment_inventory.local.json",
        ".env",
        "*.key",
        "*.pem",
        "*.xlsx",
        "openspec/changes/archive/",
        "logs/",
        "transfer/",
        "raw/"
    )
    foreach ($item in $required) {
        if ($text -notmatch [regex]::Escape($item)) {
            Fail ".graphifyignore is missing required local corpus exclusion."
        }
    }
    return $ignorePath
}

function Assert-OutputIgnored($Root) {
    foreach ($path in @("$LocalOutputDirName/", "$LegacyOutputDirName/")) {
        & git -C $Root check-ignore --quiet -- $path
        if ($LASTEXITCODE -ne 0) {
            Fail "Git ignore policy must ignore $path."
        }
    }
}

function Reset-LocalOutput($Root) {
    $outputRoot = Assert-PathUnderRoot $Root (Join-Path $Root $LocalOutputDirName) "Local output path"
    if (Test-Path -LiteralPath $outputRoot) {
        Remove-Item -LiteralPath $outputRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
    return $outputRoot
}

function Test-UnsafeText($Text, $CheckoutRoot) {
    $checkoutWindows = [regex]::Escape($CheckoutRoot)
    $checkoutSlash = [regex]::Escape($CheckoutRoot.Replace("\", "/"))
    $patterns = @(
        $checkoutWindows,
        $checkoutSlash,
        "[A-Za-z]:\\",
        "[A-Za-z]:\\\\",
        "\\\\[^\\]+\\[^\\]+",
        "\\\\\\\\[^\\]+\\\\[^\\]+",
        "/(Users|home|tmp|var/folders)/[^/\s]+",
        "(?i)(^|/)\.env(\.|$)",
        "BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY",
        "(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{20,}",
        "(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{20,})",
        "(?i)\b(password|passwd|api[_-]?key|token|secret|cookie|session|csrf)\b\s*[:=]\s*['""]?[^'"",;\s]{8,}",
        "://[^/\s:@]+:[^/\s@]+@",
        "(?i)\b(cookie|session|token|csrf)\b[^A-Za-z0-9]{0,8}[A-Za-z0-9._~+/=-]{24,}",
        "equipment_inventory\.local\.json",
        "credentials\.local",
        "(?i)\.xlsx?\b",
        "(?i)(^|/)(\.git|\.agents|\.codex|\.worktrees|node_modules|__pycache__|openspec/changes/archive|logs|transfer|raw|graphify-out|\.graphify-local)(/|$)"
    )
    foreach ($pattern in $patterns) {
        if ($Text -match $pattern) {
            return $true
        }
    }
    return $false
}

function Assert-SafeOutput($Root, $OutputRoot) {
    $htmlFiles = @(Get-ChildItem -LiteralPath $OutputRoot -Recurse -File -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -match "^\.(html?|xhtml)$" })
    if ($htmlFiles.Count -gt 0) {
        Fail "Graphify HTML visualization output is not accepted."
    }

    $files = @(Get-ChildItem -LiteralPath $OutputRoot -Recurse -File -Force -ErrorAction SilentlyContinue)
    if ($files.Count -eq 0) {
        Fail "Graphify produced no local output."
    }

    foreach ($file in $files) {
        $rel = Get-RelativePath $file.FullName $OutputRoot
        $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
        try {
            $text = $Utf8NoBomStrict.GetString($bytes)
        } catch {
            continue
        }
        if (Test-UnsafeText $text $Root) {
            Fail "Unsafe Graphify output rejected in $rel."
        }
    }
}

function Assert-NoTrackedGraphOutput($Root) {
    $trackedLegacy = (& git -C $Root ls-files $LegacyOutputDirName 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail "Unable to inspect tracked legacy graph output."
    }
    if ($trackedLegacy) {
        Fail "Tracked legacy graphify-out artifacts remain."
    }

    $trackedLocal = (& git -C $Root ls-files $LocalOutputDirName 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail "Unable to inspect tracked local graph output."
    }
    if ($trackedLocal) {
        Fail "Local .graphify-local output must not be tracked."
    }
}

$sourceRootFull = Get-RepoRootFrom $SourceRoot
$ignoreFile = Assert-GraphifyIgnore $sourceRootFull
Assert-OutputIgnored $sourceRootFull
Assert-NoTrackedGraphOutput $sourceRootFull

$version = Get-GraphifyVersion
if ($version -ne $ExpectedGraphifyVersion) {
    Fail "Graphify version mismatch. Expected $ExpectedGraphifyVersion."
}

$trackedSnapshot = Get-TrackedSnapshot $sourceRootFull
$outputRoot = Reset-LocalOutput $sourceRootFull
$graphifySucceeded = $false

try {
    & graphify extract $sourceRootFull --code-only --no-viz --ignore-file $ignoreFile --output $outputRoot
    if ($LASTEXITCODE -ne 0) {
        Fail "graphify extract failed."
    }
    $graphifySucceeded = $true
    Assert-SafeOutput $sourceRootFull $outputRoot
    Assert-NoTrackedGraphOutput $sourceRootFull
} finally {
    Restore-TrackedSnapshot $sourceRootFull $trackedSnapshot
}

if (-not $graphifySucceeded) {
    exit 1
}

Write-Host "Graphify package: $ExpectedGraphifyPackage"
Write-Host "Graphify version: $version"
Write-Host "Mode: code-only"
Write-Host "HTML visualization: disabled"
Write-Host "Source repository: $sourceRootFull"
Write-Host "Local output: $outputRoot"
Write-Host "Output is ignored and disposable."

exit 0
