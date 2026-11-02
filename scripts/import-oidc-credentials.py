#!/usr/bin/env python3
"""Import a Vasto provisioned env file into the private Workspaces .env."""
import os
from pathlib import Path
import re
import sys
import tempfile
from getpass import getpass

KEYS = {
    "VASTO_DISCOVERY_URL", "VASTO_ISSUER", "VASTO_CLIENT_ID",
    "VASTO_CLIENT_SECRET", "VASTO_REDIRECT_URI",
}

def parse(path):
    values = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)", line)
        if match and match.group(1) in KEYS:
            values[match.group(1)] = match.group(2).strip().strip("\"'")
    return values

def main():
    if len(sys.argv) != 2:
        print("Usage: setup-dev.sh --credentials-file PATH | --interactive", file=sys.stderr)
        return 2
    interactive = sys.argv[1] == "--interactive"
    source = Path(sys.argv[1]).expanduser() if not interactive else None
    target = Path(__file__).resolve().parents[1] / ".env"
    if source is not None and not source.is_file():
        print(f"Credentials file not found: {source}", file=sys.stderr)
        return 1
    if interactive:
        values = {
            "VASTO_DISCOVERY_URL": input("Discovery URL [http://127.0.0.1:8000/o/.well-known/openid-configuration]: ").strip() or "http://127.0.0.1:8000/o/.well-known/openid-configuration",
            "VASTO_ISSUER": input("Expected issuer [http://127.0.0.1:8000/o]: ").strip() or "http://127.0.0.1:8000/o",
            "VASTO_CLIENT_ID": input("Client ID: ").strip(),
            "VASTO_CLIENT_SECRET": getpass("Client Secret (hidden): "),
            "VASTO_REDIRECT_URI": input("Callback URI [http://127.0.0.1:8001/api/auth/vasto/callback/]: ").strip() or "http://127.0.0.1:8001/api/auth/vasto/callback/",
        }
        if input(f"Confirm callback URI {values['VASTO_REDIRECT_URI']}? [y/N]: ").lower() != "y":
            print("Callback confirmation declined; no changes made.", file=sys.stderr)
            return 1
    else:
        values = parse(source)
    required = KEYS - {"VASTO_ISSUER"}
    if required - values.keys() or any(not values.get(k) for k in required):
        print("Credentials file must include discovery URL, client ID, client secret, and redirect URI.", file=sys.stderr)
        return 1
    if "VASTO_ISSUER" not in values:
        values["VASTO_ISSUER"] = "http://127.0.0.1:8000/o"
    original = target.read_text() if target.exists() else ""
    lines = original.splitlines()
    existing = {}
    for line in lines:
        m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if m:
            existing[m.group(1)] = m.group(2)
    for key, value in values.items():
        current = existing.get(key, "").strip().strip("\"'")
        if current and current != value:
            print(f"{key} is already set to a different value in .env; refusing to replace it.", file=sys.stderr)
            return 1
    for key, value in values.items():
        if key in existing:
            lines = [re.sub(r"^(\s*" + re.escape(key) + r"=).*$", lambda m: m.group(1) + value, line) if re.match(r"^\s*" + re.escape(key) + r"=", line) else line for line in lines]
        else:
            lines.append(f"{key}={value}")
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tempname = tempfile.mkstemp(prefix=".env.", dir=target.parent, text=True)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write("\n".join(lines).rstrip() + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tempname, target)
        os.chmod(target, 0o600)
    finally:
        if os.path.exists(tempname):
            os.unlink(tempname)
    print("Imported Vasto OIDC credentials into the private Workspaces .env; secret value was not displayed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
