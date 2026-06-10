#!/bin/bash
# After a file edit, run scripts/check_portability.py and surface any violations
# to the agent as an additional_context payload. Fails open so an agent edit isn't
# blocked outright — CI is the hard gate, this is the early warning.

set -uo pipefail

# Cursor sends the event JSON on stdin. We don't need it; we always run the
# repo-wide check, which is fast.
cat > /dev/null

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUTPUT=$(cd "$ROOT" && python3 scripts/check_portability.py 2>&1)
STATUS=$?

if [[ $STATUS -eq 0 ]]; then
  echo '{}'
  exit 0
fi

# Escape the captured text for safe embedding into JSON.
escaped=$(printf '%s' "$OUTPUT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')

cat <<JSON
{
  "additional_context": ${escaped},
  "agent_message": "Portability invariants are violated by the latest edit. Review the diff and fix before continuing."
}
JSON

exit 0
