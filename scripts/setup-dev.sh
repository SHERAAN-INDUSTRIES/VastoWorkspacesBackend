#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON=""
CREDENTIALS_FILE=""
INTERACTIVE=0

usage() { printf 'Usage: %s [--credentials-file PATH | --interactive]\n' "$0"; }
while (($#)); do
  case "$1" in
    --credentials-file) (($# >= 2)) || { usage >&2; exit 2; }; CREDENTIALS_FILE="$2"; shift 2 ;;
    --interactive) INTERACTIVE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

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
"$PY" -m pip install --upgrade pip >/dev/null || { printf 'Could not upgrade pip. Check network/package-index access.\n' >&2; exit 1; }
"$PY" -m pip install -r requirements.txt || { printf 'Dependency installation failed. Review the error above and repository requirements.\n' >&2; exit 1; }
"$PY" -m pip install celery redis django-redis django-celery-beat django-celery-results flower packaging || { printf 'Failed to install Celery/Redis dependencies.\n' >&2; exit 1; }
"$PY" -m pip check || { printf 'Installed dependencies have conflicts.\n' >&2; exit 1; }

# Check if Redis is running
if ! command -v redis-cli >/dev/null 2>&1; then
  printf 'Redis is not installed. Please install Redis or use a managed Redis service.\n' >&2
  printf 'For local development: sudo apt install redis-server\n' >&2
  printf 'Then start Redis: redis-server\n' >&2
  exit 1
fi

if ! redis-cli ping >/dev/null 2>&1; then
  printf 'Redis is not running. Starting Redis server...\n'
  if command -v redis-server >/dev/null 2>&1; then
    redis-server --daemonize yes >/dev/null 2>&1
    sleep 2
    if ! redis-cli ping >/dev/null 2>&1; then
      printf 'Failed to start Redis server. Please start it manually.\n' >&2
      exit 1
    fi
    printf 'Redis server started successfully.\n'
  else
    printf 'Redis server not found. Please install and start Redis.\n' >&2
    exit 1
  fi
fi

if [[ ! -e .env ]]; then
  [[ -f .env.example ]] || { printf 'Missing .env.example.\n' >&2; exit 1; }
  cp .env.example .env
  chmod 600 .env
  printf 'Created .env from .env.example.\n'
else printf 'Retained existing .env.\n'; fi
if ! grep -Eq '^WORKSPACES_SECRET_KEY=.{20,}$' .env; then
  secret="$("$PY" -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')" || { printf 'Could not generate Django secret key.\n' >&2; exit 1; }
  if grep -q '^WORKSPACES_SECRET_KEY=' .env; then sed -i.bak "s|^WORKSPACES_SECRET_KEY=.*|WORKSPACES_SECRET_KEY=$secret|" .env && rm -f .env.bak
  else printf '\nWORKSPACES_SECRET_KEY=%s\n' "$secret" >> .env; fi
  chmod 600 .env
  unset secret
  printf 'Generated a local Django secret key in .env (value not displayed).\n'
fi

# Set VASTO_API_BASE_URL if not present
if ! grep -q '^VASTO_API_BASE_URL=' .env; then
  echo "VASTO_API_BASE_URL=http://127.0.0.1:8000" >> .env
  echo "Set VASTO_API_BASE_URL to localhost."
fi

# Check for VASTO_SERVICE_TOKEN
if ! grep -q '^VASTO_SERVICE_TOKEN=.' .env; then
  printf 'VASTO_SERVICE_TOKEN not found in .env\n' >&2
  printf 'Please run Pwaninet setup-dev.sh first to generate the service token.\n' >&2
  printf 'Then copy the VASTO_SERVICE_TOKEN value from Pwaninet .env to Workspaces .env\n' >&2
  exit 1
fi

# Check if OAuth credentials are already configured
if grep -q '^VASTO_CLIENT_ID=.' .env && grep -q '^VASTO_CLIENT_SECRET=.' .env; then
  printf 'OAuth credentials already configured in .env, skipping credential import.\n'
else
  if [[ -n "$CREDENTIALS_FILE" ]]; then
    "$PY" scripts/import-oidc-credentials.py "$CREDENTIALS_FILE" || exit $?
  elif ((INTERACTIVE)); then
    "$PY" scripts/import-oidc-credentials.py --interactive || exit $?
  else
    shopt -s nullglob
    local_credentials=("$HOME"/.config/vasto-workspaces/*-local.env)
    shopt -u nullglob
    if ((${#local_credentials[@]} == 1)); then
      "$PY" scripts/import-oidc-credentials.py "${local_credentials[0]}" || exit $?
    elif [[ -t 0 ]]; then
      if ((${#local_credentials[@]} > 1)); then
        printf 'Found multiple local Vasto credential files.\n'
        read -r -p 'Enter the file path to use (blank to enter credentials): ' CREDENTIALS_FILE
      fi
      if [[ -n "$CREDENTIALS_FILE" ]]; then
        "$PY" scripts/import-oidc-credentials.py "$CREDENTIALS_FILE" || exit $?
      else
        "$PY" scripts/import-oidc-credentials.py --interactive || exit $?
      fi
    else
      printf 'No Vasto credentials file was selected. Pass --credentials-file PATH or run this script in a terminal for hidden interactive setup.\n' >&2
      exit 1
    fi
  fi
fi
cd "$ROOT/workspace"
"$PY" manage.py check || { printf 'Django settings/system check failed. Review .env and the message above.\n' >&2; exit 1; }
"$PY" manage.py shell -c 'from django.db import connection; connection.ensure_connection()' >/dev/null 2>&1 || { printf 'Workspaces database is not accessible. Check WORKSPACES_DATABASE_URL or local SQLite permissions; no migrations were run.\n' >&2; exit 1; }
"$PY" manage.py migrate || { printf 'Database migration failed.\n' >&2; exit 1; }
"$PY" manage.py check_vasto_oidc || { printf 'Vasto OIDC preflight failed. Start Vasto at 127.0.0.1:8000, verify its registration and credentials, then rerun this setup script.\n' >&2; exit 1; }

printf 'Workspaces setup and Vasto OIDC preflight are complete.\n'
printf 'Start Workspaces with: %q %q runserver 127.0.0.1:8001\n' "$PY" "$ROOT/workspace/manage.py"
printf '\nTo start Celery worker (in another terminal):\n'
printf '  cd %q && %q celery -A workspace worker --loglevel=info --concurrency=2\n' "$ROOT/workspace" "$PY"
printf '\nTo start Celery Beat scheduler (in another terminal):\n'
printf '  cd %q && %q celery -A workspace beat --loglevel=info\n' "$ROOT/workspace" "$PY"
printf '\nTo monitor Celery with Flower (in another terminal):\n'
printf '  cd %q && %q flower -A workspace --port=5555\n' "$ROOT/workspace" "$PY"
