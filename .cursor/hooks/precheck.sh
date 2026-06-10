#!/bin/bash
# Lightweight before-prompt check. Re-runs portability and (when present) a
# scoped ruff check on changed files. Fails open: never blocks the user.

set -uo pipefail

cat > /dev/null

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
WARNINGS=()

if ! (cd "$ROOT" && python3 scripts/check_portability.py >/dev/null 2>&1); then
  WARNINGS+=("portability invariants currently violated — see scripts/check_portability.py")
fi

# Only run ruff if uv is available (cheap, ~200ms in cache).
if command -v uv >/dev/null 2>&1; then
  if ! (cd "$ROOT/apps/api" && uv run --quiet ruff check . >/dev/null 2>&1); then
    WARNINGS+=("ruff check is failing on apps/api — run 'uv run ruff check . --fix'")
  fi
fi

if [[ ${#WARNINGS[@]} -eq 0 ]]; then
  echo '{}'
  exit 0
fi

joined=$(printf -- "- %s\n" "${WARNINGS[@]}")
escaped=$(printf '%s' "$joined" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')

cat <<JSON
{
  "additional_context": ${escaped}
}
JSON

exit 0
