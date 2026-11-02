# Vasto Workspaces Backend

Identity foundation for the Vasto Workspaces Django application. Vasto is the only identity provider; this service does not provide password registration or password login.

## Local setup

The existing project is in `workspace/` and uses the existing Django user model and SQLite database by default.

1. Copy `.env.example` to `.env` in this repository root.
2. Set `WORKSPACES_SECRET_KEY`, `VASTO_CLIENT_ID`, and `VASTO_CLIENT_SECRET` using values registered with the local Vasto provider. Keep the local issuer and redirect URI pointed at `127.0.0.1`.
3. Install dependencies: `../.venv/bin/pip install -r requirements.txt` when running from `workspace/` (or `.venv/bin/pip install -r requirements.txt` from the repository root).
4. Run migrations and start Workspaces on port 8001:

   ```sh
   cd workspace
   ../.venv/bin/python manage.py migrate
   ../.venv/bin/python manage.py runserver 127.0.0.1:8001
   ```

5. Open `http://127.0.0.1:8001/api/auth/vasto/start/` in a browser. A successful callback shows a temporary development confirmation page, or redirects to `WORKSPACES_FRONTEND_URL` when configured.

Before relying on a live login, confirm the provider discovery document at `VASTO_DISCOVERY_URL` reports exactly the configured `VASTO_ISSUER`, and register the configured redirect URI with Vasto. Tokens and client secrets stay server side. Workspaces retains only the local identity mapping and creates its own Django session.

Run the test suite with `../.venv/bin/python manage.py test identity.tests` from `workspace/`. Delete expired OAuth transactions with `../.venv/bin/python manage.py cleanup_auth_transactions`; schedule that command periodically in deployed environments.

## Endpoints

- `GET /api/auth/vasto/start/` — starts authorization with state, nonce, and PKCE S256.
- `GET /api/auth/vasto/callback/` — consumes the browser bound transaction, exchanges the code using `client_secret_basic`, validates OIDC claims and creates/retrieves the local mapping.
- `GET /api/auth/me/` — returns an authenticated local identity's approved username and email fields; otherwise responds 401.
- `POST /api/auth/logout/` — CSRF protected logout of the local Django session only.

## Authentication documentation

- [Vasto OIDC client and authentication API](docs/authentication/vasto-oidc-client.md) — Workspaces OIDC flow, environment setup, identity mapping, sessions, API contract, and troubleshooting.

React frontend setup and integration documentation are maintained separately by the frontend team.
