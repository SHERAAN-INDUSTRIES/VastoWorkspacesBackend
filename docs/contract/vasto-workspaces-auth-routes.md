# Vasto ↔ Workspaces authentication routes

This is the route reference for the Vasto sign-in integration. It covers the browser-facing Workspaces routes and the Vasto OpenID Connect (OIDC) endpoints used by that flow. It is not a list of every product API in either repository.

## How the services connect

1. The frontend sends the browser to Workspaces `GET /api/auth/vasto/start/`.
2. Workspaces creates a short-lived, browser-bound authorization transaction (state, nonce, and PKCE verifier) and redirects the browser to Vasto.
3. Vasto authenticates the user and asks for consent when required. Vasto redirects the browser to Workspaces `GET /api/auth/vasto/callback/`.
4. Workspaces exchanges the code server-to-server, validates the OIDC identity, and finds or creates a local Workspaces user. It links that user to the Vasto identity using the issuer and OIDC `sub`.
5. Workspaces creates its own Django session and sets its session cookie. It redirects the browser to `WORKSPACES_FRONTEND_URL`.
6. The frontend calls `GET /api/auth/me/`. The browser sends the cookie; Workspaces resolves the local user from the session and returns the profile JSON.

The frontend does not submit a user ID, Vasto password, OAuth code, or session key to identify the user. The Workspaces user ID in the profile is local to Workspaces. The OIDC `sub` is stored in Workspaces as the provider identity link and is not returned by the profile endpoint. The raw session key remains in the HttpOnly cookie.

For local development, Vasto is typically at `http://127.0.0.1:8000`, Workspaces at `http://127.0.0.1:8001`, and the frontend at `http://127.0.0.1:3000`. Use the configured service origins in other environments.

## Workspaces routes

### Start Vasto authorization

`GET /api/auth/vasto/start/`

Called by top-level browser navigation to the Workspaces API origin. No JSON body is sent.

- **Success:** `302 Found` redirect to Vasto's authorization endpoint. Workspaces creates/binds a session transaction and may set its session cookie.
- **Failure:** the framework/provider may return an error response if the authorization client or provider configuration is unavailable.

The browser must follow the redirect in the same window and retain cookies.

### OIDC callback

`GET /api/auth/vasto/callback/`

Vasto redirects the browser here with the authorization response query parameters. The route is intended to be called as part of the redirect flow, not directly by frontend code.

- **Success:** `302 Found` to `WORKSPACES_FRONTEND_URL` after Workspaces validates the response, creates the Workspaces session, and sets its HttpOnly cookie. If no frontend URL is configured, the route returns a small HTML signed-in page.
- **Failure:** JSON with a non-2xx status. The current generic shape is:

```json
{
  "authenticated": false,
  "error": "Vasto authorization could not be validated."
}
```

The message varies by failure. Invalid/expired transaction and missing authorization code are 400; provider-declined authorization is 403; rejected identity validation is 401; provider/discovery or unexpected callback failures are 502. Do not replay or manually refresh a callback URL; transactions are browser-bound and single-use.

### Current user

`GET /api/auth/me/`

Send `Accept: application/json` and include browser credentials. For cross-origin frontend requests, use `credentials: 'include'`; Workspaces must allow the exact frontend origin and credentials through CORS.

- **200 OK:** authenticated profile:

```json
{
  "status": "success",
  "message": "Authenticated user profile retrieved successfully.",
  "authenticated": true,
  "user": {
    "id": 42,
    "username": "sample-user",
    "first_name": "Sample",
    "last_name": "User",
    "display_name": "Sample User",
    "email": "sample@example.test",
    "email_verified": true,
    "profile_picture": "https://pwaninet.app/media/profile_pic/sample.jpg",
    "status": "active"
  },
  "session": {
    "status": "active",
    "expires_at": "2026-11-03T13:30:00+00:00",
    "expires_in_seconds": 50400
  }
}
```

`user.id` is the Workspaces database ID. `profile_picture` is `null` when no URL was provided. `session` contains expiry metadata only; it never contains the session key.

- **401 Unauthorized:** no authenticated Workspaces session or no linked Vasto identity:

```json
{
  "status": "error",
  "message": "Authentication is required.",
  "authenticated": false
}
```

The message is `No Vasto identity is linked to this session.` when a session exists without a Vasto identity.

### Logout

`POST /api/auth/logout/`

Requires an authenticated Workspaces session and a valid Django CSRF token. Send credentials and the CSRF token using the deployment's CSRF bootstrap mechanism. This endpoint does not accept a user ID or request body.

- **200 OK:** `{"authenticated":false,"logged_out":true}`
- **401 Unauthorized:** `{"authenticated":false}` if the caller is not signed in.
- **403 Forbidden:** missing or invalid CSRF token.

Logout ends the Workspaces session. It does not log the user out of Vasto.

## Vasto OIDC routes used by Workspaces

Workspaces discovers these endpoints from the OIDC metadata at the configured `VASTO_ISSUER`; do not hard-code provider paths in the frontend.

- **Discovery:** `GET {VASTO_ISSUER}/.well-known/openid-configuration` — provider metadata used by Workspaces to find authorization, token, UserInfo, and signing-key endpoints.
- **Authorization:** browser redirect to the endpoint named `authorization_endpoint` in discovery. Vasto authenticates the user, applies OAuth client/consent policy, then redirects to the registered Workspaces callback.
- **Token exchange:** Workspaces server calls the discovered `token_endpoint` with the authorization code, client authentication, redirect URI, and PKCE verifier. Tokens are server-to-server and are not returned to the frontend.
- **UserInfo:** Workspaces server calls the discovered `userinfo_endpoint` and checks that its `sub` matches the signed ID token.
- **Signing keys:** Workspaces uses the discovered `jwks_uri` to validate the ID token signature.

Vasto's current local issuer is commonly `http://127.0.0.1:8000/o`; production issuer values must match Vasto discovery and Workspaces `VASTO_ISSUER` exactly.

## Frontend route checklist

The current frontend integration calls only:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/auth/vasto/start/` | Begin sign-in; browser follows redirects. |
| GET | `/api/auth/me/` | Read the current Workspaces session and profile. |

The callback is reached by redirect and should not be called directly. Logout is available in the backend but is not currently wired into the frontend. The frontend calls Workspaces directly and requires correctly configured credentialed CORS and compatible cookie settings.
