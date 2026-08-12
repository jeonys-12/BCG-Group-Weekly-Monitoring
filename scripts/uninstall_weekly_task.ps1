[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$TaskName = "BCG Group Weekly Monitoring"
)

$ErrorActionPreference = "Stop"
$Existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $Existing) {
    Write-Output "Scheduled task not found: $TaskName"
    exit 0
}
if ($PSCmdlet.ShouldProcess($TaskName, "Unregister scheduled task")) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}
Write-Output "Removed scheduled task: $TaskName"
