# Vasto Workspaces Backend

Identity foundation for the Vasto Workspaces Django application. Vasto is the only identity provider; this service does not provide password registration or password login.

## Local setup: Vasto sign-in, step by step

You do not need to know Django to prepare this backend. The setup script reuses an activated or existing compatible Python environment and creates `.venv` only if it cannot find one. It installs packages into that environment, imports the Vasto client credentials, prepares the database, applies database changes, and checks the connection to Vasto.

### Before you begin

- Use Linux (Ubuntu or Fedora) or macOS. Windows 10/11 users should use Ubuntu on WSL 2.
- Install Git and use Python 3.12, 3.13, or 3.14 for Workspaces. Vasto by itself supports Python 3.11 or newer.
- Install and start Docker with Compose v2 before setting up Vasto; Vasto uses it for PostgreSQL and Redis. Workspaces uses its own local SQLite database by default and does not need Docker.
- Make sure you have both the Vasto and Workspaces repositories on your computer.

### Prepare your computer by operating system

Choose your operating system below. Vasto and Workspaces setup commands must run in Bash. Linux users use their Linux terminal; macOS users use Terminal; Windows users use Ubuntu in WSL 2, not PowerShell or Command Prompt.

#### Ubuntu

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip openssl
```

For both repositories, use Python 3.12–3.14. If your Ubuntu release has an older Python, install a supported version before continuing. Install Docker Engine and Compose using [Docker's Ubuntu guide](https://docs.docker.com/engine/install/ubuntu/) and configure non-root Docker access using [Docker's post-install guide](https://docs.docker.com/engine/install/linux-postinstall/).

#### Fedora

```bash
sudo dnf install -y git python3 python3-pip openssl
```

For both repositories, use Python 3.12–3.14. If needed, install a supported version using Fedora's package tools. Install Docker Engine and Compose using [Docker's Fedora guide](https://docs.docker.com/engine/install/fedora/), start its service, and configure non-root Docker access using [Docker's post-install guide](https://docs.docker.com/engine/install/linux-postinstall/).

#### macOS

Install [Homebrew](https://brew.sh/) if it is not already installed, then use Terminal:

```bash
brew install git python@3.12 openssl
```

Install and open [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/). Wait until Docker reports that it is running.

#### Windows 10/11

Native Windows setup is not currently supported or verified. There is no PowerShell bootstrap, and the checked-in scripts require Bash plus Linux-style virtual-environment paths and file-permission handling. Docker Desktop alone does not make those scripts runnable from PowerShell. Use Ubuntu through WSL 2 for the complete Vasto + Workspaces setup:

1. In PowerShell opened as Administrator, run:

   ```powershell
   wsl --install -d Ubuntu
   ```

   Restart Windows if asked, then launch Ubuntu from the Start menu and create a Linux username and password. Follow [Microsoft's WSL instructions](https://learn.microsoft.com/en-us/windows/wsl/install) if setup requests an update.
2. Install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/). Enable the WSL 2 engine and Ubuntu integration in Docker Desktop settings. Follow [Docker's WSL guide](https://docs.docker.com/desktop/features/wsl/).
3. In the Ubuntu terminal, install the Linux tools:

   ```bash
   sudo apt update
   sudo apt install -y git python3 python3-venv python3-pip openssl
   ```
4. Keep both repositories under the Linux home directory, for example `~/projects`. Run all commands in this guide from Ubuntu in WSL, not from PowerShell. Check Python is 3.12–3.14 and Docker Desktop is running before continuing.

### 1. Set up and start Vasto

Open a terminal in the top-level folder of the Vasto repository (the folder containing its README and `scripts/`). Run:

```sh
./scripts/setup-dev.sh
```

Follow its prompts to choose a developer identifier and a Vasto staff account to own the local Workspaces client. If it offers to create a superuser, that creates a Vasto admin account and asks you to set its password. The script prepares the Vasto environment, key, database, and client registration. It saves the private client credentials file under `~/.config/vasto-workspaces/`.

When setup finishes, start Vasto. The example below uses the default `.venv`; if setup reused another environment, use the exact server command printed at the end:

```sh
.venv/bin/python manage.py runserver 127.0.0.1:8000 --settings=pwaninet.settings.local
```

Leave this terminal open. Workspaces checks the live Vasto server during its own setup, so Vasto must be running first.

### 2. Set up Workspaces

Open a second terminal and go to the top-level folder of this Workspaces repository. Use the same developer identifier from the Vasto setup in the credentials path below:

```sh
./scripts/setup-dev.sh --credentials-file ~/.config/vasto-workspaces/YOUR_IDENTIFIER-local.env
```

For example, if you chose `alex`, use `~/.config/vasto-workspaces/alex-local.env`. The Workspaces setup script reuses an activated or existing compatible Python environment (creating `.venv` only if none is found), installs dependencies, imports the client ID and secret without displaying the secret, configures its local environment, checks and migrates its own database, and verifies Vasto's discovery information and client registration.

If you are the only developer with a generated credentials file on this computer, you can instead run `./scripts/setup-dev.sh`. It finds the file automatically. If there are multiple files, it asks which one to use. You can also run `./scripts/setup-dev.sh --interactive` to enter a file path or securely enter the credentials.

Wait for the script to report that setup and the Vasto preflight are complete. If it reports that Vasto cannot be reached, confirm the Vasto server is still running in the first terminal, then rerun this script.

### 3. Start Workspaces and test login

In the Workspaces terminal, start the backend. This example uses `.venv`; if setup reused another environment, use the exact server command it printed:

```sh
.venv/bin/python workspace/manage.py runserver 127.0.0.1:8001
```

Leave both server terminals open. In your browser, visit:

```text
http://127.0.0.1:8001/api/auth/vasto/start/
```

Sign in with a Vasto account. If this is the first time that account is using Workspaces, Vasto may ask you to approve the sign-in request. After approval, the browser should return to Workspaces and show a development confirmation page, or the configured frontend if `WORKSPACES_FRONTEND_URL` is set.

Use `127.0.0.1` consistently for both sites. Do not switch between `localhost` and `127.0.0.1` during a sign-in attempt; browsers treat them as different hosts. The two applications have separate databases and sessions. Never configure Workspaces to use Vasto's database, and never put the client secret in React or other browser code.

If the repository contains several nonstandard Python environments and none is active, setup stops and tells you to activate the one you want before rerunning.

### If setup needs to be repeated

Rerun the relevant repository's `./scripts/setup-dev.sh`. It reuses the environment and applies any pending migrations. Vasto retains its existing signing key and registered client; it does not rotate secrets automatically. Workspaces can safely re-import the same credentials file. If an OAuth preflight fails, follow the error message, make sure Vasto is running, and rerun Workspaces setup.

For contributors, run automated tests or expired-transaction cleanup as separate maintenance tasks when needed. They are not part of first-time setup.

## Endpoints

### Authentication
- `GET /api/auth/vasto/start/` — starts authorization with state, nonce, and PKCE S256.
- `GET /api/auth/vasto/callback/` — consumes the browser bound transaction, exchanges the code using `client_secret_basic`, validates OIDC claims and creates/retrieves the local mapping.
- `GET /api/auth/me/` — returns the authenticated Workspaces user profile, Vasto profile-picture URL, account status, and non-secret session expiry metadata; otherwise responds 401. The session key stays in the HttpOnly cookie.
- `POST /api/auth/logout/` — CSRF protected logout of the local Django session only.

### Cached Data API (requires authentication)
- `GET /api/auth/user/profile/` — Get cached user profile from Pwaninet
- `GET /api/auth/user/documents/` — Get cached user documents
- `GET /api/auth/user/institution/` — Get cached user institution
- `GET /api/auth/user/courses/` — Get cached user courses
- `GET /api/auth/user/groups/` — Get cached user groups
- `GET /api/auth/user/notifications/` — Get cached user notifications
- `GET /api/auth/user/conversations/` — Get cached user conversations
- `POST /api/auth/user/sync/` — Manually trigger data sync for current user

All data endpoints support `?refresh=true` query parameter to force a fresh sync from Pwaninet.

## Data Synchronization Architecture

Workspaces acts as a caching layer between the frontend and Pwaninet. The frontend only communicates with Workspaces; Workspaces fetches data from Pwaninet's internal API and caches it locally.

### Flow
```
Frontend → Workspaces API → Cache Check → 
  - Cache hit: Return cached data
  - Cache miss: Fetch from Pwaninet → Update Cache → Return data
