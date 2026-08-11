#!/bin/sh
set -eu
machine_label="${1:?machine label required}"
operator_id="${2:-operator:local}"
output="${3:-host-record.json}"
archive_identity="${4:-${MNCS_ARCHIVE_IDENTITY:-}}"
set -- evaluator.py --machine-label "$machine_label" --operator-id "$operator_id" --output "$output"
if [ -n "$archive_identity" ]; then
  set -- "$@" --archive-identity "$archive_identity"
fi
python3 "$@"
