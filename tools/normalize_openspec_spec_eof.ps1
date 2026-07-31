param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryRoot
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$specRoot = Join-Path $root "openspec\specs"
if (-not (Test-Path -LiteralPath $specRoot -PathType Container)) {
    exit 0
}

Get-ChildItem -LiteralPath $specRoot -Recurse -File -Filter "spec.md" | ForEach-Object {
    $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
    if ($bytes.Length -eq 0) {
        [System.IO.File]::WriteAllBytes($_.FullName, [byte[]](10))
        return
    }

    $end = $bytes.Length
    while ($end -gt 1 -and $bytes[$end - 1] -eq 10 -and $bytes[$end - 2] -eq 10) {
        $end--
    }

    if ($bytes[$end - 1] -ne 10) {
        $normalized = New-Object byte[] ($end + 1)
        [Array]::Copy($bytes, 0, $normalized, 0, $end)
        $normalized[$normalized.Length - 1] = 10
    } elseif ($end -ne $bytes.Length) {
        $normalized = New-Object byte[] $end
        [Array]::Copy($bytes, 0, $normalized, 0, $end)
    } else {
        return
    }

    [System.IO.File]::WriteAllBytes($_.FullName, $normalized)
}
