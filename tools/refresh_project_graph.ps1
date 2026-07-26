param(
    [ValidateSet("Initial", "Incremental", "FullRebuild", "InstallExact")]
    [string]$Mode = "Initial",
    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ExpectedGraphifyVersion = "0.9.26"
$GraphDirName = "graphify-out"
$AllowedGenerated = @(
    "graphify-out/graph.json",
    "graphify-out/manifest.json",
    "graphify-out/GRAPH_REPORT.md",
    "graphify-out/baseline.json"
)

function Fail($Message) {
    Write-Error $Message
    exit 1
}

function RelPath($Path, $Root) {
    $full = [System.IO.Path]::GetFullPath($Path)
    $base = [System.IO.Path]::GetFullPath($Root)
    $uriBase = [System.Uri]::new($base.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar)
    $uriFull = [System.Uri]::new($full)
    return [System.Uri]::UnescapeDataString($uriBase.MakeRelativeUri($uriFull).ToString()).Replace("\", "/")
}

function Get-RepoRoot {
    $root = (& git rev-parse --show-toplevel 2>$null)
    if ($LASTEXITCODE -ne 0 -or -not $root) {
        Fail "Not inside a Git repository."
    }
    return [System.IO.Path]::GetFullPath($root.Trim())
}

function Get-Sha256($Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Get-GraphVersion {
    $versionText = (& graphify --version 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail "graphify --version failed: $versionText"
    }
    if ($versionText -notmatch "graphify\s+([0-9]+\.[0-9]+\.[0-9]+)") {
        Fail "Unable to parse Graphify version from: $versionText"
    }
    return $Matches[1]
}

function Assert-CleanGit($Root) {
    if ($AllowDirty) {
        Write-Host "WARNING: AllowDirty set; clean Git check skipped."
        return
    }
    $status = (& git -C $Root status --short 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail "git status failed: $status"
    }
    if ($status) {
        Fail "Working tree is not clean. Commit or discard unrelated changes before graph refresh."
    }
}

function Assert-Json($Path) {
    try {
        $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
        return $raw | ConvertFrom-Json
    } catch {
        Fail "Invalid JSON: $Path"
    }
}

function Count-Graph($Graph) {
    $nodeCount = 0
    $edgeCount = 0

    foreach ($name in @("nodes", "Nodes")) {
        if ($Graph.PSObject.Properties.Name -contains $name -and $null -ne $Graph.$name) {
            $nodeCount = @($Graph.$name).Count
            break
        }
    }
    foreach ($name in @("edges", "links", "Edges", "Links")) {
        if ($Graph.PSObject.Properties.Name -contains $name -and $null -ne $Graph.$name) {
            $edgeCount = @($Graph.$name).Count
            break
        }
    }

    return @{ Nodes = $nodeCount; Edges = $edgeCount }
}

function Get-JsonScalars($Value) {
    if ($null -eq $Value) {
        return
    }
    if ($Value -is [string]) {
        $Value
        return
    }
    if ($Value -is [System.Collections.IDictionary]) {
        foreach ($key in $Value.Keys) {
            Get-JsonScalars $Value[$key]
        }
        return
    }
    if ($Value -is [System.Management.Automation.PSCustomObject]) {
        foreach ($prop in $Value.PSObject.Properties) {
            Get-JsonScalars $prop.Value
        }
        return
    }
    if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
        foreach ($item in $Value) {
            Get-JsonScalars $item
        }
    }
}

function Assert-SafeGeneratedOutput($Root, $GraphDir, $Graph, $Manifest) {
    $files = Get-ChildItem -LiteralPath $GraphDir -File -Recurse | ForEach-Object { RelPath $_.FullName $Root }
    $unexpected = @($files | Where-Object { $AllowedGenerated -notcontains $_ })
    if ($unexpected.Count -gt 0) {
        Fail ("Unexpected generated files: " + ($unexpected -join ", "))
    }

    if (Test-Path -LiteralPath (Join-Path $GraphDir "graph.html")) {
        Fail "graph.html must not be generated or committed."
    }

    $repoRelativeScalars = @()
    foreach ($value in (Get-JsonScalars $Graph)) { $repoRelativeScalars += $value }
    foreach ($value in (Get-JsonScalars $Manifest)) { $repoRelativeScalars += $value }

    $blockedPatterns = @(
        "[A-Za-z]:\\",
        "^\\\\",
        "/home/",
        "/Users/",
        "/tmp/",
        "\.worktrees",
        "equipment_inventory\.local\.json",
        "\.xlsx\b",
        "\.xls\b",
        "\.env\b",
        "BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY",
        "graphify-out"
    )
    $sensitiveVocabulary = @("password", "passwd", "token", "cookie", "session", "csrf")

    $vocabularyHits = @{}
    foreach ($scalar in $repoRelativeScalars) {
        foreach ($pattern in $blockedPatterns) {
            if ($scalar -match $pattern) {
                Fail "Generated output contains disallowed path or sensitive marker matching pattern '$pattern'."
            }
        }
        foreach ($term in $sensitiveVocabulary) {
            if ($scalar -match "(?i)$term") {
                $vocabularyHits[$term] = $true
            }
        }
    }
    foreach ($term in ($vocabularyHits.Keys | Sort-Object)) {
        Write-Host "Security scan note: generated output contains project vocabulary '$term'; source review required, not treated as a secret by itself."
    }

    $reportPath = Join-Path $GraphDir "GRAPH_REPORT.md"
    $reportText = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8
    foreach ($pattern in $blockedPatterns) {
        if ($reportText -match $pattern) {
            Fail "GRAPH_REPORT.md contains disallowed path or sensitive marker matching pattern '$pattern'."
        }
    }
}

function Invoke-SmokeQueries($Root, $GraphPath) {
    $queries = @(
        @{ Query = "PDUController"; Source = "gui/pdu_controller.py" },
        @{ Query = "InteractiveSessionController"; Source = "core/interactive_session.py" },
        @{ Query = "EquipmentInventory"; Source = "core/equipment_inventory.py" },
        @{ Query = "Credential"; Source = "core/credentials.py" },
        @{ Query = "RelatedCodec"; Source = "core/related_codec_status.py" }
    )

    $raw = Get-Content -LiteralPath $GraphPath -Raw -Encoding UTF8
    $results = @()
    foreach ($item in $queries) {
        $sourcePath = Join-Path $Root $item.Source
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            Fail "Smoke query source missing: $($item.Source)"
        }
        if ($raw -notmatch [regex]::Escape($item.Query)) {
            Fail "Smoke query found no graph node or text for: $($item.Query)"
        }
        $sourceText = Get-Content -LiteralPath $sourcePath -Raw -Encoding UTF8
        $sourceConfirmed = $sourceText -match [regex]::Escape($item.Query)
        if (-not $sourceConfirmed -and $item.Query -eq "RelatedCodec") {
            $sourceConfirmed = $sourceText -match "related.*codec|codec"
        }
        if (-not $sourceConfirmed) {
            Fail "Smoke query not confirmed in source: $($item.Query)"
        }
        $results += "$($item.Query) -> $($item.Source) [source-confirmed, confidence=EXTRACTED-or-schema-absent]"
    }
    return $results
}

function Invoke-GraphifyBuild($Root) {
    & graphify extract $Root --code-only --no-viz
    if ($LASTEXITCODE -ne 0) {
        Fail "graphify extract failed."
    }

    & graphify cluster-only $Root --no-viz --no-label
    if ($LASTEXITCODE -ne 0) {
        Fail "graphify cluster-only failed."
    }
}

function Remove-UncommittedGraphifyByproducts($GraphDir) {
    $byproducts = @(
        "cache",
        "memory",
        "reflections",
        ".graphify_analysis.json",
        ".graphify_labels.json",
        ".graphify_root",
        "graph.html",
        "GRAPH_TREE.html"
    )

    foreach ($item in $byproducts) {
        $path = Join-Path $GraphDir $item
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Recurse -Force
        }
    }

    Get-ChildItem -LiteralPath $GraphDir -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match "^\d{4}-\d{2}-\d{2}$" } |
        ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force }
}

