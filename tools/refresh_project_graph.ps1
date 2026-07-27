param(
    [ValidateSet("Initial", "Incremental", "FullRebuild", "InstallExact")]
    [string]$Mode = "Initial",
    [string]$BaselineStage = "",
    [string]$SourceRef = "origin/master",
    [string]$TargetBranch = "master",
    [string]$PostArchiveValidationEvidence = "",
    [string]$SourceRoot = "",
    [string]$OutputRoot = "",
    [int]$MaxChangedFilesForIncremental = 25,
    [int]$MaxDeletedOrRenamedFilesForIncremental = 5,
    [int]$MaxNodeDeltaPerChangedFile = 250,
    [int]$MaxEdgeDeltaPerChangedFile = 600
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ExpectedGraphifyVersion = "0.9.26"
$GraphDirName = "graphify-out"
$TempDirName = ".graphify-tmp"
$ApprovedPostArchiveValidationEvidence = "openspec/validation/frozen-project-graph-baseline.post-archive.json"
$AllowedGenerated = @(
    "graphify-out/graph.json",
    "graphify-out/manifest.json",
    "graphify-out/GRAPH_REPORT.md",
    "graphify-out/baseline.json"
)
$CanonicalGeneratedArtifacts = @(
    "graph.json",
    "manifest.json",
    "GRAPH_REPORT.md",
    "baseline.json"
)
$Utf8NoBomStrict = [System.Text.UTF8Encoding]::new($false, $true)
$ForbiddenFreshnessAdvice = "graphify update . after code changes"

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

function Get-RepoRootFrom($Path) {
    $root = (& git -C $Path rev-parse --show-toplevel 2>$null)
    if ($LASTEXITCODE -ne 0 -or -not $root) {
        Fail "Not inside a Git repository: $Path"
    }
    return [System.IO.Path]::GetFullPath($root.Trim())
}

function Get-Sha256($Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function ConvertTo-CanonicalGeneratedTextArtifact($GraphDir, $ArtifactName) {
    if ($CanonicalGeneratedArtifacts -notcontains $ArtifactName) {
        Fail "Refusing to canonicalize unexpected generated artifact: $ArtifactName"
    }

    $graphDirFull = [System.IO.Path]::GetFullPath($GraphDir).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    $path = Join-Path $graphDirFull $ArtifactName
    if (-not (Test-Path -LiteralPath $path)) {
        Fail "Generated artifact missing before canonicalization: $ArtifactName"
    }

    $pathFull = [System.IO.Path]::GetFullPath($path)
    $graphDirPrefix = $graphDirFull + [System.IO.Path]::DirectorySeparatorChar
    if (-not $pathFull.StartsWith($graphDirPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        Fail "Generated artifact canonicalization path escaped graph output: $ArtifactName"
    }

    $bytes = [System.IO.File]::ReadAllBytes($pathFull)
    $offset = 0
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $offset = 3
    }

    try {
        $text = $Utf8NoBomStrict.GetString($bytes, $offset, ($bytes.Length - $offset))
    } catch {
        Fail "Generated artifact is not valid UTF-8: $ArtifactName"
    }

    $text = $text.Replace("`r`n", "`n").Replace("`r", "`n")
    [System.IO.File]::WriteAllText($pathFull, $text, $Utf8NoBomStrict)
}

function Get-GitSha($Root, $Ref) {
    $sha = (& git -C $Root rev-parse $Ref 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $sha -notmatch "^[0-9a-f]{40}$") {
        Fail "Unable to resolve Git ref '$Ref' in $Root`: $sha"
    }
    return $sha
}

function Assert-CleanGit($Root, $Purpose) {
    $status = (& git -C $Root status --short 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail "git status failed for $Purpose`: $status"
    }
    if ($status) {
        Fail "$Purpose worktree is not clean. Refusing to publish graph metadata for uncommitted bytes."
    }
}

function Get-BaselineStageValue($BaselineStage) {
    if ($BaselineStage -notin @("Bootstrap", "Final")) {
        Fail "BaselineStage is required and must be either Bootstrap or Final."
    }
    return $BaselineStage.ToLowerInvariant()
}

function Assert-FinalSourceContainsGraphifyTooling($SourceRoot) {
    $required = @(
        "tools/refresh_project_graph.ps1",
        ".graphifyignore",
        "docs/project-graph-runbook.md",
        "RULES.md"
    )
    foreach ($item in $required) {
        if (-not (Test-Path -LiteralPath (Join-Path $SourceRoot $item))) {
            Fail "Final baseline source is missing required graph workflow file: $item"
        }
    }
}

function Get-PathUnderRoot($Root, $Path, $Purpose) {
    if (-not $Path) {
        Fail "$Purpose path is required."
    }
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    $candidate = if ([System.IO.Path]::IsPathRooted($Path)) {
        [System.IO.Path]::GetFullPath($Path)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $Root $Path))
    }
    $rootPrefix = $rootFull + [System.IO.Path]::DirectorySeparatorChar
    if ($candidate -ne $rootFull -and -not $candidate.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        Fail "$Purpose must be inside the source tree: $Path"
    }
    return $candidate
}

