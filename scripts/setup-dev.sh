#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON=""
CREDENTIALS_FILE=""
INTERACTIVE=0

if [[ -t 1 ]]; then
  C_BLUE=$'\033[1;34m'; C_GREEN=$'\033[1;32m'; C_YELLOW=$'\033[1;33m'; C_RESET=$'\033[0m'
else
  C_BLUE=''; C_GREEN=''; C_YELLOW=''; C_RESET=''
fi
section() { printf '\n%b── %s ──%b\n' "$C_BLUE" "$1" "$C_RESET"; }
success() { printf '%b✓%b %s\n' "$C_GREEN" "$C_RESET" "$1"; }

usage() { printf 'Usage: %s [--credentials-file PATH | --interactive]\n' "$0"; }
while (($#)); do
  case "$1" in
    --credentials-file) (($# >= 2)) || { usage >&2; exit 2; }; CREDENTIALS_FILE="$2"; shift 2 ;;
    --interactive) INTERACTIVE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

printf '\n%bVasto Workspaces · Local setup%b\n' "$C_BLUE" "$C_RESET"
printf 'This setup checks your tools, updates missing .env fields, and prepares the database.\n'

FAILURES=()
run_step() {
  local label="$1"; shift
  if "$@"; then success "$label"; return 0; fi
  FAILURES+=("$label")
  printf 'Needs attention: %s; continuing independent steps.\n' "$label" >&2
  return 1
}
setup_summary() {
  local status=$?
  printf '\nWorkspaces setup summary (exit %s)\n' "$status"
  if ((${#FAILURES[@]})); then printf '  Needs attention: %s\n' "${FAILURES[@]}"; fi
  echo "  Saved configuration: $ROOT/.env (retained across retries)."
  echo "  Celery logs/PID files: $ROOT/workspace/.dev-services/"
  if (( status )); then echo '  Setup is incomplete. Fix reported errors and rerun; completed steps and credentials are retained.'; fi
}
trap setup_summary EXIT
section 'Checking your computer'
case "$(uname -s)" in Linux*|Darwin*) ;; *) printf 'Unsupported OS. Use Linux or macOS, or follow the manual setup in README.md.\n' >&2; exit 1;; esac
command -v git >/dev/null || { printf 'Git is required. Install Git and rerun.\n' >&2; exit 1; }
VENV_DIR=""
python_is_supported() { "$1" -c 'import sys; raise SystemExit(not ((3, 12) <= sys.version_info[:2] < (3, 15)))' >/dev/null 2>&1; }
if [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  VENV_DIR="$VIRTUAL_ENV"
elif [[ -n "${CONDA_PREFIX:-}" && -x "$CONDA_PREFIX/bin/python" ]]; then
  VENV_DIR="$CONDA_PREFIX"
else
  FOUND_VENVS=()
  SUPPORTED_VENVS=()
  for dir in "$ROOT/.venv" "$ROOT/venv" "$ROOT/env"; do
    if [[ -x "$dir/bin/python" ]]; then
      FOUND_VENVS+=("$dir")
      if python_is_supported "$dir/bin/python"; then SUPPORTED_VENVS+=("$dir"); fi
    fi
  done
  if ((${#SUPPORTED_VENVS[@]})); then
    VENV_DIR="${SUPPORTED_VENVS[0]}"
  else
    shopt -s nullglob
    for cfg in "$ROOT"/*/pyvenv.cfg "$ROOT"/.[!.]*/pyvenv.cfg; do
      dir="${cfg%/pyvenv.cfg}"
      case "$dir" in "$ROOT/.venv"|"$ROOT/venv"|"$ROOT/env") continue;; esac
      [[ -x "$dir/bin/python" ]] || continue
      FOUND_VENVS+=("$dir")
      if python_is_supported "$dir/bin/python"; then SUPPORTED_VENVS+=("$dir"); fi
    done
    shopt -u nullglob
    if ((${#SUPPORTED_VENVS[@]} == 1)); then
      VENV_DIR="${SUPPORTED_VENVS[0]}"
    elif ((${#SUPPORTED_VENVS[@]} > 1)); then
      printf 'Found multiple existing Python environments. Activate the one to use, then rerun setup.\n' >&2
      exit 1
    fi
  fi
  if [[ -z "$VENV_DIR" && ${#FOUND_VENVS[@]} -gt 0 ]]; then
    printf 'Found an existing Python environment, but none uses Python 3.12–3.14. Activate or install a compatible environment; setup will not create another.\n' >&2
    exit 1
  fi
fi
if [[ -n "$VENV_DIR" ]]; then
  PY="$VENV_DIR/bin/python"
  python_is_supported "$PY" || { printf 'The active Python environment must use Python 3.12–3.14. Activate a compatible environment and rerun.\n' >&2; exit 1; }
  printf 'Using existing Python environment: %s\n' "$VENV_DIR"
else
  for candidate in python3.14 python3.13 python3.12 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && python_is_supported "$(command -v "$candidate")"; then PYTHON="$candidate"; break; fi
  done
  [[ -n "$PYTHON" ]] || { printf 'Python 3.12–3.14 is required by the pinned Django 6.1 dependency. Install a supported Python version and rerun.\n' >&2; exit 1; }
  if ! "$PYTHON" -m venv .venv; then printf 'Could not create .venv; ensure the Python venv module is installed.\n' >&2; exit 1; fi
  VENV_DIR="$ROOT/.venv"
  PY="$VENV_DIR/bin/python"
  printf 'Created Python environment: %s\n' "$VENV_DIR"
fi
if [[ ! -e .env ]]; then
  [[ -f .env.example ]] || { printf 'Missing .env.example.\n' >&2; exit 1; }
  cp .env.example .env
  chmod 600 .env
  printf 'Created .env from .env.example.\n'
else printf 'Retained existing .env.\n'; fi
"$PY" scripts/sync-env-example.py .env.example .env
chmod 600 .env
if ! grep -Eq '^WORKSPACES_SECRET_KEY=.{20,}$' .env; then
  secret="$("$PY" -c 'import secrets; print(secrets.token_hex(32))')" || { printf 'Could not generate Django secret key.\n' >&2; exit 1; }
  if grep -q '^WORKSPACES_SECRET_KEY=' .env; then sed -i.bak "s|^WORKSPACES_SECRET_KEY=.*|WORKSPACES_SECRET_KEY=$secret|" .env && rm -f .env.bak
  else printf '\nWORKSPACES_SECRET_KEY=%s\n' "$secret" >> .env; fi
  chmod 600 .env
  unset secret
  printf 'Generated a local Django secret key in .env (value not displayed).\n'
fi

export PY ROOT CREDENTIALS_FILE INTERACTIVE
section 'Installing backend dependencies'
run_step "pip upgrade" "$PY" -m pip install --upgrade pip || true
"$PY" -m pip install -r requirements.txt || { printf 'Dependency installation failed. Review the error above and repository requirements.\n' >&2; exit 1; }
run_step "Dependency consistency" "$PY" -m pip check || true


section 'Connecting to Pwaninet'
if ! grep -Eq '^VASTO_SERVICE_TOKEN=.+$' .env; then
  run_step 'Pwaninet service token' "$PY" scripts/configure-service-token.py .env || true
else
  success 'Pwaninet service token is already configured.'
fi
run_step 'OAuth credential import' bash scripts/setup-oidc.sh || true
cd "$ROOT/workspace"
MIGRATED=0
if run_step 'Django settings check' "$PY" manage.py check; then
  if run_step 'Database connectivity' "$PY" manage.py shell -c 'from django.db import connection; connection.ensure_connection()'; then
    if run_step 'Database migrations' "$PY" manage.py migrate --noinput; then MIGRATED=1; fi
  fi
fi
# Provider availability does not block local Redis/worker setup.
run_step 'Pwaninet OAuth preflight' "$PY" manage.py check_vasto_oidc || true
if (( MIGRATED )); then
  run_step 'Redis and Celery startup' "$PY" "$ROOT/scripts/dev-services.py" start --root "$ROOT/workspace" --app workspace --settings workspace.settings || true
else
  run_step 'Redis connectivity' "$PY" "$ROOT/scripts/dev-services.py" check --root "$ROOT/workspace" --app workspace --settings workspace.settings || true
  FAILURES+=('Celery startup skipped until database migrations succeed')
fi
printf '\nStart Workspaces: %q -m uvicorn workspace.asgi:application --app-dir %q --host 127.0.0.1 --port 8001 --reload\n' "$PY" "$ROOT/workspace"
if ((${#FAILURES[@]})); then exit 1; fi
success 'Workspaces setup completed.'
