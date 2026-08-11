param(
  [Parameter(Mandatory=$true)][string]$MachineLabel,
  [string]$OperatorId = "operator:local",
  [string]$Output = "host-record.json",
  [string]$ArchiveIdentity = ""
)
$ErrorActionPreference = "Stop"
$Arguments = @(
  "evaluator.py",
  "--machine-label", $MachineLabel,
  "--operator-id", $OperatorId,
  "--output", $Output
)
if ($ArchiveIdentity) {
  $Arguments += @("--archive-identity", $ArchiveIdentity)
}
if (Get-Command py -ErrorAction SilentlyContinue) {
  & py -3 @Arguments
} else {
  & python @Arguments
}
