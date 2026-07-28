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
$HistoricalChangeName = "frozen-project-graph-baseline"
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
    [Console]::Error.WriteLine($Message)
    exit 1
}

function Fail-Contract($Category, $Message) {
    Fail "[$Category] $Message"
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

function Invoke-GitQuiet($Root, $Arguments) {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = (& git -C $Root @Arguments 2>$null | Out-String).Trim()
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    return [pscustomobject]@{
        ExitCode = $code
        Output = $output
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

function Get-GitSha($Root, $Ref) {
    $result = Invoke-GitQuiet $Root @("rev-parse", "--verify", "$Ref^{commit}")
    $sha = $result.Output
    if ($result.ExitCode -ne 0 -or $sha -notmatch "^[0-9a-f]{40}$") {
        Fail "Unable to resolve Git ref '$Ref'."
    }
    return $sha
}

function Assert-CleanGit($Root, $Purpose) {
    $status = (& git -C $Root status --short 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail-Contract "SOURCE_STATE" "git status failed for $Purpose."
    }
    if ($status) {
        Fail-Contract "SOURCE_STATE" "$Purpose worktree is not clean. Refusing to publish graph metadata for uncommitted bytes."
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
    $result = Invoke-GitQuiet $Root @("merge-base", "--is-ancestor", $Ancestor, $Descendant)
    return ($result.ExitCode -eq 0)
}

function Invoke-GitChecked($Root, $Arguments, $FailureMessage) {
    $output = (& git -C $Root @Arguments 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail "$FailureMessage`: $output"
    }
    return $output
}

function Assert-RelativeRepoPath($Path, $Purpose, $Category) {
    if (-not $Path) {
        Fail-Contract $Category "$Purpose path is required."
    }
    if ([System.IO.Path]::IsPathRooted($Path)) {
        Fail-Contract $Category "$Purpose path must be repository-relative."
    }
    $normalized = $Path.Replace("\", "/")
    if ($normalized -ne $Path -or $normalized -match "(^|/)\.\.(/|$)" -or $normalized -match "^/" -or $normalized -match "//") {
        Fail-Contract $Category "$Purpose path must be a normalized repository-relative path."
    }
    return $normalized
}

function Assert-SemanticChangeName($ChangeName) {
    if ([string]$ChangeName -cnotmatch "^[a-z0-9]+(?:-[a-z0-9]+)*$") {
        Fail-Contract "EVIDENCE_SCHEMA" "Graphify evidence change_name must be a semantic OpenSpec change name."
    }
}

function Get-DeterministicOrdinaryEvidencePath($ChangeName) {
    Assert-SemanticChangeName $ChangeName
    if ($ChangeName -eq $HistoricalChangeName) {
        Fail-Contract "HISTORICAL_COMPATIBILITY" "Ordinary Graphify evidence cannot use the historical frozen-baseline identity."
    }
    return "openspec/validation/$ChangeName.post-archive.json"
}

function Assert-ExactPropertySet($Object, [string[]]$Expected, $Category, $Subject) {
    if ($null -eq $Object -or -not ($Object -is [System.Management.Automation.PSCustomObject])) {
        Fail-Contract $Category "$Subject must be a JSON object."
    }
    $actual = @($Object.PSObject.Properties.Name)
    $expectedSorted = @($Expected | Sort-Object)
    $actualSorted = @($actual | Sort-Object)
    if (($actualSorted -join "`n") -ne ($expectedSorted -join "`n")) {
        Fail-Contract $Category "$Subject must contain exactly the approved fields."
    }
}

function Assert-JsonInteger($Value, $Expected, $Category, $Subject) {
    if ($Value -isnot [int] -and $Value -isnot [long]) {
        Fail-Contract $Category "$Subject must be an integer."
    }
    if ([int64]$Value -ne [int64]$Expected) {
        Fail-Contract $Category "$Subject has an invalid value."
    }
}

function Assert-NonNegativeJsonInteger($Value, $Category, $Subject) {
    if ($Value -isnot [int] -and $Value -isnot [long]) {
        Fail-Contract $Category "$Subject must be a non-negative integer."
    }
    if ([int64]$Value -lt 0) {
        Fail-Contract $Category "$Subject must be a non-negative integer."
    }
}

function Assert-StringValue($Value, $Category, $Subject) {
    if ($Value -isnot [string] -or -not $Value) {
        Fail-Contract $Category "$Subject must be a non-empty string."
    }
    return [string]$Value
}

function Assert-FullCommitSha($Root, $Value, $Category, $Subject) {
    $sha = Assert-StringValue $Value $Category $Subject
    if ($sha -cnotmatch "^[0-9a-f]{40}$") {
        Fail-Contract $Category "$Subject must be a full lowercase commit SHA."
    }
    $result = Invoke-GitQuiet $Root @("rev-parse", "--verify", "$sha^{commit}")
    if ($result.ExitCode -ne 0 -or $result.Output -cnotmatch "^[0-9a-f]{40}$") {
        Fail-Contract $Category "$Subject must resolve to a repository commit."
    }
    return $result.Output
}

function Assert-TrackedHeadEvidence($SourceRoot, $EvidenceFull, $ExpectedRelativePath = $ApprovedPostArchiveValidationEvidence) {
    $relativeEvidencePath = RelPath $EvidenceFull $SourceRoot
    if ($relativeEvidencePath -ne $ExpectedRelativePath) {
        Fail-Contract "EVIDENCE_PATH" "Post-archive validation evidence path does not match the deterministic change path."
    }

    & git -C $SourceRoot check-ignore --no-index --quiet -- $relativeEvidencePath
    if ($LASTEXITCODE -eq 0) {
        Fail-Contract "EVIDENCE_PATH" "Post-archive validation evidence must not be ignored."
    }
    if ($LASTEXITCODE -ne 1) {
        Fail-Contract "EVIDENCE_PATH" "Unable to verify post-archive validation evidence ignore status."
    }

    $tracked = Invoke-GitQuiet $SourceRoot @("ls-files", "--error-unmatch", "--", $relativeEvidencePath)
    if ($tracked.ExitCode -ne 0) {
        Fail-Contract "EVIDENCE_PATH" "Post-archive validation evidence must be tracked in Git."
    }
    $headPath = Invoke-GitQuiet $SourceRoot @("cat-file", "-e", "HEAD:$relativeEvidencePath")
    if ($headPath.ExitCode -ne 0) {
        Fail-Contract "EVIDENCE_BYTES" "Post-archive validation evidence must exist in SourceRoot HEAD."
    }

    $headBlob = Invoke-GitChecked $SourceRoot @("rev-parse", "HEAD:$relativeEvidencePath") "[EVIDENCE_BYTES] Unable to read HEAD blob for post-archive validation evidence"
    $workingBlob = Invoke-GitChecked $SourceRoot @("hash-object", "--path=$relativeEvidencePath", "--", $EvidenceFull) "[EVIDENCE_BYTES] Unable to hash working-tree post-archive validation evidence"
    if ($headBlob -ne $workingBlob) {
        Fail-Contract "EVIDENCE_BYTES" "Post-archive validation evidence working-tree bytes must match the committed HEAD blob after repository filters."
    }

    return $relativeEvidencePath
}

function Assert-PathAbsentAtCommit($SourceRoot, $Commit, $Path, $Category, $Message) {
    $result = Invoke-GitQuiet $SourceRoot @("ls-tree", "-r", "--name-only", $Commit, "--", $Path)
    if ($result.ExitCode -ne 0) {
        Fail-Contract $Category "Unable to verify committed path absence."
    }
    if ($result.Output) {
        Fail-Contract $Category $Message
    }
}

function Assert-PathPresentAtCommit($SourceRoot, $Commit, $Path, $Category, $Message) {
    $result = Invoke-GitQuiet $SourceRoot @("ls-tree", "-r", "--name-only", $Commit, "--", $Path)
    if ($result.ExitCode -ne 0 -or -not $result.Output) {
        Fail-Contract $Category $Message
    }
}

function Assert-WorkingTreeBlobMatchesCommit($SourceRoot, $Commit, $Path, $Category, $Subject) {
    $pathFull = Get-PathUnderRoot $SourceRoot $Path $Subject
    if (-not (Test-Path -LiteralPath $pathFull -PathType Leaf)) {
        Fail-Contract $Category "$Subject file is missing from the working tree."
    }
    $commitBlob = Invoke-GitChecked $SourceRoot @("rev-parse", "$Commit`:$Path") "[$Category] Unable to read committed blob for $Subject"
    $workingBlob = Invoke-GitChecked $SourceRoot @("hash-object", "--path=$Path", "--", $pathFull) "[$Category] Unable to hash working-tree bytes for $Subject"
    if ($commitBlob -ne $workingBlob) {
        Fail-Contract $Category "$Subject working-tree bytes must match the declared committed blob after repository filters."
    }
}

function Assert-TrackedReportPath($SourceRoot, $ReportPath) {
    & git -C $SourceRoot check-ignore --no-index --quiet -- $ReportPath
    if ($LASTEXITCODE -eq 0) {
        Fail-Contract "REPORT_PATH" "Verification report must not be ignored."
    }
    if ($LASTEXITCODE -ne 1) {
        Fail-Contract "REPORT_PATH" "Unable to verify verification report ignore status."
    }
    $tracked = Invoke-GitQuiet $SourceRoot @("ls-files", "--error-unmatch", "--", $ReportPath)
    if ($tracked.ExitCode -ne 0) {
        Fail-Contract "REPORT_PATH" "Verification report must be tracked in Git."
    }
}

function Get-ChangedPathSet($SourceRoot, $FromCommit, $ToCommit, $Category, $Purpose) {
    $diffOutput = (& git -C $SourceRoot diff --name-only $FromCommit $ToCommit -- 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail-Contract $Category "Unable to verify $Purpose path delta."
    }
    return @($diffOutput -split "`r?`n" |
        Where-Object { $_.Trim() } |
        ForEach-Object { $_.Trim().Replace("\", "/") } |
        Sort-Object -Unique)
}

function Assert-ExactCommitDelta($SourceRoot, $FromCommit, $ToCommit, $ExpectedPath, $Category, $Purpose) {
    $changedPaths = @(Get-ChangedPathSet $SourceRoot $FromCommit $ToCommit $Category $Purpose)
    if ($changedPaths.Count -ne 1 -or $changedPaths[0] -ne $ExpectedPath) {
        Fail-Contract $Category "$Purpose path delta must contain exactly the declared repository path."
    }
}

function Assert-EvidenceOnlyCommitDelta($SourceRoot, $ValidatedSourceCommit, $SourceCommit) {
    $previousEvidencePath = (& git -C $SourceRoot ls-tree -r --name-only $ValidatedSourceCommit -- $ApprovedPostArchiveValidationEvidence 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail "Unable to verify post-archive validation evidence absence from validated_source_commit: $previousEvidencePath"
    }
    if ($previousEvidencePath) {
        Fail "Post-archive validation evidence must be created by the evidence commit and absent from validated_source_commit."
    }

    Assert-ExactCommitDelta $SourceRoot $ValidatedSourceCommit $SourceCommit $ApprovedPostArchiveValidationEvidence "LINEAGE" "historical evidence-only"
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

function Assert-StatusObjectPass($Object, [string[]]$ExpectedFields, $Category, $Subject) {
    Assert-ExactPropertySet $Object $ExpectedFields $Category $Subject
    if ([string]$Object.status -cne "pass") {
        Fail-Contract $Category "$Subject status must be pass."
    }
}

function Assert-OrdinaryEvidenceSchema($SourceRoot, $Evidence) {
    $topFields = @(
        "schema_version",
        "change_name",
        "archive_path",
        "archive_commit",
        "validated_source_commit",
        "verification_report_path",
        "verification_report_commit",
        "openspec_all_validation",
        "python_tests",
        "git_diff_check",
        "repository_protection",
        "verdict"
    )
    Assert-ExactPropertySet $Evidence $topFields "EVIDENCE_SCHEMA" "Ordinary Graphify evidence"
    Assert-JsonInteger $Evidence.schema_version 1 "EVIDENCE_SCHEMA" "schema_version"

    $changeName = Assert-StringValue $Evidence.change_name "EVIDENCE_SCHEMA" "change_name"
    Assert-SemanticChangeName $changeName
    if ($changeName -eq $HistoricalChangeName) {
        Fail-Contract "HISTORICAL_COMPATIBILITY" "Ordinary evidence cannot impersonate the historical frozen-baseline workflow."
    }

    $archivePath = Assert-RelativeRepoPath (Assert-StringValue $Evidence.archive_path "EVIDENCE_SCHEMA" "archive_path") "archive_path" "EVIDENCE_PATH"
    if ($archivePath -cnotmatch "^openspec/changes/archive/[^/]+$") {
        Fail-Contract "ARCHIVE_STATE" "archive_path must identify one archived OpenSpec change directory."
    }
    $archiveLeaf = ($archivePath -split "/")[-1]
    if ($archiveLeaf -ne $changeName -and $archiveLeaf -notlike "*-$changeName") {
        Fail-Contract "EVIDENCE_PATH" "archive_path must match change_name."
    }

    $reportPath = Assert-RelativeRepoPath (Assert-StringValue $Evidence.verification_report_path "EVIDENCE_SCHEMA" "verification_report_path") "verification_report_path" "REPORT_PATH"
    if ($reportPath -ne "$archivePath/verification-report.md") {
        Fail-Contract "REPORT_PATH" "verification_report_path must be the declared archive verification-report.md."
    }

    $archiveCommit = Assert-FullCommitSha $SourceRoot $Evidence.archive_commit "COMMIT_IDENTITY" "archive_commit"
    $validatedSourceCommit = Assert-FullCommitSha $SourceRoot $Evidence.validated_source_commit "COMMIT_IDENTITY" "validated_source_commit"
    $verificationReportCommit = Assert-FullCommitSha $SourceRoot $Evidence.verification_report_commit "COMMIT_IDENTITY" "verification_report_commit"

    Assert-StatusObjectPass $Evidence.openspec_all_validation @("status") "REQUIRED_CHECK" "openspec_all_validation"
    Assert-StatusObjectPass $Evidence.git_diff_check @("status") "REQUIRED_CHECK" "git_diff_check"
    Assert-StatusObjectPass $Evidence.repository_protection @("status") "REQUIRED_CHECK" "repository_protection"
    Assert-ExactPropertySet $Evidence.python_tests @("status", "tests", "failures", "errors", "skips") "EVIDENCE_SCHEMA" "python_tests"
    if ([string]$Evidence.python_tests.status -cne "pass") {
        Fail-Contract "REQUIRED_CHECK" "python_tests status must be pass."
    }
    foreach ($field in @("tests", "failures", "errors", "skips")) {
        Assert-NonNegativeJsonInteger $Evidence.python_tests.$field "EVIDENCE_SCHEMA" "python_tests.$field"
    }

    $verdict = Assert-StringValue $Evidence.verdict "EVIDENCE_SCHEMA" "verdict"
    if (@("APPROVE", "APPROVE WITH NON-BLOCKING NOTES") -cnotcontains $verdict) {
        Fail-Contract "VERDICT" "Graphify evidence verdict is not allowed."
    }

    return [pscustomobject]@{
        ChangeName = $changeName
        ExpectedEvidencePath = Get-DeterministicOrdinaryEvidencePath $changeName
        ArchivePath = $archivePath
        ArchiveCommit = $archiveCommit
        ValidatedSourceCommit = $validatedSourceCommit
        VerificationReportPath = $reportPath
        VerificationReportCommit = $verificationReportCommit
        Verdict = $verdict
    }
}

function Get-CommittedText($SourceRoot, $Commit, $Path, $Category, $Subject) {
    $text = (& git -C $SourceRoot show "$Commit`:$Path" 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) {
        Fail-Contract $Category "$Subject committed bytes are unavailable."
    }
    return $text
}

function Get-ReportEvidenceLines($Lines, $BeginIndex, $EndIndex) {
    $evidenceLines = @()
    $inFence = $false
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($i -ge $BeginIndex -and $i -le $EndIndex) {
            continue
        }
        $line = $Lines[$i]
        if ($line -match '^```') {
            $inFence = -not $inFence
            continue
        }
        if ($inFence -or $line -match '^\s*>') {
            continue
        }
        $evidenceLines += $line
    }
    return @($evidenceLines)
}

function Assert-SingleReportHeading($Lines, $Heading) {
    $count = @($Lines | Where-Object { $_ -ceq $Heading }).Count
    if ($count -ne 1) {
        Fail-Contract "REPORT_COMPLETENESS" "Validation report must contain each required evidence heading exactly once."
    }
}

function Get-SingleReportField($Lines, $Label) {
    $escaped = [regex]::Escape($Label)
    $matches = @($Lines | Where-Object { $_ -cmatch "^$escaped`: (?<value>.+)$" })
    if ($matches.Count -ne 1) {
        Fail-Contract "REPORT_COMPLETENESS" "Validation report must contain each required evidence field exactly once."
    }
    [void]($matches[0] -cmatch "^$escaped`: (?<value>.+)$")
    $value = $Matches["value"].Trim()
    if (-not $value) {
        Fail-Contract "REPORT_COMPLETENESS" "Validation report evidence fields must not be empty."
    }
    return $value.Trim("`"")
}

function Assert-ReportFieldEquals($Actual, $Expected, $Subject) {
    if ($Actual -cne $Expected) {
        Fail-Contract "REPORT_CONSISTENCY" "Validation report $Subject does not match the approved authority."
    }
}

function Convert-MetadataBooleanToReportValue($Value) {
    if ($Value -cne "true" -and $Value -cne "false") {
        Fail-Contract "REPORT_METADATA" "Validation metadata booleans must be lowercase literals."
    }
    if ($Value -cne "true") { return "no" }
    return "yes"
}

function Assert-ValidationReportCompleteness($ReportLines, $BeginIndex, $EndIndex, $Metadata, $ValidatedSourceCommit, $ExpectedVerdict, $ChangeName) {
    $evidenceLines = @(Get-ReportEvidenceLines $ReportLines $BeginIndex $EndIndex)

    foreach ($heading in @(
        "# Independent Validation Report",
        "## Validation Identity",
        "## Worktree Evidence",
        "## Environment",
        "## Commands",
        "## Repository Protection",
        "## Findings",
        "## Verdict"
    )) {
        Assert-SingleReportHeading $evidenceLines $heading
    }

    $requiredLabels = @(
        "Repository",
        "Branch",
        "PR",
        "Change",
        "Validated implementation/source SHA",
        "Validated remote SHA",
        "Commit subject",
        "Local/remote SHA equality",
        "Clean validation worktree before",
        "Clean validation worktree after",
        "Python version",
        "Node version",
        "npm version",
        "Graphify version",
        "Dependency restoration command",
        "Dependency restoration result",
        "Focused-test command",
        "Focused-test exit code",
        "Focused-test counts",
        "Full-suite command",
        "Full-suite exit code",
        "Full-suite counts",
        "Change strict-validation command",
        "Change strict-validation result",
        "All strict-validation command",
        "All strict-validation counts",
        "git diff --check result",
        "Repository-protection checks",
        "Findings",
        "Final verdict",
        "Archive permitted",
        "Merge permitted",
        "Production-code-changed-by-validator",
        "Tests-changed-by-validator"
    )

    $facts = @{}
    foreach ($label in $requiredLabels) {
        $facts[$label] = Get-SingleReportField $evidenceLines $label
    }

    Assert-ReportFieldEquals $facts["Branch"] $Metadata["validated_remote_branch"] "branch"
    Assert-ReportFieldEquals $facts["Change"] $ChangeName "change name"
    Assert-ReportFieldEquals $facts["Validated implementation/source SHA"] $ValidatedSourceCommit "source SHA"
    Assert-ReportFieldEquals $facts["Validated remote SHA"] $ValidatedSourceCommit "remote SHA"
    Assert-ReportFieldEquals $facts["Final verdict"] $ExpectedVerdict "verdict"
    Assert-ReportFieldEquals $facts["Archive permitted"] (Convert-MetadataBooleanToReportValue $Metadata["archive_permitted"]) "archive permission"
    Assert-ReportFieldEquals $facts["Merge permitted"] (Convert-MetadataBooleanToReportValue $Metadata["merge_permitted"]) "merge permission"
    Assert-ReportFieldEquals $facts["Production-code-changed-by-validator"] $Metadata["production_code_changed_by_validator"] "production-code validator flag"
    Assert-ReportFieldEquals $facts["Tests-changed-by-validator"] $Metadata["tests_changed_by_validator"] "tests validator flag"

    foreach ($yesNoLabel in @("Local/remote SHA equality", "Clean validation worktree before", "Clean validation worktree after")) {
        if (@("yes", "no") -cnotcontains $facts[$yesNoLabel]) {
            Fail-Contract "REPORT_COMPLETENESS" "Validation report yes/no evidence fields must use lowercase yes or no."
        }
    }
    foreach ($exitLabel in @("Focused-test exit code", "Full-suite exit code")) {
        if ($facts[$exitLabel] -cnotmatch "^[0-9]+$") {
            Fail-Contract "REPORT_COMPLETENESS" "Validation report exit-code evidence fields must be numeric."
        }
    }
}

function Assert-ValidationReportMetadata($SourceRoot, $ReportText, $ValidatedSourceCommit, $ExpectedVerdict) {
    $normalized = $ReportText.Replace("`r`n", "`n").Replace("`r", "`n")
    $lines = @($normalized -split "`n")
    if ($lines.Count -gt 0 -and $lines[-1] -eq "") {
        $lines = @($lines[0..($lines.Count - 2)])
    }

    $begin = @()
    $end = @()
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -eq "BEGIN VALIDATION METADATA") { $begin += $i }
        if ($lines[$i] -eq "END VALIDATION METADATA") { $end += $i }
    }
    if ($begin.Count -ne 1 -or $end.Count -ne 1 -or $begin[0] -ge $end[0]) {
        Fail-Contract "REPORT_METADATA" "Validation report must contain exactly one ordered metadata block."
    }

    $fenceCountBefore = @($lines[0..$begin[0]] | Where-Object { $_ -match '^```' }).Count
    if (($fenceCountBefore % 2) -ne 0) {
        Fail-Contract "REPORT_METADATA" "Validation metadata block must not be quoted or fenced."
    }

    $inside = @($lines[($begin[0] + 1)..($end[0] - 1)])
    $expectedKeys = @(
        "schema_version",
        "validated_remote_branch",
        "validated_source_commit",
        "verdict",
        "archive_permitted",
        "merge_permitted",
        "production_code_changed_by_validator",
        "tests_changed_by_validator"
    )
    if ($inside.Count -ne $expectedKeys.Count) {
        Fail-Contract "REPORT_METADATA" "Validation metadata block must contain exactly eight key/value lines."
    }

    $metadata = @{}
    for ($i = 0; $i -lt $expectedKeys.Count; $i++) {
        $line = $inside[$i]
        $colonCount = @($line.ToCharArray() | Where-Object { $_ -eq ':' }).Count
        if ($line -cnotmatch '^[a-z_]+: [^\r\n]+$' -or $colonCount -ne 1) {
            Fail-Contract "REPORT_METADATA" "Validation metadata line grammar is invalid."
        }
        $parts = $line -split ": ", 2
        if ($parts[0] -ne $expectedKeys[$i]) {
            Fail-Contract "REPORT_METADATA" "Validation metadata keys must match the approved order."
        }
        if ($metadata.ContainsKey($parts[0])) {
            Fail-Contract "REPORT_METADATA" "Validation metadata contains a duplicate key."
        }
        $metadata[$parts[0]] = $parts[1]
    }

    if ($metadata["schema_version"] -cne "1") {
        Fail-Contract "REPORT_METADATA" "Validation metadata schema_version must be 1."
    }
    $branch = $metadata["validated_remote_branch"]
    if (-not $branch -or $branch -match "[\x00-\x1f\x7f]") {
        Fail-Contract "REPORT_METADATA" "Validation metadata branch is invalid."
    }
    $branchCheck = Invoke-GitQuiet $SourceRoot @("check-ref-format", "--branch", $branch)
    if ($branchCheck.ExitCode -ne 0) {
        Fail-Contract "REPORT_METADATA" "Validation metadata branch is not a valid Git branch name."
    }
    if ($metadata["validated_source_commit"] -cnotmatch "^[0-9a-f]{40}$" -or $metadata["validated_source_commit"] -cne $ValidatedSourceCommit) {
        Fail-Contract "REPORT_METADATA" "Validation metadata source commit must exactly match the validated source commit."
    }
    if (@("APPROVE", "APPROVE WITH NON-BLOCKING NOTES") -cnotcontains $metadata["verdict"] -or $metadata["verdict"] -cne $ExpectedVerdict) {
        Fail-Contract "VERDICT" "Validation metadata verdict must be allowed and match Graphify evidence."
    }
    foreach ($key in @("archive_permitted", "merge_permitted", "production_code_changed_by_validator", "tests_changed_by_validator")) {
        if (@("true", "false") -cnotcontains $metadata[$key]) {
            Fail-Contract "REPORT_METADATA" "Validation metadata booleans must be lowercase literals."
        }
    }
    if ($metadata["archive_permitted"] -cne "true") {
        Fail-Contract "REPORT_METADATA" "Final Graphify refresh requires archive_permitted true."
    }
    if ($metadata["production_code_changed_by_validator"] -cne "false" -or $metadata["tests_changed_by_validator"] -cne "false") {
        Fail-Contract "REPORT_METADATA" "Validator code/test mutation flags must be false."
    }

    $outsideLines = @()
    if ($begin[0] -gt 0) {
        $outsideLines += $lines[0..($begin[0] - 1)]
    }
    if (($end[0] + 1) -lt $lines.Count) {
        $outsideLines += $lines[($end[0] + 1)..($lines.Count - 1)]
    }
    $withoutBlock = $outsideLines -join "`n"
    $contradictions = @(
        "CHANGES REQUIRED",
        "archive_permitted: false",
        "archive permitted: false",
        "archive permitted: no",
        "production_code_changed_by_validator: true",
        "production code changed by validator: true",
        "tests_changed_by_validator: true",
        "tests changed by validator: true"
    )
    foreach ($needle in $contradictions) {
        if ($withoutBlock -match [regex]::Escape($needle)) {
            Fail-Contract "REPORT_METADATA" "Validation report contains an authoritative statement contradicting metadata."
        }
    }

    return [pscustomobject]@{
        Branch = $branch
        Verdict = $metadata["verdict"]
        Values = $metadata
        Lines = $lines
        BeginIndex = $begin[0]
        EndIndex = $end[0]
    }
}

function Assert-OrdinaryFinalWorkflowGate($SourceRoot, $SourceCommit, $EvidencePath, $Evidence, $EvidenceFull) {
    $facts = Assert-OrdinaryEvidenceSchema $SourceRoot $Evidence
    $relativeEvidencePath = Assert-TrackedHeadEvidence $SourceRoot $EvidenceFull $facts.ExpectedEvidencePath
    if ($EvidencePath.Replace("\", "/") -ne $relativeEvidencePath) {
        Fail-Contract "EVIDENCE_PATH" "PostArchiveValidationEvidence argument must use the deterministic ordinary evidence path."
    }

    if ($facts.VerificationReportCommit -eq $SourceCommit -or $facts.ValidatedSourceCommit -eq $facts.VerificationReportCommit) {
        Fail-Contract "LINEAGE" "Ordinary final lineage must use distinct V, R, and E commits."
    }
    if (-not (Test-GitAncestor $SourceRoot $facts.ArchiveCommit $facts.ValidatedSourceCommit)) {
        Fail-Contract "LINEAGE" "archive_commit must be an ancestor of or equal to validated_source_commit."
    }
    if (-not (Test-GitAncestor $SourceRoot $facts.ValidatedSourceCommit $facts.VerificationReportCommit)) {
        Fail-Contract "LINEAGE" "validated_source_commit must be an ancestor of verification_report_commit."
    }
    if (-not (Test-GitAncestor $SourceRoot $facts.VerificationReportCommit $SourceCommit)) {
        Fail-Contract "LINEAGE" "verification_report_commit must be an ancestor of evidence commit."
    }

    Assert-PathPresentAtCommit $SourceRoot $facts.ValidatedSourceCommit $facts.ArchivePath "ARCHIVE_STATE" "validated_source_commit must contain the declared archive path."
    Assert-PathAbsentAtCommit $SourceRoot $facts.ValidatedSourceCommit "openspec/changes/$($facts.ChangeName)" "ARCHIVE_STATE" "validated_source_commit must not contain the active OpenSpec change path."
    Assert-PathPresentAtCommit $SourceRoot $facts.VerificationReportCommit $facts.VerificationReportPath "REPORT_BYTES" "verification_report_commit must contain the declared verification report."
    Assert-TrackedReportPath $SourceRoot $facts.VerificationReportPath
    Assert-WorkingTreeBlobMatchesCommit $SourceRoot $facts.VerificationReportCommit $facts.VerificationReportPath "REPORT_BYTES" "verification report"
    Assert-ExactCommitDelta $SourceRoot $facts.ValidatedSourceCommit $facts.VerificationReportCommit $facts.VerificationReportPath "LINEAGE" "V..R validation-report"

    Assert-PathAbsentAtCommit $SourceRoot $facts.VerificationReportCommit $relativeEvidencePath "LINEAGE" "Graphify evidence JSON must be absent at verification_report_commit."
    Assert-PathPresentAtCommit $SourceRoot $SourceCommit $relativeEvidencePath "EVIDENCE_BYTES" "Graphify evidence JSON must exist at evidence commit."
    Assert-ExactCommitDelta $SourceRoot $facts.VerificationReportCommit $SourceCommit $relativeEvidencePath "LINEAGE" "R..E Graphify-evidence"

    $reportText = Get-CommittedText $SourceRoot $facts.VerificationReportCommit $facts.VerificationReportPath "REPORT_BYTES" "verification report"
    $metadata = Assert-ValidationReportMetadata $SourceRoot $reportText $facts.ValidatedSourceCommit $facts.Verdict
    Assert-ValidationReportCompleteness $metadata.Lines $metadata.BeginIndex $metadata.EndIndex $metadata.Values $facts.ValidatedSourceCommit $facts.Verdict $facts.ChangeName
}

function Assert-HistoricalFinalWorkflowGate($SourceRoot, $SourceCommit, $EvidencePath, $EvidenceFull, $Evidence) {
    if ($EvidencePath.Replace("\", "/") -ne $ApprovedPostArchiveValidationEvidence) {
        Fail-Contract "HISTORICAL_COMPATIBILITY" "Historical frozen-baseline evidence must use its published path."
    }
    [void](Assert-TrackedHeadEvidence $SourceRoot $EvidenceFull $ApprovedPostArchiveValidationEvidence)

    if ($Evidence.change_name -ne $HistoricalChangeName) {
        Fail "Post-archive validation evidence change_name must be frozen-project-graph-baseline."
    }
    if ([string]$Evidence.archive_commit -cnotmatch "^[0-9a-f]{40}$") {
        Fail "Post-archive validation evidence archive_commit must be a full commit SHA."
    }
    $archiveCommit = Get-GitSha $SourceRoot ([string]$Evidence.archive_commit)
    if ([string]$Evidence.validated_source_commit -cnotmatch "^[0-9a-f]{40}$") {
        Fail "Post-archive validation evidence validated_source_commit must be a full commit SHA."
    }
    $validatedSourceCommit = Get-GitSha $SourceRoot ([string]$Evidence.validated_source_commit)
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
        Where-Object { $_.Name -eq $HistoricalChangeName -or $_.Name -like "*-$HistoricalChangeName" })
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
        Assert-EvidenceCheckPassed $Evidence $check
    }
}

function Assert-FinalWorkflowGate($SourceRoot, $SourceCommit, $EvidencePath) {
    if (-not $EvidencePath) {
        Fail-Contract "EVIDENCE_PATH" "Final baseline requires -PostArchiveValidationEvidence pointing to project-owned post-archive validation JSON."
    }

    $normalizedEvidencePath = Assert-RelativeRepoPath $EvidencePath "PostArchiveValidationEvidence" "EVIDENCE_PATH"
    if ($normalizedEvidencePath -cnotmatch "^openspec/validation/[a-z0-9]+(?:-[a-z0-9]+)*\.post-archive\.json$") {
        Fail-Contract "EVIDENCE_PATH" "PostArchiveValidationEvidence must use the deterministic validation JSON path."
    }
    $evidenceFull = Get-PathUnderRoot $SourceRoot $normalizedEvidencePath "PostArchiveValidationEvidence"
    if (-not (Test-Path -LiteralPath $evidenceFull -PathType Leaf)) {
        Fail-Contract "EVIDENCE_PATH" "Post-archive validation evidence file is missing."
    }
    $evidence = Assert-Json $evidenceFull "EVIDENCE_SCHEMA" "post-archive Graphify evidence"
    $changeName = if ($null -ne $evidence -and $evidence.PSObject.Properties.Name -contains "change_name") { [string]$evidence.change_name } else { "" }
    if ($changeName -eq $HistoricalChangeName) {
        $ordinaryOnlyFields = @("schema_version", "verification_report_path", "verification_report_commit", "repository_protection", "verdict")
        foreach ($field in $ordinaryOnlyFields) {
            if ($evidence.PSObject.Properties.Name -contains $field) {
                Fail-Contract "HISTORICAL_COMPATIBILITY" "Historical frozen-baseline identity cannot be used with ordinary Graphify evidence schema."
            }
        }
        Assert-HistoricalFinalWorkflowGate $SourceRoot $SourceCommit $normalizedEvidencePath $evidenceFull $evidence
    } else {
        Assert-OrdinaryFinalWorkflowGate $SourceRoot $SourceCommit $normalizedEvidencePath $evidence $evidenceFull
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

function Assert-Json($Path, $Category = "GRAPH_INTEGRITY", $Subject = "JSON artifact") {
    try {
        $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
        return $raw | ConvertFrom-Json
    } catch {
        Fail-Contract $Category "Invalid JSON for $Subject."
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
    Fail-Contract "SOURCE_BINDING" "Source HEAD must equal SourceRef."
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
