#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${VIRTUAL_ENV:-$ROOT/.venv}/bin/python"
[[ -x "$PY" ]] || { echo 'Run bash scripts/setup-dev.sh first, or activate your Python environment.' >&2; exit 1; }
# Uses configured Redis URLs and reuses responsive workers and managed Beat.
exec "$PY" "$ROOT/scripts/dev-services.py" start --root "$ROOT/workspace" --app workspace --settings workspace.settings
