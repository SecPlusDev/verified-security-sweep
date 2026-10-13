#!/usr/bin/env bash
# Leakage check. Kept under this name for CI and documentation; the logic is in
# .github/scripts/leakage_check.py (standard library only). Same exit codes.
# The private term list is .github/leakage-terms.local when it exists (ignored by git); CI
# sets LEAKAGE_TERMS_FILE itself from the repository secret.
here="$(cd "$(dirname "$0")" && pwd)"
if [ -z "${LEAKAGE_TERMS_FILE:-}" ] && [ -f "$here/../leakage-terms.local" ]; then
  export LEAKAGE_TERMS_FILE="$here/../leakage-terms.local"
fi
exec python3 "$here/leakage_check.py" "$@"
