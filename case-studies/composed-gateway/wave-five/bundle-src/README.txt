MNCS Wave Five portable evaluator

Requirements: Python 3.9 or later. No third-party packages and no network access are required.

Before extraction, verify the ZIP against the supplied .sha256 sidecar.

Windows PowerShell:
  .\run.ps1 -MachineLabel windows-a -OperatorId operator:alexander

Linux / Pi OS:
  ./run.sh fedora-a operator:alexander

Return the generated host-record.json without editing it.
This records operator-controlled reproduction. It does not claim protected holdout or independent evaluation.
