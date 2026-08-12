[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$RepoPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [Parameter(Mandatory)]
    [string]$OutputFolder,
    [ValidatePattern("^([01]\d|2[0-3]):[0-5]\d$")]
    [string]$At = "07:00",
    [string]$TaskName = "BCG Group Weekly Monitoring",
    [switch]$RunWhetherLoggedOn
)

$ErrorActionPreference = "Stop"
$RepoPath = [IO.Path]::GetFullPath($RepoPath)
$OutputFolder = [IO.Path]::GetFullPath($OutputFolder)
$Runner = Join-Path $RepoPath "scripts\run_weekly.ps1"
$PythonPath = Join-Path $RepoPath ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Runner)) {
    throw "Weekly runner is missing: $Runner"
}
if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Virtual environment is missing: $PythonPath"
}
New-Item -ItemType Directory -Force -Path $OutputFolder | Out-Null

$PowerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$ActionArguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $Runner + '" -RepoPath "' + $RepoPath + '" -OutputFolder "' + $OutputFolder + '"'
$Action = New-ScheduledTaskAction -Execute $PowerShellExe -Argument $ActionArguments -WorkingDirectory $RepoPath
$TriggerTime = [datetime]::Today.Add([TimeSpan]::ParseExact($At, "hh\:mm", [Globalization.CultureInfo]::InvariantCulture))
$Trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday -At $TriggerTime
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
$Description = "Collect official BCG and BCG Land IR disclosures and save the weekly Excel report."

if ($PSCmdlet.ShouldProcess($TaskName, "Register weekly task at Monday $At")) {
    if ($RunWhetherLoggedOn) {
        $Credential = Get-Credential -Message "Enter the Windows account that will run the weekly BCG report"
        Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description $Description -User $Credential.UserName -Password $Credential.GetNetworkCredential().Password -RunLevel Limited -Force | Out-Null
    }
    else {
        $UserId = [Security.Principal.WindowsIdentity]::GetCurrent().Name
        $Principal = New-ScheduledTaskPrincipal -UserId $UserId -LogonType Interactive -RunLevel Limited
        Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description $Description -Principal $Principal -Force | Out-Null
    }
}

Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State, Description
Get-ScheduledTaskInfo -TaskName $TaskName | Select-Object LastRunTime, LastTaskResult, NextRunTime
Write-Output "Output folder: $OutputFolder"