function Test-GitAncestor($Root, $Ancestor, $Descendant) {
    & git -C $Root merge-base --is-ancestor $Ancestor $Descendant 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Invoke-GitChecked($Root, $Arguments, $FailureMessage) {
    $output = (& git -C $Root @Arguments 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail "$FailureMessage`: $output"
    }
    return $output
}

function Assert-TrackedHeadEvidence($SourceRoot, $EvidenceFull) {
    $relativeEvidencePath = RelPath $EvidenceFull $SourceRoot
    if ($relativeEvidencePath -ne $ApprovedPostArchiveValidationEvidence) {
        Fail "Post-archive validation evidence must be exactly $ApprovedPostArchiveValidationEvidence."
    }

    & git -C $SourceRoot check-ignore --no-index --quiet -- $relativeEvidencePath
    if ($LASTEXITCODE -eq 0) {
        Fail "Post-archive validation evidence must not be ignored: $relativeEvidencePath"
    }
    if ($LASTEXITCODE -ne 1) {
        Fail "Unable to verify ignore status for post-archive validation evidence: $relativeEvidencePath"
    }

    [void](Invoke-GitChecked $SourceRoot @("ls-files", "--error-unmatch", "--", $relativeEvidencePath) "Post-archive validation evidence must be tracked in Git")
    [void](Invoke-GitChecked $SourceRoot @("cat-file", "-e", "HEAD:$relativeEvidencePath") "Post-archive validation evidence must exist in SourceRoot HEAD")

    $headBlob = Invoke-GitChecked $SourceRoot @("rev-parse", "HEAD:$relativeEvidencePath") "Unable to read HEAD blob for post-archive validation evidence"
    $workingBlob = Invoke-GitChecked $SourceRoot @("hash-object", "--path=$relativeEvidencePath", "--", $EvidenceFull) "Unable to hash working-tree post-archive validation evidence"
    if ($headBlob -ne $workingBlob) {
        Fail "Post-archive validation evidence working-tree content must hash to the SourceRoot HEAD blob after repository filters."
    }

    return $relativeEvidencePath
}

function Assert-EvidenceOnlyCommitDelta($SourceRoot, $ValidatedSourceCommit, $SourceCommit) {
    $previousEvidencePath = (& git -C $SourceRoot ls-tree -r --name-only $ValidatedSourceCommit -- $ApprovedPostArchiveValidationEvidence 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail "Unable to verify post-archive validation evidence absence from validated_source_commit: $previousEvidencePath"
    }
    if ($previousEvidencePath) {
        Fail "Post-archive validation evidence must be created by the evidence commit and absent from validated_source_commit."
    }

    $diffOutput = (& git -C $SourceRoot diff --name-only $ValidatedSourceCommit $SourceCommit -- 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail "Unable to verify evidence-only delta from validated_source_commit to SourceRoot HEAD: $diffOutput"
    }
    $changedPaths = @($diffOutput -split "`r?`n" |
        Where-Object { $_.Trim() } |
        ForEach-Object { $_.Trim().Replace("\", "/") } |
        Sort-Object -Unique)
    if ($changedPaths.Count -ne 1 -or $changedPaths[0] -ne $ApprovedPostArchiveValidationEvidence) {
        $actual = if ($changedPaths.Count -eq 0) { "<none>" } else { $changedPaths -join ", " }
        Fail "Final evidence commit delta from validated_source_commit to SourceRoot HEAD must contain only $ApprovedPostArchiveValidationEvidence; actual: $actual"
    }
}

function Assert-EvidenceCheckPassed($Evidence, $Name) {
    if ($Evidence.PSObject.Properties.Name -notcontains $Name) {
        Fail "Post-archive validation evidence is missing required check: $Name"
    }
    $value = $Evidence.$Name
    $status = if ($value -is [string]) {
        $value
    } elseif ($null -ne $value -and $value.PSObject.Properties.Name -contains "status") {
        [string]$value.status
    } else {
        ""
    }
    if ($status.ToLowerInvariant() -ne "pass") {
        Fail "Post-archive validation evidence check '$Name' must have status pass."
    }
}

function Assert-FinalWorkflowGate($SourceRoot, $SourceCommit, $EvidencePath) {
    if (-not $EvidencePath) {
        Fail "Final baseline requires -PostArchiveValidationEvidence pointing to project-owned post-archive validation JSON."
    }

    $evidenceFull = Get-PathUnderRoot $SourceRoot $EvidencePath "PostArchiveValidationEvidence"
    if (-not (Test-Path -LiteralPath $evidenceFull -PathType Leaf)) {
        Fail "Post-archive validation evidence file is missing: $EvidencePath"
    }
    [void](Assert-TrackedHeadEvidence $SourceRoot $evidenceFull)
    $evidence = Assert-Json $evidenceFull

    if ($evidence.change_name -ne "frozen-project-graph-baseline") {
        Fail "Post-archive validation evidence change_name must be frozen-project-graph-baseline."
    }
    if ([string]$evidence.archive_commit -notmatch "^[0-9a-f]{40}$") {
        Fail "Post-archive validation evidence archive_commit must be a full commit SHA."
    }
    $archiveCommit = Get-GitSha $SourceRoot ([string]$evidence.archive_commit)
    if ([string]$evidence.validated_source_commit -notmatch "^[0-9a-f]{40}$") {
        Fail "Post-archive validation evidence validated_source_commit must be a full commit SHA."
    }
    $validatedSourceCommit = Get-GitSha $SourceRoot ([string]$evidence.validated_source_commit)
    if (-not (Test-GitAncestor $SourceRoot $archiveCommit $validatedSourceCommit)) {
        Fail "Post-archive validation evidence archive_commit must be an ancestor of validated_source_commit."
    }
    if (-not (Test-GitAncestor $SourceRoot $validatedSourceCommit $SourceCommit)) {
        Fail "Post-archive validation evidence validated_source_commit must be an ancestor of SourceRoot HEAD."
    }
    Assert-EvidenceOnlyCommitDelta $SourceRoot $validatedSourceCommit $SourceCommit

    $archiveRoot = Join-Path $SourceRoot "openspec/changes/archive"
    if (-not (Test-Path -LiteralPath $archiveRoot -PathType Container)) {
        Fail "Final baseline requires archived OpenSpec changes under openspec/changes/archive/."
    }
    $archivedChangeDirs = @(Get-ChildItem -LiteralPath $archiveRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq "frozen-project-graph-baseline" -or $_.Name -like "*-frozen-project-graph-baseline" })
    if ($archivedChangeDirs.Count -eq 0) {
        Fail "Final baseline requires archived change artifact for frozen-project-graph-baseline under openspec/changes/archive/."
    }
    $archiveSpecFound = $false
    foreach ($dir in $archivedChangeDirs) {
        if (Test-Path -LiteralPath (Join-Path $dir.FullName "specs/agent-project-navigation/spec.md") -PathType Leaf) {
            $archiveSpecFound = $true
            break
        }
    }
    if (-not $archiveSpecFound) {
        Fail "Archived frozen-project-graph-baseline artifact must include specs/agent-project-navigation/spec.md."
    }

    $activeChange = Join-Path $SourceRoot "openspec/changes/frozen-project-graph-baseline"
    if (Test-Path -LiteralPath $activeChange) {
        Fail "Final baseline requires active openspec/changes/frozen-project-graph-baseline/ to be archived first."
    }

    foreach ($check in @("openspec_change_validation", "openspec_all_validation", "python_tests", "git_diff_check")) {
        Assert-EvidenceCheckPassed $evidence $check
    }
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

function Assert-Json($Path) {
    try {
        $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
        return $raw | ConvertFrom-Json
    } catch {
        Fail "Invalid JSON: $Path"
    }
}

function Count-Graph($Graph) {
    $nodes = @()
    $edges = @()
    if ($Graph.PSObject.Properties.Name -contains "nodes" -and $null -ne $Graph.nodes) {
        $nodes = @($Graph.nodes)
    }
    if ($Graph.PSObject.Properties.Name -contains "links" -and $null -ne $Graph.links) {
        $edges = @($Graph.links)
    } elseif ($Graph.PSObject.Properties.Name -contains "edges" -and $null -ne $Graph.edges) {
        $edges = @($Graph.edges)
    }
    return @{ Nodes = $nodes.Count; Edges = $edges.Count }
}

function Get-GraphNodes($Graph) {
    if ($Graph.PSObject.Properties.Name -contains "nodes" -and $null -ne $Graph.nodes) {
        return @($Graph.nodes)
    }
    return @()
}

function Get-GraphLinks($Graph) {
    if ($Graph.PSObject.Properties.Name -contains "links" -and $null -ne $Graph.links) {
        return @($Graph.links)
    }
    if ($Graph.PSObject.Properties.Name -contains "edges" -and $null -ne $Graph.edges) {
        return @($Graph.edges)
    }
    return @()
}

function Get-ManifestSourceSet($Manifest) {
    $paths = @()
    foreach ($prop in $Manifest.PSObject.Properties) {
        $paths += $prop.Name.Replace("\", "/")
    }
    return @($paths | Sort-Object -Unique)
}

function Get-NodeIdentitySet($Graph) {
    return @(Get-GraphNodes $Graph | ForEach-Object { [string]$_.id } | Sort-Object -Unique)
}

function Get-LinkIdentitySet($Graph) {
    return @(Get-GraphLinks $Graph | ForEach-Object {
        $confidence = if ($_.PSObject.Properties.Name -contains "confidence" -and $_.confidence) { $_.confidence } else { "NOT_AVAILABLE" }
        "$($_.source)|$($_.target)|$($_.relation)|$confidence|$($_.source_file)|$($_.source_location)"
    } | Sort-Object -Unique)
}

function Get-ConfidenceSummary($Graph) {
    $summary = @{}
    foreach ($link in (Get-GraphLinks $Graph)) {
        $confidence = if ($link.PSObject.Properties.Name -contains "confidence" -and $link.confidence) {
            [string]$link.confidence
        } else {
            "NOT_AVAILABLE"
        }
        if (-not $summary.ContainsKey($confidence)) {
            $summary[$confidence] = 0
        }
        $summary[$confidence] += 1
    }
    return $summary
}

function Get-JsonScalarsWithPath($Value, $Path) {
    if ($null -eq $Value) {
        return
    }
    if ($Value -is [string]) {
        [pscustomobject]@{ Path = $Path; Value = $Value }
        return
    }
    if ($Value -is [System.Collections.IDictionary]) {
        foreach ($key in $Value.Keys) {
            Get-JsonScalarsWithPath $Value[$key] "$Path.$key"
        }
        return
    }
    if ($Value -is [System.Management.Automation.PSCustomObject]) {
        foreach ($prop in $Value.PSObject.Properties) {
            Get-JsonScalarsWithPath $prop.Value "$Path.$($prop.Name)"
        }
        return
    }
    if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
        $i = 0
        foreach ($item in $Value) {
            Get-JsonScalarsWithPath $item "$Path[$i]"
            $i += 1
        }
    }
}

function Get-SafeFingerprint($Value) {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        $sha = $hasher.ComputeHash($bytes)
        return ([System.BitConverter]::ToString($sha).Replace("-", "").ToLowerInvariant()).Substring(0, 16)
    } finally {
        $hasher.Dispose()
    }
}

function Get-ShannonEntropy($Value) {
    if (-not $Value) {
        return 0
    }
    $counts = @{}
    foreach ($ch in $Value.ToCharArray()) {
        $key = [string]$ch
        if (-not $counts.ContainsKey($key)) {
            $counts[$key] = 0
        }
        $counts[$key] += 1
    }
    $entropy = 0.0
    foreach ($count in $counts.Values) {
        $p = [double]$count / [double]$Value.Length
        $entropy -= $p * [Math]::Log($p, 2)
    }
    return $entropy
}

function Add-SecretFinding([System.Collections.ArrayList]$Findings, $Artifact, $JsonPath, $Category, $Value) {
    [void]$Findings.Add([pscustomobject]@{
        Artifact = $Artifact
        JsonPath = $JsonPath
        Category = $Category
        Fingerprint = Get-SafeFingerprint $Value
    })
}

function Test-SecretScalars($Artifact, $Scalars) {
    $findings = [System.Collections.ArrayList]::new()
    foreach ($item in $Scalars) {
        $value = [string]$item.Value
        $jsonPath = [string]$item.Path
        $isKnownHashField = $jsonPath -match "(?i)(ast_hash|semantic_hash|graph_sha256|ignore_file_sha256|sha256)$"

        if ($value -match "[A-Za-z]:\\") { Add-SecretFinding $findings $Artifact $jsonPath "windows-absolute-path" $value }
        if ($value -match "^\\\\") { Add-SecretFinding $findings $Artifact $jsonPath "unc-path" $value }
        if ($value -match "/(Users|home|tmp|var/folders)/[^/\s]+") { Add-SecretFinding $findings $Artifact $jsonPath "posix-checkout-path" $value }
        if ($value -match "(?i)(^|/)\.env(\.|$)|docker-compose\.override|local\.settings|deployment\.local") { Add-SecretFinding $findings $Artifact $jsonPath "local-deployment-file" $value }
        if ($value -match "BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY") { Add-SecretFinding $findings $Artifact $jsonPath "private-key-block" $value }
        if ($value -match "(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{20,}") { Add-SecretFinding $findings $Artifact $jsonPath "bearer-token" $value }
        if ($value -match "(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{20,})") { Add-SecretFinding $findings $Artifact $jsonPath "api-key-prefix" $value }
        if ($value -match "(?i)\b(password|passwd|api[_-]?key|token|secret|cookie|session|csrf)\b\s*[:=]\s*['""]?[^'"",;\s]{8,}") { Add-SecretFinding $findings $Artifact $jsonPath "credential-literal" $value }
        if ($value -match "://[^/\s:@]+:[^/\s@]+@") { Add-SecretFinding $findings $Artifact $jsonPath "url-embedded-credential" $value }
        if ($value -match "(?i)\b(cookie|session|token|csrf)\b[^A-Za-z0-9]{0,8}[A-Za-z0-9._~+/=-]{24,}") { Add-SecretFinding $findings $Artifact $jsonPath "session-token-value" $value }
        if ($value -match "equipment_inventory\.local\.json") { Add-SecretFinding $findings $Artifact $jsonPath "equipment-inventory-local-file" $value }
        if ($value -match "(?i)\.xls[xm]?\b") { Add-SecretFinding $findings $Artifact $jsonPath "excel-file-reference" $value }
        if ($value -match "(^|/|\\)\.worktrees($|/|\\)") { Add-SecretFinding $findings $Artifact $jsonPath "temporary-worktree-path" $value }
        if ($value -match "(^|/|\\)graphify-out($|/|\\)") { Add-SecretFinding $findings $Artifact $jsonPath "graph-output-self-indexing" $value }
        if (-not $isKnownHashField -and $value.Length -ge 40 -and $value -match "^\S+$" -and $value -match "[a-z]" -and $value -match "[A-Z]" -and $value -match "\d" -and (Get-ShannonEntropy $value) -ge 4.5) {
            Add-SecretFinding $findings $Artifact $jsonPath "high-entropy-string-literal" $value
        }
    }
    return @($findings)
}

function Assert-SecretScan($GraphDir, $Graph, $Manifest, $Baseline) {
    $allFindings = @()
    $allFindings += Test-SecretScalars "graphify-out/graph.json" @(Get-JsonScalarsWithPath $Graph '$')
    $allFindings += Test-SecretScalars "graphify-out/manifest.json" @(Get-JsonScalarsWithPath $Manifest '$')
    $allFindings += Test-SecretScalars "graphify-out/baseline.json" @(Get-JsonScalarsWithPath $Baseline '$')

    $reportPath = Join-Path $GraphDir "GRAPH_REPORT.md"
    $reportText = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8
    $allFindings += Test-SecretScalars "graphify-out/GRAPH_REPORT.md" @([pscustomobject]@{ Path = '$'; Value = $reportText })

    if ($allFindings.Count -gt 0) {
        foreach ($finding in $allFindings) {
            Write-Error "Secret/path scan finding: artifact=$($finding.Artifact); path=$($finding.JsonPath); category=$($finding.Category); fingerprint=$($finding.Fingerprint)"
        }
        Fail "Generated graph artifacts failed strengthened secret/path scan."
    }
}

function Assert-GraphifyIgnore($OutputRoot) {
    $ignorePath = Join-Path $OutputRoot ".graphifyignore"
    if (-not (Test-Path -LiteralPath $ignorePath)) {
        Fail ".graphifyignore is required in the output worktree."
    }
    $text = Get-Content -LiteralPath $ignorePath -Raw -Encoding UTF8
    $required = @(
        "graphify-out/",
        ".worktrees/",
        "equipment_inventory.local.json",
        "*.xlsx",
        "*.xls",
        ".env",
        "credentials.local.json",
        "openspec/changes/archive/"
    )
    foreach ($entry in $required) {
        if ($text -notmatch [regex]::Escape($entry)) {
            Fail ".graphifyignore is missing required rule: $entry"
        }
    }
    if ($text -match "[A-Za-z]:\\|/Users/|/home/|/tmp/") {
        Fail ".graphifyignore contains a user-specific absolute path."
    }
}

function New-TempRoot($OutputRoot) {
    $tempParent = Join-Path $OutputRoot $TempDirName
    New-Item -ItemType Directory -Force -Path $tempParent | Out-Null
    $name = "graph-build-$PID-$([Guid]::NewGuid().ToString('N'))"
    $tempRoot = Join-Path $tempParent $name
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    return $tempRoot
}

function New-BuildCopy($SourceRoot, $OutputRoot) {
    $buildRoot = New-TempRoot $OutputRoot
    $tarPath = Join-Path $buildRoot "source.tar"
    & git -C $SourceRoot archive --format=tar HEAD -o $tarPath
    if ($LASTEXITCODE -ne 0) {
        Fail "git archive failed for source root."
    }
    & tar -xf $tarPath -C $buildRoot
    if ($LASTEXITCODE -ne 0) {
        Fail "tar extraction failed for temporary source copy."
    }
    Remove-Item -LiteralPath $tarPath -Force

    $ignoreSource = Join-Path $OutputRoot ".graphifyignore"
    Copy-Item -LiteralPath $ignoreSource -Destination (Join-Path $buildRoot ".graphifyignore") -Force
    return $buildRoot
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

function Set-FrozenGraphReportPolicy($GraphDir, $SourceCommit, $BaselineStage, $SourceRef, $TargetBranch) {
    $reportPath = Join-Path $GraphDir "GRAPH_REPORT.md"
    if (-not (Test-Path -LiteralPath $reportPath)) {
        return
    }

    $report = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8
    if ($BaselineStage -eq "bootstrap") {
        $policy = @(
            "## Bootstrap Frozen Baseline Policy",
            "- Built from source commit: ``$SourceCommit``",
            "- Indexed source ref: ``$SourceRef``",
            "- Target branch: ``$TargetBranch``",
            "- Stage: bootstrap, pre-archive, non-final.",
            "- This frozen project baseline verifies the initial Graphify integration, wrapper, corpus filters, security scans, smoke queries, and reproducibility.",
            "- This graph is not the navigation baseline for the next change.",
            "- Do not rebuild or incrementally update the graph during active implementation, review, testing, or validation.",
            '- Read `RULES.md`, `docs/project-graph-runbook.md`, and `graphify-out/baseline.json`.',
            '- Compare `indexed_source_commit` with the current branch and analyze the branch diff separately.',
            "- Build the final baseline only after independent review, archive, and post-archive validation."
        ) -join "`r`n"
    } else {
        $policy = @(
            "## Final Frozen Baseline Policy",
            "- Built from post-archive validated source commit: ``$SourceCommit``",
            "- Indexed source ref: ``$SourceRef``",
            "- Target branch: ``$TargetBranch``",
            "- Stage: final.",
            "- This is the frozen project baseline for subsequent project navigation.",
            "- Do not rebuild or incrementally update the graph during active implementation, review, testing, or validation.",
            '- Read `RULES.md`, `docs/project-graph-runbook.md`, and `graphify-out/baseline.json`.',
            '- Compare `indexed_source_commit` with the current branch and analyze the branch diff separately.',
            "- Refresh only at the approved post-archive graph checkpoint."
        ) -join "`r`n"
    }

    $pattern = "(?s)## Graph Freshness.*?(?=^## |\z)"
    if ($report -match $pattern) {
        $report = [regex]::Replace($report, $pattern, ($policy.TrimEnd() + "`r`n`r`n"), "Multiline")
    } else {
        $report = $report.TrimEnd() + "`r`n`r`n" + $policy.TrimEnd() + "`r`n"
    }
    $report = $report -replace [regex]::Escape($ForbiddenFreshnessAdvice), "frozen baseline refresh is controlled by project policy"
    $report = $report.TrimEnd()
    [System.IO.File]::WriteAllText($reportPath, $report, $Utf8NoBomStrict)
}

function Sanitize-GraphReport($GraphDir, $BuildRoot, $SourceCommit, $BaselineStage, $SourceRef, $TargetBranch) {
    $reportPath = Join-Path $GraphDir "GRAPH_REPORT.md"
    if (-not (Test-Path -LiteralPath $reportPath)) {
        return
    }
    $report = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8
    $buildFull = [System.IO.Path]::GetFullPath($BuildRoot).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    $buildForward = $buildFull.Replace("\", "/")
    $projectLabel = "diag-module-ref@$($SourceCommit.Substring(0, 12))"
    $report = $report.Replace($buildFull, $projectLabel).Replace($buildForward, $projectLabel)
    $report = $report.TrimEnd()
    [System.IO.File]::WriteAllText($reportPath, $report, $Utf8NoBomStrict)
    Set-FrozenGraphReportPolicy $GraphDir $SourceCommit $BaselineStage $SourceRef $TargetBranch

    $updated = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8
    if ($updated -match [regex]::Escape($ForbiddenFreshnessAdvice)) {
        Fail "GRAPH_REPORT.md still contains forbidden generated freshness advice."
    }
    if ($updated -notmatch "(Bootstrap|Final) Frozen Baseline Policy" -or $updated -notmatch "frozen project baseline") {
        Fail "GRAPH_REPORT.md does not contain the frozen baseline policy block."
    }
}

function Invoke-GraphifyBuild($BuildRoot) {
    Push-Location $BuildRoot
    try {
        & graphify extract $BuildRoot --code-only --no-viz
        if ($LASTEXITCODE -ne 0) {
            Fail "graphify extract failed."
        }

        & graphify cluster-only $BuildRoot --no-viz --no-label
        if ($LASTEXITCODE -ne 0) {
            Fail "graphify cluster-only failed."
        }
    } finally {
        Pop-Location
    }
}

function Invoke-GraphifyIncremental($BuildRoot) {
    Push-Location $BuildRoot
    try {
        & graphify check-update $BuildRoot
        if ($LASTEXITCODE -ne 0) {
            Fail "graphify check-update failed."
        }
        & graphify update $BuildRoot
        if ($LASTEXITCODE -ne 0) {
            Fail "graphify update failed."
        }
        & graphify cluster-only $BuildRoot --no-viz --no-label
        if ($LASTEXITCODE -ne 0) {
            Fail "graphify cluster-only after update failed."
        }
    } finally {
        Pop-Location
    }
}

function Get-NodeById($Graph, $Id) {
    foreach ($node in (Get-GraphNodes $Graph)) {
        if ([string]$node.id -eq $Id) {
            return $node
        }
    }
    return $null
}

function Get-LinkByIdentity($Graph, $Source, $Target, $Relation) {
    foreach ($link in (Get-GraphLinks $Graph)) {
        if ([string]$link.source -eq $Source -and [string]$link.target -eq $Target -and [string]$link.relation -eq $Relation) {
            return $link
        }
    }
    return $null
}

function Assert-SourceContains($SourceRoot, $Path, $Pattern, $Query) {
    $sourcePath = Join-Path $SourceRoot $Path
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        Fail "Smoke query '$Query' source missing: $Path"
    }
    $sourceText = Get-Content -LiteralPath $sourcePath -Raw -Encoding UTF8
    if ($sourceText -notmatch $Pattern) {
        Fail "Smoke query '$Query' was not confirmed in source path $Path."
    }
}

function Assert-SmokeNode($Graph, $SourceRoot, $Query, $Id, $Label, $SourcePath, $SourcePattern) {
    $node = Get-NodeById $Graph $Id
    if ($null -eq $node) {
        Fail "Smoke query '$Query' did not find node id $Id."
    }
    if ([string]$node.label -ne $Label) {
        Fail "Smoke query '$Query' matched wrong label for $Id."
    }
    if ([string]$node.source_file -ne $SourcePath) {
        Fail "Smoke query '$Query' matched wrong source path for $Id."
    }
    if ([string]$node.file_type -ne "code") {
        Fail "Smoke query '$Query' matched non-code node $Id."
    }
    Assert-SourceContains $SourceRoot $SourcePath $SourcePattern $Query
    return [pscustomobject]@{
        query = $Query
        matched_node_ids = @($Id)
        source_paths = @($SourcePath)
        edge_ids = @()
        edge_types = @()
        confidence = @("NODE")
        source_confirmed = $true
    }
}

function Assert-SmokeEdge($Graph, $SourceRoot, $Query, $SourceId, $TargetId, $Relation, $SourcePath, $SourcePattern) {
    $sourceNode = Get-NodeById $Graph $SourceId
    $targetNode = Get-NodeById $Graph $TargetId
    $link = Get-LinkByIdentity $Graph $SourceId $TargetId $Relation
    if ($null -eq $sourceNode -or $null -eq $targetNode -or $null -eq $link) {
        Fail "Smoke query '$Query' missing edge $SourceId --$Relation--> $TargetId."
    }
    $confidence = if ($link.PSObject.Properties.Name -contains "confidence" -and $link.confidence) { [string]$link.confidence } else { "NOT_AVAILABLE" }
    if ($confidence -eq "AMBIGUOUS") {
        Fail "Smoke query '$Query' found AMBIGUOUS evidence, which is not acceptable."
    }
    Assert-SourceContains $SourceRoot $SourcePath $SourcePattern $Query
    return [pscustomobject]@{
        query = $Query
        matched_node_ids = @($SourceId, $TargetId)
        source_paths = @($SourcePath)
        edge_ids = @("$SourceId|$Relation|$TargetId")
        edge_types = @($Relation)
        confidence = @($confidence)
        source_confirmed = $true
    }
}

function Invoke-SmokeQueries($SourceRoot, $Graph) {
    $results = @()
    $results += Assert-SmokeNode $Graph $SourceRoot "PDUController" "gui_pdu_controller_pducontroller" "PDUController" "gui/pdu_controller.py" "class\s+PDUController\b"
    $results += Assert-SmokeNode $Graph $SourceRoot "InteractiveSessionController" "core_interactive_session_interactivesessioncontroller" "InteractiveSessionController" "core/interactive_session.py" "class\s+InteractiveSessionController\b"
    $results += Assert-SmokeNode $Graph $SourceRoot "EquipmentInventory" "core_equipment_inventory_equipmentinventory" "EquipmentInventory" "core/equipment_inventory.py" "class\s+EquipmentInventory\b"
    $results += Assert-SmokeEdge $Graph $SourceRoot "credential fallback ownership" "core_interactive_session_interactivesessioncontroller_acquire_handler" "core_credentials_credentialattemptplan" "calls" "core/interactive_session.py" "CredentialAttemptPlan\(context\.candidates,\s*start_index\)"
    $results += Assert-SmokeEdge $Graph $SourceRoot "accepted PDU refresh to enrichment controller" "gui_main_window_vcsdiagnosticapp_on_pdu_refresh_accepted_for_enrichment" "gui_main_window_vcsdiagnosticapp_pdu_room_codec_controller" "calls" "gui/main_window.py" "_on_pdu_refresh_accepted_for_enrichment"
    $results += Assert-SmokeEdge $Graph $SourceRoot "related codec resolver navigation hint" "core_room_context_roomcontextresolver_resolve_related_codec" "core_equipment_inventory_equipmentinventory" "references" "core/room_context.py" "inventory\.find_by_ip\(pdu_ip_address\)"
    $results += Assert-SmokeEdge $Graph $SourceRoot "related codec status operation navigation hint" "gui_pdu_room_codec_enrichment_pduroomcodecenrichmentcontroller_handler_factory" "core_related_codec_status_relatedcodecstatusadapter_read_status" "indirect_call" "gui/pdu_room_codec_enrichment.py" "_status_adapter\.read_status\(related_handler,\s*expected_model\)"
    return $results
}

function Assert-GeneratedAllowlist($OutputRoot, $GraphDir) {
    $files = Get-ChildItem -LiteralPath $GraphDir -File -Recurse | ForEach-Object { RelPath $_.FullName $OutputRoot }
    $unexpected = @($files | Where-Object { $AllowedGenerated -notcontains $_ })
    if ($unexpected.Count -gt 0) {
        Fail ("Unexpected generated files: " + ($unexpected -join ", "))
    }
    foreach ($required in $AllowedGenerated) {
        if (-not (Test-Path -LiteralPath (Join-Path $OutputRoot $required))) {
            Fail "Required allowlisted output missing: $required"
        }
    }
}

function Assert-GeneratedCandidateBoundary($OutputRoot, $GraphDir) {
    $files = Get-ChildItem -LiteralPath $GraphDir -File -Recurse | ForEach-Object { RelPath $_.FullName $OutputRoot }
    $unexpected = @($files | Where-Object { $AllowedGenerated -notcontains $_ })
    if ($unexpected.Count -gt 0) {
        Fail ("Unexpected generated files before canonicalization: " + ($unexpected -join ", "))
    }

    foreach ($required in @("graphify-out/graph.json", "graphify-out/manifest.json", "graphify-out/GRAPH_REPORT.md")) {
        if (-not (Test-Path -LiteralPath (Join-Path $OutputRoot $required))) {
            Fail "Required generated candidate missing before canonicalization: $required"
        }
    }
}

function Assert-NoGraphifyIntegrations($OutputRoot) {
    $forbidden = @(
        "AGENTS.md",
        ".codex/hooks.json",
        ".codex/mcp.json",
        ".agents/skills/graphify",
        ".cursor/rules/graphify.mdc",
        ".cursor/mcp.json",
        ".kiro/skills/graphify",
        ".kiro/mcp.json",
        ".mcp",
        ".mcp.json",
        "mcp.json"
    )
    foreach ($item in $forbidden) {
        if (Test-Path -LiteralPath (Join-Path $OutputRoot $item)) {
            Fail "Forbidden Graphify integration present: $item"
        }
    }

    $hooksPath = (& git -C $OutputRoot rev-parse --git-path hooks 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -eq 0 -and $hooksPath) {
        $hooks = if ([System.IO.Path]::IsPathRooted($hooksPath)) {
            [System.IO.Path]::GetFullPath($hooksPath)
        } else {
            [System.IO.Path]::GetFullPath((Join-Path $OutputRoot $hooksPath))
        }
    } else {
        $hooks = Join-Path $OutputRoot ".git/hooks"
    }
    if (Test-Path -LiteralPath $hooks) {
        $hookHits = Get-ChildItem -LiteralPath $hooks -File -ErrorAction SilentlyContinue | Where-Object {
            $hookText = Get-Content -LiteralPath $_.FullName -Raw -ErrorAction SilentlyContinue
            $hookText -match "(?im)(^|[;&|]\s*)(exec\s+)?&?\s*['""]?graphify(\.exe)?['""]?(\s|$)" -or
                $hookText -match "(?i)\bgraphify(\.exe)?\s+(extract|update|check-update|watch|mcp)\b"
        }
        if (@($hookHits).Count -gt 0) {
            Fail "Graphify hook integration present in .git/hooks."
        }
    }

    $mergeDriverConfig = (& git -C $OutputRoot config --local --get-regexp "^merge\..*\.driver$" 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -eq 0 -and $mergeDriverConfig) {
        Fail "Repository-local merge driver configuration present."
    }
    if ($LASTEXITCODE -notin @(0, 1)) {
        Fail "Unable to inspect repository-local merge driver configuration: $mergeDriverConfig"
    }

    $gitattributes = Join-Path $OutputRoot ".gitattributes"
    if (Test-Path -LiteralPath $gitattributes -PathType Leaf) {
        $attributesText = Get-Content -LiteralPath $gitattributes -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        if ($attributesText -match "(?im)^\s*[^#\r\n]+\s+merge\s*=\s*graphify\b") {
            Fail "Graphify merge driver attribute present in .gitattributes."
        }
    }

    $documentaryPathPattern = "^(openspec|docs)/|^RULES\.md$|^tools/refresh_project_graph\.ps1$"
    $repoTextFiles = Get-ChildItem -LiteralPath $OutputRoot -File -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object {
            $rel = RelPath $_.FullName $OutputRoot
            $rel -notmatch "^(\.git|graphify-out|node_modules|$TempDirName)/" -and
                $rel -notmatch $documentaryPathPattern -and
                $_.Length -lt 1048576
        }
    foreach ($file in $repoTextFiles) {
        $rel = RelPath $file.FullName $OutputRoot
        $text = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        if ($text -match "(?i)\bgraphify(\.exe)?\s+(watch|mcp)\b") {
            Fail "Unexpected Graphify watch/MCP integration command in $rel."
        }
    }
}

function Write-Baseline($OutputRoot, $GraphDir, $SourceCommit, $BaselineStage, $SourceRef, $TargetBranch, $GraphifyVersion, $Graph, $GraphPath) {
    $counts = Count-Graph $Graph
    if ($counts.Nodes -le 0 -or $counts.Edges -le 0) {
        Fail "Graph must contain nonzero nodes and edges. Found nodes=$($counts.Nodes), edges=$($counts.Edges)."
    }

    $baseline = [ordered]@{
        schema_version = 2
        generator = "graphify"
        graphify_version = $GraphifyVersion
        mode = "code-only"
        baseline_stage = $BaselineStage
        indexed_source_commit = $SourceCommit
        indexed_source_ref = $SourceRef
        target_branch = $TargetBranch
        generated_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        graph_sha256 = Get-Sha256 $GraphPath
        ignore_file_sha256 = Get-Sha256 (Join-Path $OutputRoot ".graphifyignore")
        node_count = $counts.Nodes
        edge_count = $counts.Edges
    }

    $baselinePath = Join-Path $GraphDir "baseline.json"
    $baselineJson = $baseline | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText($baselinePath, $baselineJson, $Utf8NoBomStrict)
    ConvertTo-CanonicalGeneratedTextArtifact $GraphDir "baseline.json"
    return (Assert-Json $baselinePath)
}

function Assert-Metadata($OutputRoot, $SourceRoot, $GraphDir, $Graph, $Baseline, $SourceCommit, $BaselineStage, $SourceRef, $SourceRefSha, $TargetBranch, $Version) {
    $counts = Count-Graph $Graph
    $graphPath = Join-Path $GraphDir "graph.json"
    $ignorePath = Join-Path $OutputRoot ".graphifyignore"
    if ([int]$Baseline.schema_version -ne 2) { Fail "baseline.schema_version mismatch." }
    if ($Baseline.PSObject.Properties.Name -contains "indexed_branch") { Fail "baseline.indexed_branch is obsolete and must not be present." }
    if ($Baseline.generator -ne "graphify") { Fail "baseline.generator mismatch." }
    if ($Baseline.indexed_source_commit -ne $SourceCommit) { Fail "baseline.indexed_source_commit mismatch." }
    if ($Baseline.baseline_stage -ne $BaselineStage) { Fail "baseline.baseline_stage mismatch." }
    if ($Baseline.indexed_source_ref -ne $SourceRef) { Fail "baseline.indexed_source_ref mismatch." }
    if ($Baseline.target_branch -ne $TargetBranch) { Fail "baseline.target_branch mismatch." }
    if ((Get-GitSha $SourceRoot $SourceRef) -ne $SourceRefSha) { Fail "SourceRef no longer resolves to the generation source commit." }
    if ($Baseline.graphify_version -ne $Version) { Fail "baseline.graphify_version mismatch." }
    if ($Baseline.mode -ne "code-only") { Fail "baseline.mode mismatch." }
    if ($Baseline.graph_sha256 -ne (Get-Sha256 $graphPath)) { Fail "baseline.graph_sha256 mismatch." }
    if ($Baseline.ignore_file_sha256 -ne (Get-Sha256 $ignorePath)) { Fail "baseline.ignore_file_sha256 mismatch." }
    if ([int]$Baseline.node_count -ne [int]$counts.Nodes) { Fail "baseline.node_count mismatch." }
    if ([int]$Baseline.edge_count -ne [int]$counts.Edges) { Fail "baseline.edge_count mismatch." }
}

function Test-SourcePathInCorpus($Path) {
    return $Path -match "(?i)\.(py|json|toml|yaml|yml|js|ts|tsx|jsx|ps1|cmd|bat)$"
}

function Get-GitNameStatus($SourceRoot, $PreviousCommit, $CurrentCommit) {
    if ($PreviousCommit -eq $CurrentCommit) {
        return @()
    }
    $lines = @(& git -C $SourceRoot diff --name-status --find-renames $PreviousCommit $CurrentCommit)
    if ($LASTEXITCODE -ne 0) {
        Fail "Unable to compute source diff from $PreviousCommit to $CurrentCommit."
    }
    $changes = @()
    foreach ($line in $lines) {
        if (-not $line.Trim()) { continue }
        $parts = $line -split "`t"
        $status = $parts[0]
        if ($status -match "^R") {
            $changes += [pscustomobject]@{ Kind = "renamed"; OldPath = $parts[1].Replace("\", "/"); NewPath = $parts[2].Replace("\", "/") }
        } elseif ($status -eq "D") {
            $changes += [pscustomobject]@{ Kind = "deleted"; OldPath = $parts[1].Replace("\", "/"); NewPath = "" }
        } elseif ($status -eq "A") {
            $changes += [pscustomobject]@{ Kind = "added"; OldPath = ""; NewPath = $parts[1].Replace("\", "/") }
        } else {
            $changes += [pscustomobject]@{ Kind = "modified"; OldPath = ""; NewPath = $parts[1].Replace("\", "/") }
        }
    }
    return $changes
}

function Assert-IncrementalIntegrity($SourceRoot, $PreviousBaseline, $PreGraph, $PreManifest, $PostGraph, $PostManifest, $CurrentCommit) {
    $previousCommit = [string]$PreviousBaseline.indexed_source_commit
    $changes = @(Get-GitNameStatus $SourceRoot $previousCommit $CurrentCommit)
    $changedCount = [Math]::Max(1, $changes.Count)
    $deleteRenameCount = @($changes | Where-Object { $_.Kind -in @("deleted", "renamed") }).Count
    if ($changes.Count -gt $MaxChangedFilesForIncremental) {
        Fail "Incremental integrity rejected $($changes.Count) changed files; run FullRebuild."
    }
    if ($deleteRenameCount -gt $MaxDeletedOrRenamedFilesForIncremental) {
        Fail "Incremental integrity rejected $deleteRenameCount deleted/renamed files; run FullRebuild."
    }

    $postManifestPaths = @(Get-ManifestSourceSet $PostManifest)
    $postNodePaths = @(Get-GraphNodes $PostGraph | ForEach-Object { [string]$_.source_file } | Sort-Object -Unique)
    foreach ($change in $changes) {
        if ($change.Kind -eq "deleted") {
            if ($postManifestPaths -contains $change.OldPath -or $postNodePaths -contains $change.OldPath) {
                Fail "Ghost node/source path after deletion: $($change.OldPath); run FullRebuild."
            }
        }
        if ($change.Kind -eq "renamed") {
            if ($postManifestPaths -contains $change.OldPath -or $postNodePaths -contains $change.OldPath) {
                Fail "Ghost node/source path after rename: $($change.OldPath); run FullRebuild."
            }
            if ((Test-SourcePathInCorpus $change.NewPath) -and -not ($postManifestPaths -contains $change.NewPath)) {
                Fail "Renamed source path missing from post-update manifest: $($change.NewPath); run FullRebuild."
            }
        }
    }

    $changedPaths = @{}
    foreach ($change in $changes) {
        if ($change.OldPath) { $changedPaths[$change.OldPath] = $true }
        if ($change.NewPath) { $changedPaths[$change.NewPath] = $true }
    }
    $preUnchangedNodeIds = @(Get-GraphNodes $PreGraph | Where-Object {
        $path = [string]$_.source_file
            $path -and -not $changedPaths.ContainsKey($path)
    } | ForEach-Object { [string]$_.id } | Sort-Object -Unique)
    $postIds = @{}
    foreach ($id in (Get-NodeIdentitySet $PostGraph)) { $postIds[$id] = $true }
    $lost = @($preUnchangedNodeIds | Where-Object { -not $postIds.ContainsKey($_) })
    if ($lost.Count -gt 0) {
        Fail "Incremental update lost $($lost.Count) unchanged node identities; run FullRebuild."
    }

    $preCounts = Count-Graph $PreGraph
    $postCounts = Count-Graph $PostGraph
    $nodeDelta = [int]$postCounts.Nodes - [int]$preCounts.Nodes
    $edgeDelta = [int]$postCounts.Edges - [int]$preCounts.Edges
    if ([Math]::Abs($nodeDelta) -gt ($MaxNodeDeltaPerChangedFile * $changedCount)) {
        Fail "Unexpected topology node delta $nodeDelta for $($changes.Count) source changes; run FullRebuild."
    }
    if ([Math]::Abs($edgeDelta) -gt ($MaxEdgeDeltaPerChangedFile * $changedCount)) {
        Fail "Unexpected topology edge delta $edgeDelta for $($changes.Count) source changes; run FullRebuild."
    }

    return [pscustomobject]@{
        PreviousCommit = $previousCommit
        CurrentCommit = $CurrentCommit
        ChangedFiles = $changes.Count
        DeletedOrRenamed = $deleteRenameCount
        NodeDelta = $nodeDelta
        EdgeDelta = $edgeDelta
    }
}

function Assert-Candidate($SourceRoot, $OutputRoot, $BuildRoot, $GraphDir, $SourceCommit, $BaselineStage, $SourceRef, $SourceRefSha, $TargetBranch, $Version) {
    $graphPath = Join-Path $GraphDir "graph.json"
    $manifestPath = Join-Path $GraphDir "manifest.json"
    $reportPath = Join-Path $GraphDir "GRAPH_REPORT.md"
    foreach ($required in @($graphPath, $manifestPath, $reportPath)) {
        if (-not (Test-Path -LiteralPath $required)) {
            Fail "Required Graphify output missing: $required"
        }
    }

    Remove-UncommittedGraphifyByproducts $GraphDir
    Assert-GeneratedCandidateBoundary (Split-Path -Parent $GraphDir) $GraphDir
    foreach ($artifact in @("graph.json", "manifest.json", "GRAPH_REPORT.md")) {
        ConvertTo-CanonicalGeneratedTextArtifact $GraphDir $artifact
    }
    Sanitize-GraphReport $GraphDir $BuildRoot $SourceCommit $BaselineStage $SourceRef $TargetBranch
    ConvertTo-CanonicalGeneratedTextArtifact $GraphDir "GRAPH_REPORT.md"

    $graph = Assert-Json $graphPath
    $manifest = Assert-Json $manifestPath
    $baseline = Write-Baseline $OutputRoot $GraphDir $SourceCommit $BaselineStage $SourceRef $TargetBranch $Version $graph $graphPath
    $baseline = Assert-Json (Join-Path $GraphDir "baseline.json")

    Assert-GeneratedAllowlist (Split-Path -Parent $GraphDir) $GraphDir
    Assert-SecretScan $GraphDir $graph $manifest $baseline
    Assert-Metadata $OutputRoot $SourceRoot $GraphDir $graph $baseline $SourceCommit $BaselineStage $SourceRef $SourceRefSha $TargetBranch $Version
    $smoke = Invoke-SmokeQueries $SourceRoot $graph
    $confidence = Get-ConfidenceSummary $graph

    return [pscustomobject]@{
        Graph = $graph
        Manifest = $manifest
        Baseline = $baseline
        Smoke = $smoke
        Confidence = $confidence
    }
}

function Publish-ValidatedGraph($OutputRoot, $CandidateGraphDir) {
    $target = Join-Path $OutputRoot $GraphDirName
    $tempParent = Join-Path $OutputRoot $TempDirName
    $backup = Join-Path $tempParent "accepted-backup-$PID-$([Guid]::NewGuid().ToString('N'))"

    try {
        if (Test-Path -LiteralPath $target) {
            Copy-Item -LiteralPath $target -Destination $backup -Recurse -Force
            Remove-Item -LiteralPath $target -Recurse -Force
        }
        New-Item -ItemType Directory -Path $target -Force | Out-Null
        foreach ($file in @("graph.json", "manifest.json", "GRAPH_REPORT.md", "baseline.json")) {
            Copy-Item -LiteralPath (Join-Path $CandidateGraphDir $file) -Destination (Join-Path $target $file) -Force
        }
    } catch {
        if (Test-Path -LiteralPath $target) {
            Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction SilentlyContinue
        }
        if (Test-Path -LiteralPath $backup) {
            Copy-Item -LiteralPath $backup -Destination $target -Recurse -Force
        }
        Fail "Validated graph publication failed; previous accepted output was restored from backup: $($_.Exception.Message)"
    }
}

function Remove-TempOutputs($OutputRoot) {
    $tempParent = Join-Path $OutputRoot $TempDirName
    if (Test-Path -LiteralPath $tempParent) {
        Remove-Item -LiteralPath $tempParent -Recurse -Force
    }
}

$invocationRoot = Get-RepoRootFrom "."
$outputRootFull = if ($OutputRoot) { Get-RepoRootFrom $OutputRoot } else { $invocationRoot }
$sourceRootFull = if ($SourceRoot) { Get-RepoRootFrom $SourceRoot } else { $outputRootFull }

if (-not (Test-Path -LiteralPath (Join-Path $outputRootFull "RULES.md")) -or
    -not (Test-Path -LiteralPath (Join-Path $outputRootFull "openspec.cmd"))) {
    Fail "Output repository root verification failed."
}

if ($Mode -eq "InstallExact") {
    & uv tool install "graphifyy==$ExpectedGraphifyVersion"
    exit $LASTEXITCODE
}

Assert-GraphifyIgnore $outputRootFull

$baselineStageValue = Get-BaselineStageValue $BaselineStage
$sourceCommit = Get-GitSha $sourceRootFull "HEAD"
$sourceRefSha = Get-GitSha $sourceRootFull $SourceRef
if ($sourceCommit -ne $sourceRefSha) {
    Fail "Source HEAD must equal SourceRef. source=$sourceCommit SourceRef($SourceRef)=$sourceRefSha"
}
if ($baselineStageValue -eq "final") {
    Assert-FinalSourceContainsGraphifyTooling $sourceRootFull
    Assert-FinalWorkflowGate $sourceRootFull $sourceCommit $PostArchiveValidationEvidence
}
Assert-CleanGit $sourceRootFull "Source"

$version = Get-GraphVersion
if ($version -ne $ExpectedGraphifyVersion) {
    Fail "Graphify version mismatch. Expected $ExpectedGraphifyVersion, got $version."
}

Remove-TempOutputs $outputRootFull
$buildRoot = $null
$candidateGraphDir = $null
$result = $null
$incrementalEvidence = $null

try {
    $buildRoot = New-BuildCopy $sourceRootFull $outputRootFull
    $candidateGraphDir = Join-Path $buildRoot $GraphDirName

    if ($Mode -eq "Initial") {
        Invoke-GraphifyBuild $buildRoot
    } elseif ($Mode -eq "FullRebuild") {
        Invoke-GraphifyBuild $buildRoot
    } elseif ($Mode -eq "Incremental") {
        $acceptedGraphDir = Join-Path $outputRootFull $GraphDirName
        $acceptedBaselinePath = Join-Path $acceptedGraphDir "baseline.json"
        if (-not (Test-Path -LiteralPath $acceptedBaselinePath)) {
            Fail "Accepted baseline is required for incremental mode."
        }
        Copy-Item -LiteralPath $acceptedGraphDir -Destination $candidateGraphDir -Recurse -Force
        $preGraph = Assert-Json (Join-Path $candidateGraphDir "graph.json")
        $preManifest = Assert-Json (Join-Path $candidateGraphDir "manifest.json")
        $previousBaseline = Assert-Json $acceptedBaselinePath
        Invoke-GraphifyIncremental $buildRoot
        $postGraph = Assert-Json (Join-Path $candidateGraphDir "graph.json")
        $postManifest = Assert-Json (Join-Path $candidateGraphDir "manifest.json")
        $incrementalEvidence = Assert-IncrementalIntegrity $sourceRootFull $previousBaseline $preGraph $preManifest $postGraph $postManifest $sourceCommit
    }

    $result = Assert-Candidate $sourceRootFull $outputRootFull $buildRoot $candidateGraphDir $sourceCommit $baselineStageValue $SourceRef $sourceRefSha $TargetBranch $version
    Publish-ValidatedGraph $outputRootFull $candidateGraphDir
} finally {
    Remove-TempOutputs $outputRootFull
}

$acceptedGraphDir = Join-Path $outputRootFull $GraphDirName
$acceptedGraph = Assert-Json (Join-Path $acceptedGraphDir "graph.json")
$acceptedManifest = Assert-Json (Join-Path $acceptedGraphDir "manifest.json")
$acceptedBaseline = Assert-Json (Join-Path $acceptedGraphDir "baseline.json")
Assert-GeneratedAllowlist $outputRootFull $acceptedGraphDir
Assert-SecretScan $acceptedGraphDir $acceptedGraph $acceptedManifest $acceptedBaseline
Assert-Metadata $outputRootFull $sourceRootFull $acceptedGraphDir $acceptedGraph $acceptedBaseline $sourceCommit $baselineStageValue $SourceRef $sourceRefSha $TargetBranch $version
Assert-NoGraphifyIntegrations $outputRootFull
Assert-CleanGit $sourceRootFull "Source"

Write-Host "Graphify version: $version"
Write-Host "Baseline stage: $baselineStageValue"
Write-Host "Indexed source commit: $sourceCommit"
Write-Host "Indexed source ref: $SourceRef"
Write-Host "Target branch: $TargetBranch"
Write-Host "Mode: code-only"
Write-Host "No-viz: true"
Write-Host "Graph SHA-256: $($acceptedBaseline.graph_sha256)"
Write-Host "Ignore SHA-256: $($acceptedBaseline.ignore_file_sha256)"
Write-Host "Node count: $($acceptedBaseline.node_count)"
Write-Host "Edge count: $($acceptedBaseline.edge_count)"
if ($null -ne $incrementalEvidence) {
    Write-Host "Incremental source range: $($incrementalEvidence.PreviousCommit) -> $($incrementalEvidence.CurrentCommit)"
    Write-Host "Incremental changed files: $($incrementalEvidence.ChangedFiles)"
    Write-Host "Incremental deleted/renamed files: $($incrementalEvidence.DeletedOrRenamed)"
    Write-Host "Incremental node delta: $($incrementalEvidence.NodeDelta)"
    Write-Host "Incremental edge delta: $($incrementalEvidence.EdgeDelta)"
}
Write-Host "Confidence summary:"
foreach ($key in ($result.Confidence.Keys | Sort-Object)) {
    Write-Host "  $key=$($result.Confidence[$key])"
}
Write-Host "Smoke queries:"
foreach ($item in $result.Smoke) {
    Write-Host "  query=$($item.query)"
    Write-Host "    matched node ids=$(@($item.matched_node_ids) -join ', ')"
    Write-Host "    source paths=$(@($item.source_paths) -join ', ')"
    Write-Host "    edge ids=$(@($item.edge_ids) -join ', ')"
    Write-Host "    edge types=$(@($item.edge_types) -join ', ')"
    Write-Host "    confidence=$(@($item.confidence) -join ', ')"
    Write-Host "    source-confirmed=$($item.source_confirmed)"
}

exit 0
