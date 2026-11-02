import base64
import hashlib
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def get_json(url, timeout=8):
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=timeout) as response:
            if response.status != 200:
                raise ValueError(f"HTTP {response.status}")
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ValueError(f"HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(type(exc).__name__) from None


class Command(BaseCommand):
    help = "Check the configured Vasto OIDC provider and local client registration."

    def handle(self, *args, **options):
        failures = []
        discovery_url = settings.VASTO_DISCOVERY_URL
        try:
            metadata = get_json(discovery_url)
            if not isinstance(metadata, dict):
                raise ValueError("document is not a JSON object")
            self.stdout.write(self.style.SUCCESS("OK discovery document is reachable and valid JSON"))
        except ValueError as exc:
            raise CommandError(f"Discovery unavailable or invalid at {discovery_url}: {exc}")

        if metadata.get("issuer") != settings.VASTO_ISSUER:
            failures.append(f"issuer mismatch: expected {settings.VASTO_ISSUER!r}, received {metadata.get('issuer')!r}")
        for field in ("authorization_endpoint", "token_endpoint", "userinfo_endpoint", "jwks_uri"):
            if not metadata.get(field):
                failures.append(f"discovery is missing {field}")
        if failures:
            raise CommandError("Vasto discovery configuration failed: " + "; ".join(failures))
        self.stdout.write(self.style.SUCCESS("OK issuer and required OIDC endpoints"))

        try:
            jwks = get_json(metadata["jwks_uri"])
            keys = jwks.get("keys", []) if isinstance(jwks, dict) else []
            rsa_keys = [key for key in keys if key.get("kty") == "RSA" and key.get("use", "sig") == "sig"
                        and key.get("n") and key.get("e") and key.get("alg", "RS256") == "RS256"]
            if not rsa_keys:
                raise ValueError("no usable RSA RS256 signing key")
        except ValueError as exc:
            raise CommandError(f"JWKS check failed at {metadata['jwks_uri']}: {exc}")
        self.stdout.write(self.style.SUCCESS("OK JWKS contains a usable RSA RS256 signing key"))

        if not settings.VASTO_CLIENT_ID:
            failures.append("VASTO_CLIENT_ID is missing")
        if not settings.VASTO_CLIENT_SECRET:
            failures.append("VASTO_CLIENT_SECRET is missing")
        if failures:
            raise CommandError("Client configuration failed: " + "; ".join(failures))
        callback = settings.VASTO_REDIRECT_URI
        expected_callback = "http://127.0.0.1:8001/api/auth/vasto/callback/"
        if callback != expected_callback:
            self.stderr.write(self.style.WARNING(f"Configured callback is {callback}; local default is {expected_callback}. Verify it is registered exactly."))
        else:
            self.stdout.write(self.style.SUCCESS("OK configured callback matches local default"))

        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        params = {
            "client_id": settings.VASTO_CLIENT_ID,
            "redirect_uri": callback,
            "response_type": "code",
            "scope": "openid profile email",
            "state": secrets.token_urlsafe(24),
            "nonce": secrets.token_urlsafe(24),
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        url = metadata["authorization_endpoint"] + ("&" if "?" in metadata["authorization_endpoint"] else "?") + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"Accept": "text/html, application/json"})
        try:
            with urllib.request.build_opener(NoRedirect).open(request, timeout=8) as response:
                status, location, body = response.status, response.headers.get("Location", ""), response.read(4096).decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            status, location, body = exc.code, exc.headers.get("Location", ""), exc.read(4096).decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError) as exc:
            raise CommandError(f"Authorization preflight could not reach Vasto: {type(exc).__name__}") from None

        location_query = urllib.parse.parse_qs(urllib.parse.urlparse(location).query)
        body_error = ""
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict):
                body_error = str(parsed.get("error", ""))
                description = str(parsed.get("error_description", "")).lower()
            else:
                description = ""
        except json.JSONDecodeError:
            description = body.lower()
        error = (location_query.get("error") or [body_error])[0]
        detail = (location_query.get("error_description") or [description])[0].lower()
        if status in (301, 302, 303, 307, 308) and location and not error:
            self.stdout.write(self.style.SUCCESS("OK provider accepted client, callback, and authorization parameters (no redirect followed)"))
        elif error:
            if error in {"invalid_client", "invalid_client_id"}:
                reason = "Vasto rejected the Client ID; verify this local Application exists and its ID matches the credentials file"
            elif error == "invalid_redirect_uri" or "redirect" in detail:
                reason = "Vasto rejected the callback URI; match it exactly to the Application redirect URI"
            else:
                reason = f"Vasto rejected authorization parameters ({error}); {detail[:240]}"
            raise CommandError(reason)
        elif status in (400, 401, 403):
            raise CommandError(f"Vasto rejected the authorization preflight with HTTP {status}; inspect client ID and registered callback in Vasto Admin")
        else:
            raise CommandError(f"Authorization preflight returned unexpected HTTP {status}; no browser redirect was followed")

        # A deliberately bogus code tests client authentication without requesting
        # a real grant. A valid client gets invalid_grant; invalid_client indicates
        # the ID/secret pair is not recognized. No token can be issued for this code.
        token_url = metadata["token_endpoint"]
        token_payload = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": "vasto-oidc-preflight-invalid-code",
            "redirect_uri": callback,
            "code_verifier": secrets.token_urlsafe(48),
        }).encode()
        basic = base64.b64encode(f"{settings.VASTO_CLIENT_ID}:{settings.VASTO_CLIENT_SECRET}".encode()).decode()
        token_request = urllib.request.Request(
            token_url, data=token_payload, method="POST",
            headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )
        token_status, token_body = 0, ""
        try:
            with urllib.request.build_opener(NoRedirect).open(token_request, timeout=8) as response:
                token_status = response.status
                token_body = response.read(4096).decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            token_status = exc.code
            token_body = exc.read(4096).decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError) as exc:
            raise CommandError(f"Token endpoint preflight could not reach Vasto: {type(exc).__name__}") from None
        try:
            token_error = str(json.loads(token_body).get("error", ""))
        except (json.JSONDecodeError, AttributeError):
            token_error = ""
        if token_error == "invalid_client":
            raise CommandError("Vasto rejected client authentication at the token endpoint; verify the Client Secret belongs to this Client ID")
        if token_error == "invalid_grant":
            self.stdout.write(self.style.SUCCESS("OK token endpoint authenticated the client; the deliberately invalid test code was rejected without issuing a token"))
        else:
            raise CommandError(f"Token endpoint preflight returned HTTP {token_status} with an unexpected response; verify Vasto client authentication configuration")