function Sanitize-GraphReport($Root, $GraphDir) {
    $reportPath = Join-Path $GraphDir "GRAPH_REPORT.md"
    if (-not (Test-Path -LiteralPath $reportPath)) {
        return
    }

    $report = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    $rootForward = $rootFull.Replace("\", "/")
    $projectLabel = Split-Path -Leaf $rootFull
    $report = $report.Replace($rootFull, $projectLabel).Replace($rootForward, $projectLabel)
    Set-Content -LiteralPath $reportPath -Value $report -Encoding UTF8
}

function Write-Baseline($Root, $GraphDir, $SourceCommit, $GraphifyVersion, $Graph, $GraphPath) {
    $counts = Count-Graph $Graph
    if ($counts.Nodes -le 0 -or $counts.Edges -le 0) {
        Fail "Graph must contain nonzero nodes and edges. Found nodes=$($counts.Nodes), edges=$($counts.Edges)."
    }

    $baseline = [ordered]@{
        schema_version = 1
        generator = "graphify"
        graphify_version = $GraphifyVersion
        mode = "code-only"
        indexed_source_commit = $SourceCommit
        indexed_branch = "master"
        generated_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        graph_sha256 = Get-Sha256 $GraphPath
        ignore_file_sha256 = Get-Sha256 (Join-Path $Root ".graphifyignore")
        node_count = $counts.Nodes
        edge_count = $counts.Edges
    }

    $baselinePath = Join-Path $GraphDir "baseline.json"
    $baseline | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $baselinePath -Encoding UTF8
    return $baseline
}

$root = Get-RepoRoot
Set-Location $root

if (-not (Test-Path -LiteralPath (Join-Path $root "RULES.md")) -or
    -not (Test-Path -LiteralPath (Join-Path $root "openspec.cmd"))) {
    Fail "Repository root verification failed."
}

if ($Mode -eq "InstallExact") {
    & uv tool install "graphifyy==$ExpectedGraphifyVersion"
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath (Join-Path $root ".graphifyignore"))) {
    Fail ".graphifyignore is required."
}