```

### Cache Strategy
- **Redis**: Hot cache for frequently accessed data (2 min - 24 hours TTL)
- **Database**: Persistent cache for offline access
- **Background Sync**: Celery tasks sync data daily/hourly/incrementally

### Scheduled Sync Tasks
- Daily full sync: 2 AM
- Hourly incremental sync: Every hour
- Notifications sync: Every 2 minutes (active users)
- Conversations sync: Every 5 minutes (active users)
- Groups sync: Every 6 hours
- Cache cleanup: 3:30 AM daily

### Environment Variables

```bash
# Pwaninet Internal API
VASTO_API_BASE_URL=http://127.0.0.1:8000
VASTO_SERVICE_TOKEN=<token-from-pwaninet>

# Redis Configuration (defaults shown)
# CELERY_BROKER_URL=redis://127.0.0.1:6379/3
# CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/4
# REDIS_CACHE_URL=redis://127.0.0.1:6379/2
```

### Running Celery

```bash
# Start Celery worker
cd workspace && ../.venv/bin/celery -A workspace worker --loglevel=info --concurrency=2

# Start Celery Beat scheduler
cd workspace && ../.venv/bin/celery -A workspace beat --loglevel=info

# Monitor with Flower
cd workspace && ../.venv/bin/flower -A workspace --port=5555
```

## Authentication documentation

- [Authentication route reference](docs/api/vasto-workspaces-auth-routes.md) — route methods, request behavior, response examples, status codes, and how Vasto and Workspaces connect.
- [Vasto OIDC client and authentication API](docs/authentication/vasto-oidc-client.md) — Workspaces OIDC flow, environment setup, identity mapping, sessions, API contract, and troubleshooting.

React frontend setup and integration documentation are maintained separately by the frontend team.
