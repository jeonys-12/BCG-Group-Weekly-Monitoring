[CmdletBinding()]
param(
    [string]$RepoPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$OutputFolder = "",
    [string]$PythonPath = "",
    [string]$RunDate = "",
    [ValidateRange(1, 100)]
    [int]$MaxPages = 10
)

$ErrorActionPreference = "Stop"
$RepoPath = [IO.Path]::GetFullPath($RepoPath)
if (-not $OutputFolder) {
    $OutputFolder = Join-Path $RepoPath "reports\output"
}
$OutputFolder = [IO.Path]::GetFullPath($OutputFolder)
if (-not $PythonPath) {
    $PythonPath = Join-Path $RepoPath ".venv\Scripts\python.exe"
}
$PythonPath = [IO.Path]::GetFullPath($PythonPath)
$Runner = Join-Path $RepoPath "src\weekly_report.py"
$Template = Join-Path $RepoPath "reports\template\BCG_Group_Trend_Master.xlsx"

foreach ($RequiredPath in @($RepoPath, $PythonPath, $Runner, $Template)) {
    if (-not (Test-Path -LiteralPath $RequiredPath)) {
        throw "Required path does not exist: $RequiredPath"
    }
}

$LogFolder = Join-Path $RepoPath "logs"
$MetadataFolder = Join-Path $RepoPath "data\history"
New-Item -ItemType Directory -Force -Path $OutputFolder, $LogFolder, $MetadataFolder | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LogPath = Join-Path $LogFolder "weekly-$Timestamp.log"
$PythonArguments = @(
    "-m", "src.weekly_report",
    "--sources", "config\sources.yaml",
    "--rules", "config\report_rules.yaml",
    "--template", "reports\template\BCG_Group_Trend_Master.xlsx",
    "--output-dir", $OutputFolder,
    "--metadata-dir", $MetadataFolder,
    "--max-pages", [string]$MaxPages
)
if ($RunDate) {
    $ParsedRunDate = [datetime]::ParseExact($RunDate, "yyyy-MM-dd", [Globalization.CultureInfo]::InvariantCulture)
    $PythonArguments += @("--run-date", $ParsedRunDate.ToString("yyyy-MM-dd"))
}

Push-Location $RepoPath
try {
    "[$(Get-Date -Format o)] Starting BCG weekly report" | Tee-Object -FilePath $LogPath
    "Repository: $RepoPath" | Tee-Object -FilePath $LogPath -Append
    "Output: $OutputFolder" | Tee-Object -FilePath $LogPath -Append
    & $PythonPath @PythonArguments 2>&1 | Tee-Object -FilePath $LogPath -Append
    $ExitCode = $LASTEXITCODE
    "[$(Get-Date -Format o)] Finished with exit code $ExitCode" | Tee-Object -FilePath $LogPath -Append
}
finally {
    Pop-Location
}
exit $ExitCode