Assert-CleanGit $root

$sourceCommit = (& git -C $root rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $sourceCommit.Length -ne 40) {
    Fail "Unable to determine full source commit."
}

$version = Get-GraphVersion
if ($version -ne $ExpectedGraphifyVersion) {
    Fail "Graphify version mismatch. Expected $ExpectedGraphifyVersion, got $version."
}

$graphDir = Join-Path $root $GraphDirName

if ($Mode -eq "FullRebuild") {
    if (Test-Path -LiteralPath $graphDir) {
        Remove-Item -LiteralPath $graphDir -Recurse -Force
    }
}

if ($Mode -eq "Initial") {
    if (Test-Path -LiteralPath $graphDir) {
        $existing = Get-ChildItem -LiteralPath $graphDir -Force
        if ($existing.Count -gt 0) {
            Fail "graphify-out already exists. Use FullRebuild for an explicit rebuild."
        }
    }
    Invoke-GraphifyBuild $root
} elseif ($Mode -eq "Incremental") {
    & graphify check-update $root
    if ($LASTEXITCODE -ne 0) {
        Fail "graphify check-update failed."
    }
    & graphify update $root
    if ($LASTEXITCODE -ne 0) {
        Fail "graphify update failed."
    }
} elseif ($Mode -eq "FullRebuild") {
    Invoke-GraphifyBuild $root
}

$graphPath = Join-Path $graphDir "graph.json"
$manifestPath = Join-Path $graphDir "manifest.json"
$reportPath = Join-Path $graphDir "GRAPH_REPORT.md"

foreach ($required in @($graphPath, $manifestPath, $reportPath)) {
    if (-not (Test-Path -LiteralPath $required)) {
        Fail "Required Graphify output missing: $required"
    }
}

$graph = Assert-Json $graphPath
$manifest = Assert-Json $manifestPath
Remove-UncommittedGraphifyByproducts $graphDir
Sanitize-GraphReport $root $graphDir
$baseline = Write-Baseline $root $graphDir $sourceCommit $version $graph $graphPath
Assert-SafeGeneratedOutput $root $graphDir $graph $manifest
$smoke = Invoke-SmokeQueries $root $graphPath

Write-Host "Graphify version: $version"
Write-Host "Indexed source commit: $sourceCommit"
Write-Host "Mode: code-only"
Write-Host "No-viz: true"
Write-Host "Graph SHA-256: $($baseline.graph_sha256)"
Write-Host "Ignore SHA-256: $($baseline.ignore_file_sha256)"
Write-Host "Node count: $($baseline.node_count)"
Write-Host "Edge count: $($baseline.edge_count)"
Write-Host "Smoke queries:"
$smoke | ForEach-Object { Write-Host "  $_" }

exit 0
