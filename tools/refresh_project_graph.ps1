param(
    [ValidateSet("Incremental", "FullRebuild", "InstallExact")]
    [string]$Mode = "FullRebuild",
    [string]$SourceRef = "origin/master",
    [string]$TargetBranch = "master",
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
$BaselineStage = "final"
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
$GraphSchemaContract = "graphify-0.9.26-graph-json-structural-v1"
$ManifestSchemaContract = "graphify-0.9.26-manifest-json-map-v1"
$BaselineMetadataContract = "diag-project-graph-baseline-v3"
$IndexedSourceRootPolicy = "repo-root-code-config-v1;extensions=py,json,toml,yaml,yml,js,ts,tsx,jsx,ps1,cmd,bat;exclude=graphify-out,openspec/changes/archive,node_modules,.worktrees,logs,transfer,inventory,excel,credentials,secrets"
$PackageBoundaryPolicy = "graphify-default-repository-package-boundaries-v1;python-packages-by-__init__;repo-root-tools-docs-excluded-by-policy"

function Fail($Message) {
    throw $Message
}

function RelPath($Path, $Root) {
    $full = [System.IO.Path]::GetFullPath($Path)
    $base = [System.IO.Path]::GetFullPath($Root)
    $uriBase = [System.Uri]::new($base.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar)
    $uriFull = [System.Uri]::new($full)
    return [System.Uri]::UnescapeDataString($uriBase.MakeRelativeUri($uriFull).ToString()).Replace("\", "/")
}

function Get-RepoRootFrom($Path) {
    if (-not $Path) {
        Fail "Repository path is required."
    }
    $root = (& git -C $Path rev-parse --show-toplevel 2>$null)
    if ($LASTEXITCODE -ne 0 -or -not $root) {
        Fail "Not inside a Git repository: $Path"
    }
    return [System.IO.Path]::GetFullPath($root.Trim())
}

function Get-Sha256($Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Get-Sha256ForText($Text) {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes([string]$Text)
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        $sha = $hasher.ComputeHash($bytes)
        return ([System.BitConverter]::ToString($sha).Replace("-", "").ToLowerInvariant())
    } finally {
        $hasher.Dispose()
    }
}

function Get-GraphPolicyIdentity($SourceRoot, $IgnorePolicySha256) {
    $gitattributesPath = Join-Path $SourceRoot ".gitattributes"
    if (-not (Test-Path -LiteralPath $gitattributesPath -PathType Leaf)) {
        Fail ".gitattributes is required for graph policy identity."
    }
    [void](Invoke-GitChecked $SourceRoot @("cat-file", "-e", "HEAD:.gitattributes") ".gitattributes must exist in source HEAD")
    $headBlob = Invoke-GitChecked $SourceRoot @("rev-parse", "HEAD:.gitattributes") "Unable to read source HEAD .gitattributes blob"
    $workingBlob = Invoke-GitChecked $SourceRoot @("hash-object", "--path=.gitattributes", "--", $gitattributesPath) "Unable to hash source .gitattributes after repository filters"
    if ($headBlob -ne $workingBlob) {
        Fail "SourceRoot .gitattributes must match committed source bytes after repository filters."
    }

    $identity = [ordered]@{
        graph_schema_contract = $GraphSchemaContract
        manifest_schema_contract = $ManifestSchemaContract
        baseline_metadata_contract = $BaselineMetadataContract
        indexed_source_root_policy = $IndexedSourceRootPolicy
        package_boundary_policy = $PackageBoundaryPolicy
        ignore_file_sha256 = $IgnorePolicySha256
        gitattributes_sha256 = Get-Sha256 $gitattributesPath
        indexed_source_root_policy_sha256 = Get-Sha256ForText $IndexedSourceRootPolicy
        package_boundary_policy_sha256 = Get-Sha256ForText $PackageBoundaryPolicy
        graph_schema_contract_sha256 = Get-Sha256ForText $GraphSchemaContract
        manifest_schema_contract_sha256 = Get-Sha256ForText $ManifestSchemaContract
        baseline_metadata_contract_sha256 = Get-Sha256ForText $BaselineMetadataContract
    }
    $composite = ($identity.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "`n"
    $identity.policy_fingerprint_sha256 = Get-Sha256ForText $composite
    return [pscustomobject]$identity
}

function Invoke-GitChecked($Root, $Arguments, $FailureMessage) {
    $output = (& git -C $Root @Arguments 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail "$FailureMessage`: $output"
    }
    return $output
}

function Get-GitSha($Root, $Ref) {
    $sha = (& git -C $Root rev-parse $Ref 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $sha -notmatch "^[0-9a-f]{40}$") {
        Fail "Unable to resolve Git ref '$Ref'."
    }
    return $sha
}

function Assert-CleanGit($Root, $Purpose) {
    $status = (& git -C $Root status --short 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail "git status failed for $Purpose worktree."
    }
    if ($status) {
        Fail "$Purpose worktree is not clean."
    }
}

function Assert-SameExactBase($SourceRoot, $OutputRoot, $SourceRef) {
    $sourceFull = [System.IO.Path]::GetFullPath($SourceRoot).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    $outputFull = [System.IO.Path]::GetFullPath($OutputRoot).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    if ([string]::Equals($sourceFull, $outputFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        Fail "SourceRoot and OutputRoot must be distinct Git worktrees."
    }

    Assert-CleanGit $SourceRoot "Source"
    Assert-CleanGit $OutputRoot "Output"

    $sourceCommit = Get-GitSha $SourceRoot "HEAD"
    $sourceRefSha = Get-GitSha $SourceRoot $SourceRef
    $outputCommit = Get-GitSha $OutputRoot "HEAD"

    if ($sourceCommit -ne $sourceRefSha) {
        Fail "SourceRef must resolve to SourceRoot HEAD."
    }
    if ($outputCommit -ne $sourceCommit) {
        Fail "OutputRoot HEAD must equal source commit S."
    }

    & git -C $OutputRoot diff --quiet $sourceCommit --
    if ($LASTEXITCODE -ne 0) {
        Fail "OutputRoot has a pre-existing diff from source commit S."
    }

    return [pscustomobject]@{
        SourceCommit = $sourceCommit
        SourceRefSha = $sourceRefSha
    }
}

function Assert-TargetBranch($TargetBranch) {
    if ($TargetBranch -ne "master") {
        Fail "TargetBranch must be master for the approved graph maintenance workflow."
    }
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

function Assert-Json($Path) {
    try {
        $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
        return $raw | ConvertFrom-Json
    } catch {
        Fail "Invalid JSON: $(Split-Path -Leaf $Path)"
    }
}

function Count-Graph($Graph) {
    $nodes = @(Get-GraphNodes $Graph)
    $edges = @(Get-GraphLinks $Graph)
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

function Test-JsonObject($Value) {
    return $Value -is [System.Management.Automation.PSCustomObject]
}

function Test-JsonArray($Value) {
    return ($Value -is [System.Array]) -or ($Value -is [System.Collections.IList] -and -not ($Value -is [string]))
}

function Assert-StringField($Object, $Field, $Purpose) {
    if (-not (Test-JsonObject $Object) -or -not ($Object.PSObject.Properties.Name -contains $Field)) {
        Fail "$Purpose schema mismatch: missing $Field."
    }
    $value = $Object.$Field
    if (-not ($value -is [string]) -or -not $value) {
        Fail "$Purpose schema mismatch: $Field must be a non-empty string."
    }
    return [string]$value
}

function Assert-RepoRelativePath($Path, $Purpose) {
    if (-not $Path) {
        Fail "$Purpose path is empty."
    }
    if ([System.IO.Path]::IsPathRooted($Path) -or $Path -match "^[A-Za-z]:[\\/]" -or $Path -match "^\\\\" -or $Path -match "(^|/)\.\.(/|$)") {
        Fail "$Purpose path must be repository-relative."
    }
    if ($Path -match "^(graphify-out|openspec/changes/archive|node_modules|\.worktrees|logs|transfer|diag-module-ref-pdu-archive|diag-module-ref-pdu-implementation)(/|$)") {
        Fail "$Purpose path is outside the approved source corpus."
    }
    if ($Path -match "(?i)(equipment_inventory\.local\.json|credentials\.local|\.xlsx$|\.xls$|\.env($|\.))") {
        Fail "$Purpose path is excluded from the graph corpus."
    }
}

function Test-SourcePathInCorpus($Path) {
    return $Path -match "(?i)\.(py|json|toml|yaml|yml|js|ts|tsx|jsx|ps1|cmd|bat)$"
}

function Assert-CurrentCorpusPaths($SourceRoot, $Manifest, $Graph) {
    foreach ($path in (Get-ManifestSourceSet $Manifest)) {
        Assert-RepoRelativePath $path "manifest source"
        if (-not (Test-SourcePathInCorpus $path)) {
            Fail "Manifest source path is not an approved code/config file."
        }
        if (-not (Test-Path -LiteralPath (Join-Path $SourceRoot $path) -PathType Leaf)) {
            Fail "Manifest source path is not present in SourceRoot."
        }
    }

    foreach ($node in (Get-GraphNodes $Graph)) {
        if ($node.PSObject.Properties.Name -contains "source_file" -and $node.source_file) {
            $path = ([string]$node.source_file).Replace("\", "/")
            Assert-RepoRelativePath $path "graph node source"
            if (-not (Test-Path -LiteralPath (Join-Path $SourceRoot $path) -PathType Leaf)) {
                Fail "Graph node source path is not present in SourceRoot."
            }
        }
    }
}

function Assert-GraphStructure($Graph, $Manifest) {
    if (-not (Test-JsonObject $Graph)) {
        Fail "graph.json schema mismatch: root must be an object."
    }
    if (-not ($Graph.PSObject.Properties.Name -contains "nodes") -or -not (Test-JsonArray $Graph.nodes)) {
        Fail "graph.json schema mismatch: nodes must be an array."
    }
    $edgeProperty = ""
    if ($Graph.PSObject.Properties.Name -contains "links") {
        $edgeProperty = "links"
    } elseif ($Graph.PSObject.Properties.Name -contains "edges") {
        $edgeProperty = "edges"
    } else {
        Fail "graph.json schema mismatch: links or edges array is required."
    }
    if (-not (Test-JsonArray $Graph.$edgeProperty)) {
        Fail "graph.json schema mismatch: edge collection must be an array."
    }

    if (-not (Test-JsonObject $Manifest)) {
        Fail "manifest.json schema mismatch: root must be an object map."
    }
    if (@($Manifest.PSObject.Properties.Name).Count -le 0) {
        Fail "manifest.json schema mismatch: source map must be non-empty."
    }
    foreach ($prop in $Manifest.PSObject.Properties) {
        $path = [string]$prop.Name
        Assert-RepoRelativePath $path "manifest source"
        if (-not (Test-JsonObject $prop.Value)) {
            Fail "manifest.json schema mismatch: each source entry must be an object."
        }
        if ($prop.Value.PSObject.Properties.Name -contains "symbols") {
            if (-not (Test-JsonArray $prop.Value.symbols)) {
                Fail "manifest.json schema mismatch: symbols must be an array."
            }
            foreach ($symbol in @($prop.Value.symbols)) {
                if (-not ($symbol -is [string]) -or -not $symbol) {
                    Fail "manifest.json schema mismatch: symbol entries must be non-empty strings."
                }
            }
        }
    }

    $nodes = @(Get-GraphNodes $Graph)
    $links = @(Get-GraphLinks $Graph)
    if ($nodes.Count -le 0 -or $links.Count -le 0) {
        Fail "Graph must contain nonzero nodes and edges. Found nodes=$($nodes.Count), edges=$($links.Count)."
    }

    $ids = @{}
    foreach ($node in $nodes) {
        if (-not (Test-JsonObject $node)) {
            Fail "graph.json schema mismatch: each node must be an object."
        }
        $id = Assert-StringField $node "id" "graph node"
        if ($node.PSObject.Properties.Name -contains "label" -and $null -ne $node.label -and -not ($node.label -is [string])) {
            Fail "graph node schema mismatch: label must be a string when present."
        }
        if ($node.PSObject.Properties.Name -contains "source_file" -and $null -ne $node.source_file -and -not ($node.source_file -is [string])) {
            Fail "graph node schema mismatch: source_file must be a string when present."
        }
        if ($node.PSObject.Properties.Name -contains "file_type" -and $null -ne $node.file_type -and -not ($node.file_type -is [string])) {
            Fail "graph node schema mismatch: file_type must be a string when present."
        }
        if ($ids.ContainsKey($id)) {
            Fail "Graph contains duplicate node id."
        }
        $ids[$id] = $true
    }

    foreach ($link in $links) {
        if (-not (Test-JsonObject $link)) {
            Fail "graph.json schema mismatch: each edge must be an object."
        }
        $source = Assert-StringField $link "source" "graph edge"
        $target = Assert-StringField $link "target" "graph edge"
        if ($link.PSObject.Properties.Name -contains "relation" -and $null -ne $link.relation -and -not ($link.relation -is [string])) {
            Fail "graph edge schema mismatch: relation must be a string when present."
        }
        if (-not $ids.ContainsKey($source) -or -not $ids.ContainsKey($target)) {
            Fail "Graph edge contains broken internal node reference."
        }
    }
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
        if ($value -match "(?i)\.(xlsx|xls)\b") { Add-SecretFinding $findings $Artifact $jsonPath "excel-path" $value }
        if ($value -match "(^|/|\\)\.worktrees($|/|\\)|(^|/|\\)$TempDirName($|/|\\)") { Add-SecretFinding $findings $Artifact $jsonPath "temporary-worktree-path" $value }
        if ($value -match "(^|/|\\)graphify-out($|/|\\)") { Add-SecretFinding $findings $Artifact $jsonPath "graph-output-self-indexing" $value }
        if (-not $isKnownHashField -and $value.Length -ge 40 -and $value -match "^[A-Za-z0-9_./+=-]+$" -and (Get-ShannonEntropy $value) -ge 4.5) {
            Add-SecretFinding $findings $Artifact $jsonPath "high-entropy-token-like-value" $value
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
        Fail "Generated graph artifacts failed secret/path scan."
    }
}

function Assert-SourceGraphifyIgnore($SourceRoot) {
    $ignorePath = Join-Path $SourceRoot ".graphifyignore"
    if (-not (Test-Path -LiteralPath $ignorePath -PathType Leaf)) {
        Fail ".graphifyignore is required in SourceRoot."
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
            Fail ".graphifyignore is missing required source-policy rule."
        }
    }
    if ($text -match "[A-Za-z]:\\|/Users/|/home/|/tmp/") {
        Fail ".graphifyignore contains a user-specific absolute path."
    }

    [void](Invoke-GitChecked $SourceRoot @("cat-file", "-e", "HEAD:.graphifyignore") ".graphifyignore must exist in source HEAD")
    $headBlob = Invoke-GitChecked $SourceRoot @("rev-parse", "HEAD:.graphifyignore") "Unable to read source HEAD .graphifyignore blob"
    $workingBlob = Invoke-GitChecked $SourceRoot @("hash-object", "--path=.graphifyignore", "--", $ignorePath) "Unable to hash source .graphifyignore after repository filters"
    if ($headBlob -ne $workingBlob) {
        Fail "SourceRoot .graphifyignore must match committed source bytes after repository filters."
    }
    return [pscustomobject]@{
        Path = $ignorePath
        Sha256 = Get-Sha256 $ignorePath
    }
}

function New-TempRoot($OutputRoot) {
    $tempParent = Join-Path ([System.IO.Path]::GetTempPath()) "diag-project-graph-refresh"
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

function Set-FrozenGraphReportPolicy($GraphDir, $SourceCommit, $SourceRef, $TargetBranch) {
    $reportPath = Join-Path $GraphDir "GRAPH_REPORT.md"
    if (-not (Test-Path -LiteralPath $reportPath)) {
        return
    }

    $report = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8
    $policy = @(
        "## Final Frozen Baseline Policy",
        "- Built from stable source commit: ``$SourceCommit``",
        "- Indexed source ref: ``$SourceRef``",
        "- Target branch: ``$TargetBranch``",
        "- Stage: final.",
        "- This graph is optional frozen navigation data, not validation evidence.",
        "- Ordinary OpenSpec changes do not rebuild or repair it.",
        "- Refresh only as separately authorized graph maintenance from exact source ``S`` to graph-only commit ``G``.",
        '- Read `RULES.md`, `docs/project-graph-runbook.md`, and `graphify-out/baseline.json`.',
        '- Compare `indexed_source_commit` with current branches and analyze diffs separately.'
    ) -join "`r`n"

    $pattern = "(?s)## (Bootstrap|Final) Frozen Baseline Policy.*?(?=^## |\z)"
    if ($report -match $pattern) {
        $report = [regex]::Replace($report, $pattern, ($policy.TrimEnd() + "`r`n`r`n"), "Multiline")
    } else {
        $report = $report.TrimEnd() + "`r`n`r`n" + $policy.TrimEnd() + "`r`n"
    }
    $report = $report -replace [regex]::Escape($ForbiddenFreshnessAdvice), "frozen baseline refresh is controlled by project policy"
    $report = $report.TrimEnd()
    [System.IO.File]::WriteAllText($reportPath, $report, $Utf8NoBomStrict)
}

function Sanitize-GraphReport($GraphDir, $BuildRoot, $SourceCommit, $SourceRef, $TargetBranch) {
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
    Set-FrozenGraphReportPolicy $GraphDir $SourceCommit $SourceRef $TargetBranch

    $updated = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8
    if ($updated -match [regex]::Escape($ForbiddenFreshnessAdvice)) {
        Fail "GRAPH_REPORT.md still contains forbidden generated freshness advice."
    }
    if ($updated -notmatch "Final Frozen Baseline Policy") {
        Fail "GRAPH_REPORT.md does not contain the final frozen baseline policy block."
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
        Fail "Unable to inspect repository-local merge driver configuration."
    }

    $gitattributes = Join-Path $OutputRoot ".gitattributes"
    if (Test-Path -LiteralPath $gitattributes -PathType Leaf) {
        $attributesText = Get-Content -LiteralPath $gitattributes -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        if ($attributesText -match "(?im)^\s*[^#\r\n]+\s+merge\s*=\s*graphify\b") {
            Fail "Graphify merge driver attribute present in .gitattributes."
        }
    }
}

function Write-Baseline($GraphDir, $SourceCommit, $SourceRef, $TargetBranch, $GraphifyVersion, $Graph, $GraphPath, $PolicyIdentity) {
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
        ignore_file_sha256 = $PolicyIdentity.ignore_file_sha256
        gitattributes_sha256 = $PolicyIdentity.gitattributes_sha256
        indexed_source_root_policy = $PolicyIdentity.indexed_source_root_policy
        indexed_source_root_policy_sha256 = $PolicyIdentity.indexed_source_root_policy_sha256
        package_boundary_policy = $PolicyIdentity.package_boundary_policy
        package_boundary_policy_sha256 = $PolicyIdentity.package_boundary_policy_sha256
        graph_schema_contract = $PolicyIdentity.graph_schema_contract
        graph_schema_contract_sha256 = $PolicyIdentity.graph_schema_contract_sha256
        manifest_schema_contract = $PolicyIdentity.manifest_schema_contract
        manifest_schema_contract_sha256 = $PolicyIdentity.manifest_schema_contract_sha256
        baseline_metadata_contract = $PolicyIdentity.baseline_metadata_contract
        baseline_metadata_contract_sha256 = $PolicyIdentity.baseline_metadata_contract_sha256
        policy_fingerprint_sha256 = $PolicyIdentity.policy_fingerprint_sha256
        node_count = $counts.Nodes
        edge_count = $counts.Edges
    }

    $baselinePath = Join-Path $GraphDir "baseline.json"
    $baselineJson = $baseline | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText($baselinePath, $baselineJson, $Utf8NoBomStrict)
    ConvertTo-CanonicalGeneratedTextArtifact $GraphDir "baseline.json"
    return (Assert-Json $baselinePath)
}

function Assert-Metadata($SourceRoot, $GraphDir, $Graph, $Baseline, $SourceCommit, $SourceRef, $SourceRefSha, $TargetBranch, $Version, $PolicyIdentity) {
    $counts = Count-Graph $Graph
    $graphPath = Join-Path $GraphDir "graph.json"
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
    if ($Baseline.ignore_file_sha256 -ne $PolicyIdentity.ignore_file_sha256) { Fail "baseline.ignore_file_sha256 mismatch." }
    if ($Baseline.gitattributes_sha256 -ne $PolicyIdentity.gitattributes_sha256) { Fail "baseline.gitattributes_sha256 mismatch." }
    if ($Baseline.indexed_source_root_policy -ne $PolicyIdentity.indexed_source_root_policy) { Fail "baseline.indexed_source_root_policy mismatch." }
    if ($Baseline.indexed_source_root_policy_sha256 -ne $PolicyIdentity.indexed_source_root_policy_sha256) { Fail "baseline.indexed_source_root_policy_sha256 mismatch." }
    if ($Baseline.package_boundary_policy -ne $PolicyIdentity.package_boundary_policy) { Fail "baseline.package_boundary_policy mismatch." }
    if ($Baseline.package_boundary_policy_sha256 -ne $PolicyIdentity.package_boundary_policy_sha256) { Fail "baseline.package_boundary_policy_sha256 mismatch." }
    if ($Baseline.graph_schema_contract -ne $PolicyIdentity.graph_schema_contract) { Fail "baseline.graph_schema_contract mismatch." }
    if ($Baseline.graph_schema_contract_sha256 -ne $PolicyIdentity.graph_schema_contract_sha256) { Fail "baseline.graph_schema_contract_sha256 mismatch." }
    if ($Baseline.manifest_schema_contract -ne $PolicyIdentity.manifest_schema_contract) { Fail "baseline.manifest_schema_contract mismatch." }
    if ($Baseline.manifest_schema_contract_sha256 -ne $PolicyIdentity.manifest_schema_contract_sha256) { Fail "baseline.manifest_schema_contract_sha256 mismatch." }
    if ($Baseline.baseline_metadata_contract -ne $PolicyIdentity.baseline_metadata_contract) { Fail "baseline.baseline_metadata_contract mismatch." }
    if ($Baseline.baseline_metadata_contract_sha256 -ne $PolicyIdentity.baseline_metadata_contract_sha256) { Fail "baseline.baseline_metadata_contract_sha256 mismatch." }
    if ($Baseline.policy_fingerprint_sha256 -ne $PolicyIdentity.policy_fingerprint_sha256) { Fail "baseline.policy_fingerprint_sha256 mismatch." }
    if ([int]$Baseline.node_count -ne [int]$counts.Nodes) { Fail "baseline.node_count mismatch." }
    if ([int]$Baseline.edge_count -ne [int]$counts.Edges) { Fail "baseline.edge_count mismatch." }
}

function Get-GitNameStatus($SourceRoot, $PreviousCommit, $CurrentCommit) {
    if ($PreviousCommit -eq $CurrentCommit) {
        return @()
    }
    $lines = @(& git -C $SourceRoot diff --name-status --find-renames $PreviousCommit $CurrentCommit)
    if ($LASTEXITCODE -ne 0) {
        Fail "Unable to compute source diff for incremental mode."
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

function Assert-PolicyField($Baseline, $Field, $ExpectedValue) {
    if (-not ($Baseline.PSObject.Properties.Name -contains $Field)) {
        Fail "Incremental requires baseline.$Field; run FullRebuild."
    }
    if ([string]$Baseline.$Field -ne [string]$ExpectedValue) {
        Fail "Incremental policy mismatch for $Field; run FullRebuild."
    }
}

function Assert-IncrementalPreconditions($PreviousBaseline, $PolicyIdentity, $Version) {
    if ([int]$PreviousBaseline.schema_version -ne 2) { Fail "Incremental requires previous schema version 2." }
    if ($PreviousBaseline.graphify_version -ne $Version) { Fail "Incremental requires unchanged Graphify version; run FullRebuild." }
    Assert-PolicyField $PreviousBaseline "ignore_file_sha256" $PolicyIdentity.ignore_file_sha256
    Assert-PolicyField $PreviousBaseline "gitattributes_sha256" $PolicyIdentity.gitattributes_sha256
    Assert-PolicyField $PreviousBaseline "indexed_source_root_policy" $PolicyIdentity.indexed_source_root_policy
    Assert-PolicyField $PreviousBaseline "indexed_source_root_policy_sha256" $PolicyIdentity.indexed_source_root_policy_sha256
    Assert-PolicyField $PreviousBaseline "package_boundary_policy" $PolicyIdentity.package_boundary_policy
    Assert-PolicyField $PreviousBaseline "package_boundary_policy_sha256" $PolicyIdentity.package_boundary_policy_sha256
    Assert-PolicyField $PreviousBaseline "graph_schema_contract" $PolicyIdentity.graph_schema_contract
    Assert-PolicyField $PreviousBaseline "graph_schema_contract_sha256" $PolicyIdentity.graph_schema_contract_sha256
    Assert-PolicyField $PreviousBaseline "manifest_schema_contract" $PolicyIdentity.manifest_schema_contract
    Assert-PolicyField $PreviousBaseline "manifest_schema_contract_sha256" $PolicyIdentity.manifest_schema_contract_sha256
    Assert-PolicyField $PreviousBaseline "baseline_metadata_contract" $PolicyIdentity.baseline_metadata_contract
    Assert-PolicyField $PreviousBaseline "baseline_metadata_contract_sha256" $PolicyIdentity.baseline_metadata_contract_sha256
    Assert-PolicyField $PreviousBaseline "policy_fingerprint_sha256" $PolicyIdentity.policy_fingerprint_sha256
    if ($PreviousBaseline.mode -ne "code-only") { Fail "Incremental requires unchanged code-only mode; run FullRebuild." }
}

function Assert-IncrementalIntegrity($SourceRoot, $PreviousBaseline, $PreGraph, $PreManifest, $PostGraph, $PostManifest, $CurrentCommit) {
    $previousCommit = [string]$PreviousBaseline.indexed_source_commit
    $changes = @(Get-GitNameStatus $SourceRoot $previousCommit $CurrentCommit)
    $changedCount = [Math]::Max(1, $changes.Count)
    $deleteRenameCount = @($changes | Where-Object { $_.Kind -in @("deleted", "renamed") }).Count
    if ($changes.Count -gt $MaxChangedFilesForIncremental) {
        Fail "Incremental integrity rejected changed-file count; run FullRebuild."
    }
    if ($deleteRenameCount -gt $MaxDeletedOrRenamedFilesForIncremental) {
        Fail "Incremental integrity rejected deleted/renamed-file count; run FullRebuild."
    }

    $postManifestPaths = @(Get-ManifestSourceSet $PostManifest)
    $postNodePaths = @(Get-GraphNodes $PostGraph | ForEach-Object { [string]$_.source_file } | Sort-Object -Unique)
    foreach ($change in $changes) {
        if ($change.Kind -eq "deleted") {
            if ($postManifestPaths -contains $change.OldPath -or $postNodePaths -contains $change.OldPath) {
                Fail "Ghost node/source path after deletion; run FullRebuild."
            }
        }
        if ($change.Kind -eq "renamed") {
            if ($postManifestPaths -contains $change.OldPath -or $postNodePaths -contains $change.OldPath) {
                Fail "Ghost node/source path after rename; run FullRebuild."
            }
            if ((Test-SourcePathInCorpus $change.NewPath) -and -not ($postManifestPaths -contains $change.NewPath)) {
                Fail "Renamed source path missing from post-update manifest; run FullRebuild."
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
    foreach ($id in (Get-GraphNodes $PostGraph | ForEach-Object { [string]$_.id } | Sort-Object -Unique)) { $postIds[$id] = $true }
    $lost = @($preUnchangedNodeIds | Where-Object { -not $postIds.ContainsKey($_) })
    if ($lost.Count -gt 0) {
        Fail "Incremental update lost unchanged node identities; run FullRebuild."
    }

    $preCounts = Count-Graph $PreGraph
    $postCounts = Count-Graph $PostGraph
    $nodeDelta = [int]$postCounts.Nodes - [int]$preCounts.Nodes
    $edgeDelta = [int]$postCounts.Edges - [int]$preCounts.Edges
    if ([Math]::Abs($nodeDelta) -gt ($MaxNodeDeltaPerChangedFile * $changedCount)) {
        Fail "Unexpected topology node delta; run FullRebuild."
    }
    if ([Math]::Abs($edgeDelta) -gt ($MaxEdgeDeltaPerChangedFile * $changedCount)) {
        Fail "Unexpected topology edge delta; run FullRebuild."
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

function Assert-Candidate($SourceRoot, $BuildRoot, $GraphDir, $SourceCommit, $SourceRef, $SourceRefSha, $TargetBranch, $Version, $PolicyIdentity) {
    $graphPath = Join-Path $GraphDir "graph.json"
    $manifestPath = Join-Path $GraphDir "manifest.json"
    $reportPath = Join-Path $GraphDir "GRAPH_REPORT.md"
    foreach ($required in @($graphPath, $manifestPath, $reportPath)) {
        if (-not (Test-Path -LiteralPath $required)) {
            Fail "Required Graphify output missing."
        }
    }

    Remove-UncommittedGraphifyByproducts $GraphDir
    Assert-GeneratedCandidateBoundary (Split-Path -Parent $GraphDir) $GraphDir
    foreach ($artifact in @("graph.json", "manifest.json", "GRAPH_REPORT.md")) {
        ConvertTo-CanonicalGeneratedTextArtifact $GraphDir $artifact
    }
    Sanitize-GraphReport $GraphDir $BuildRoot $SourceCommit $SourceRef $TargetBranch
    ConvertTo-CanonicalGeneratedTextArtifact $GraphDir "GRAPH_REPORT.md"

    $graph = Assert-Json $graphPath
    $manifest = Assert-Json $manifestPath
    Assert-GraphStructure $graph $manifest
    Assert-CurrentCorpusPaths $SourceRoot $manifest $graph
    $baseline = Write-Baseline $GraphDir $SourceCommit $SourceRef $TargetBranch $Version $graph $graphPath $PolicyIdentity
    $baseline = Assert-Json (Join-Path $GraphDir "baseline.json")

    Assert-GeneratedAllowlist (Split-Path -Parent $GraphDir) $GraphDir
    Assert-SecretScan $GraphDir $graph $manifest $baseline
    Assert-Metadata $SourceRoot $GraphDir $graph $baseline $SourceCommit $SourceRef $SourceRefSha $TargetBranch $Version $PolicyIdentity

    return [pscustomobject]@{
        Graph = $graph
        Manifest = $manifest
        Baseline = $baseline
        Confidence = Get-ConfidenceSummary $graph
    }
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

function Test-CandidateMatchesAccepted($OutputRoot, $CandidateGraphDir) {
    $acceptedGraphDir = Join-Path $OutputRoot $GraphDirName
    if (-not (Test-Path -LiteralPath $acceptedGraphDir -PathType Container)) {
        return $false
    }
    foreach ($file in @("graph.json", "manifest.json", "GRAPH_REPORT.md")) {
        $candidate = Join-Path $CandidateGraphDir $file
        $accepted = Join-Path $acceptedGraphDir $file
        if (-not (Test-Path -LiteralPath $accepted -PathType Leaf)) {
            return $false
        }
        $candidateHash = Get-Sha256 $candidate
        $acceptedHash = Get-Sha256 $accepted
        if ($candidateHash -ne $acceptedHash) {
            return $false
        }
    }
    $candidateBaseline = Assert-Json (Join-Path $CandidateGraphDir "baseline.json")
    $acceptedBaseline = Assert-Json (Join-Path $acceptedGraphDir "baseline.json")
    $candidateComparable = $candidateBaseline | Select-Object -Property * -ExcludeProperty generated_at
    $acceptedComparable = $acceptedBaseline | Select-Object -Property * -ExcludeProperty generated_at
    $candidateJson = $candidateComparable | ConvertTo-Json -Depth 20 -Compress
    $acceptedJson = $acceptedComparable | ConvertTo-Json -Depth 20 -Compress
    if ($candidateJson -ne $acceptedJson) {
        return $false
    }
    return $true
}

function Start-GraphPublicationTransaction($OutputRoot, $CandidateGraphDir) {
    $target = Join-Path $OutputRoot $GraphDirName
    $transactionRoot = Join-Path ([System.IO.Path]::GetTempPath()) "diag-project-graph-publication-$PID-$([Guid]::NewGuid().ToString('N'))"
    New-Item -ItemType Directory -Path $transactionRoot -Force | Out-Null
    $backup = Join-Path $transactionRoot "accepted-backup"
    $hadPrevious = Test-Path -LiteralPath $target -PathType Container

    try {
        if ($hadPrevious) {
            Copy-Item -LiteralPath $target -Destination $backup -Recurse -Force
            Remove-Item -LiteralPath $target -Recurse -Force
        }
        New-Item -ItemType Directory -Path $target -Force | Out-Null
        foreach ($file in @("graph.json", "manifest.json", "GRAPH_REPORT.md", "baseline.json")) {
            Copy-Item -LiteralPath (Join-Path $CandidateGraphDir $file) -Destination (Join-Path $target $file) -Force
        }
        return [pscustomobject]@{
            OutputRoot = $OutputRoot
            Target = $target
            TransactionRoot = $transactionRoot
            Backup = $backup
            HadPrevious = $hadPrevious
            Started = $true
        }
    } catch {
        Restore-GraphPublicationTransaction ([pscustomobject]@{
            OutputRoot = $OutputRoot
            Target = $target
            TransactionRoot = $transactionRoot
            Backup = $backup
            HadPrevious = $hadPrevious
            Started = $true
        })
        Fail "Graph publication transaction failed during artifact replacement."
    }
}

function Restore-GraphPublicationTransaction($Transaction) {
    if ($null -eq $Transaction -or -not $Transaction.Started) {
        return
    }
    if (Test-Path -LiteralPath $Transaction.Target) {
        Remove-Item -LiteralPath $Transaction.Target -Recurse -Force -ErrorAction SilentlyContinue
    }
    if ($Transaction.HadPrevious -and (Test-Path -LiteralPath $Transaction.Backup -PathType Container)) {
        Copy-Item -LiteralPath $Transaction.Backup -Destination $Transaction.Target -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath $Transaction.TransactionRoot) {
        Remove-Item -LiteralPath $Transaction.TransactionRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Complete-GraphPublicationTransaction($Transaction) {
    if ($null -eq $Transaction) {
        return
    }
    if (Test-Path -LiteralPath $Transaction.TransactionRoot) {
        Remove-Item -LiteralPath $Transaction.TransactionRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Remove-TempOutputs($OutputRoot) {
    $tempParent = Join-Path $OutputRoot $TempDirName
    if (Test-Path -LiteralPath $tempParent) {
        Remove-Item -LiteralPath $tempParent -Recurse -Force
    }
}

function Assert-PublicationDiff($OutputRoot, $SourceCommit) {
    $diffOutput = (& git -C $OutputRoot status --short --untracked-files=all 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail "Unable to inspect publication status."
    }
    $changedPaths = @($diffOutput -split "`r?`n" |
        Where-Object { $_.Trim() } |
        ForEach-Object { $_.Substring(2).Trim().Replace("\", "/") } |
        Sort-Object -Unique)
    if ($changedPaths.Count -eq 0) {
        return $false
    }
    $unexpected = @($changedPaths | Where-Object { $AllowedGenerated -notcontains $_ })
    if ($unexpected.Count -gt 0) {
        Fail ("Publication diff includes non-allowlisted paths: " + ($unexpected -join ", "))
    }
    return $true
}

function Invoke-ResultingTreeChecks($OutputRoot, $SourceRoot, $SourceCommit, $SourceRef, $SourceRefSha, $TargetBranch, $Version, $PolicyIdentity) {
    $acceptedGraphDir = Join-Path $OutputRoot $GraphDirName
    $acceptedGraph = Assert-Json (Join-Path $acceptedGraphDir "graph.json")
    $acceptedManifest = Assert-Json (Join-Path $acceptedGraphDir "manifest.json")
    $acceptedBaseline = Assert-Json (Join-Path $acceptedGraphDir "baseline.json")
    Assert-GeneratedAllowlist $OutputRoot $acceptedGraphDir
    Assert-GraphStructure $acceptedGraph $acceptedManifest
    Assert-CurrentCorpusPaths $SourceRoot $acceptedManifest $acceptedGraph
    Assert-SecretScan $acceptedGraphDir $acceptedGraph $acceptedManifest $acceptedBaseline
    Assert-Metadata $SourceRoot $acceptedGraphDir $acceptedGraph $acceptedBaseline $SourceCommit $SourceRef $SourceRefSha $TargetBranch $Version $PolicyIdentity
    Assert-NoGraphifyIntegrations $OutputRoot
    Assert-CleanGit $SourceRoot "Source"
    $hasPublicationDiff = Assert-PublicationDiff $OutputRoot $SourceCommit
    if (-not $hasPublicationDiff) {
        Fail "Published graph artifacts produced no reviewable allowlisted diff."
    }
    return [pscustomobject]@{
        Graph = $acceptedGraph
        Manifest = $acceptedManifest
        Baseline = $acceptedBaseline
    }
}

try {
$invocationRoot = Get-RepoRootFrom "."
$outputRootFull = if ($OutputRoot) { Get-RepoRootFrom $OutputRoot } else { Fail "OutputRoot is required for graph publication." }
$sourceRootFull = if ($SourceRoot) { Get-RepoRootFrom $SourceRoot } else { Fail "SourceRoot is required for graph publication." }

if (-not (Test-Path -LiteralPath (Join-Path $outputRootFull "RULES.md")) -or
    -not (Test-Path -LiteralPath (Join-Path $outputRootFull "openspec.cmd"))) {
    Fail "Output repository root verification failed."
}

if ($Mode -eq "InstallExact") {
    & uv tool install "graphifyy==$ExpectedGraphifyVersion"
    exit $LASTEXITCODE
}

Assert-TargetBranch $TargetBranch
$boundary = Assert-SameExactBase $sourceRootFull $outputRootFull $SourceRef
$sourceCommit = $boundary.SourceCommit
$sourceRefSha = $boundary.SourceRefSha
$ignorePolicy = Assert-SourceGraphifyIgnore $sourceRootFull

$version = (& graphify --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    Fail "graphify --version failed."
}
if ($version -notmatch "graphify\s+([0-9]+\.[0-9]+\.[0-9]+)") {
    Fail "Unable to parse Graphify version."
}
$version = $Matches[1]
if ($version -ne $ExpectedGraphifyVersion) {
    Fail "Graphify version mismatch."
}
$policyIdentity = Get-GraphPolicyIdentity $sourceRootFull $ignorePolicy.Sha256

Remove-TempOutputs $outputRootFull
$buildRoot = $null
$candidateGraphDir = $null
$result = $null
$incrementalEvidence = $null
$acceptedResult = $null

try {
    $buildRoot = New-BuildCopy $sourceRootFull $outputRootFull
    $candidateGraphDir = Join-Path $buildRoot $GraphDirName

    if ($Mode -eq "FullRebuild") {
        Invoke-GraphifyBuild $buildRoot
    } elseif ($Mode -eq "Incremental") {
        $acceptedGraphDir = Join-Path $outputRootFull $GraphDirName
        $acceptedBaselinePath = Join-Path $acceptedGraphDir "baseline.json"
        if (-not (Test-Path -LiteralPath $acceptedBaselinePath)) {
            Fail "Accepted baseline is required for incremental mode."
        }
        New-Item -ItemType Directory -Path $candidateGraphDir -Force | Out-Null
        Get-ChildItem -LiteralPath $acceptedGraphDir -Force | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $candidateGraphDir -Recurse -Force
        }
        $preGraph = Assert-Json (Join-Path $candidateGraphDir "graph.json")
        $preManifest = Assert-Json (Join-Path $candidateGraphDir "manifest.json")
        $previousBaseline = Assert-Json $acceptedBaselinePath
        Assert-IncrementalPreconditions $previousBaseline $policyIdentity $version
        Invoke-GraphifyIncremental $buildRoot
        $postGraph = Assert-Json (Join-Path $candidateGraphDir "graph.json")
        $postManifest = Assert-Json (Join-Path $candidateGraphDir "manifest.json")
        $incrementalEvidence = Assert-IncrementalIntegrity $sourceRootFull $previousBaseline $preGraph $preManifest $postGraph $postManifest $sourceCommit
    }

    $result = Assert-Candidate $sourceRootFull $buildRoot $candidateGraphDir $sourceCommit $SourceRef $sourceRefSha $TargetBranch $version $policyIdentity
    if (Test-CandidateMatchesAccepted $outputRootFull $candidateGraphDir) {
        Write-Host "No graph publication changes: accepted artifacts are semantically byte-current except volatile generated_at."
        exit 0
    }
    Assert-CleanGit $outputRootFull "Output"
    $transaction = Start-GraphPublicationTransaction $outputRootFull $candidateGraphDir
    try {
        $acceptedResult = Invoke-ResultingTreeChecks $outputRootFull $sourceRootFull $sourceCommit $SourceRef $sourceRefSha $TargetBranch $version $policyIdentity
        Complete-GraphPublicationTransaction $transaction
    } catch {
        $failureCategory = [string]$_.Exception.Message
        Restore-GraphPublicationTransaction $transaction
        Fail "Graph publication transaction failed after artifact replacement: $failureCategory"
    }
} finally {
    if ($buildRoot -and (Test-Path -LiteralPath $buildRoot)) {
        Remove-Item -LiteralPath $buildRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    Remove-TempOutputs $outputRootFull
}
$acceptedBaseline = $acceptedResult.Baseline

Write-Host "Graphify version: $version"
Write-Host "Baseline stage: $BaselineStage"
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

exit 0
} catch {
    [Console]::Error.WriteLine([string]$_.Exception.Message)
    exit 1
}
