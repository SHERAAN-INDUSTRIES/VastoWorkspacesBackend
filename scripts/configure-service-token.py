#!/usr/bin/env python3
"""Securely prompt for and store the Pwaninet service token in .env."""

from __future__ import annotations

import os
import re
import sys
import tempfile
from getpass import getpass
from pathlib import Path


KEY = "VASTO_SERVICE_TOKEN"


def main() -> int:
    env_path = Path(sys.argv[1] if len(sys.argv) > 1 else ".env")
    if not sys.stdin.isatty():
        print(
            "Pwaninet service token is missing. Run setup in a terminal and enter the token when prompted.",
            file=sys.stderr,
        )
        return 2

    print("\nPwaninet connection")
    print("  Run Pwaninet setup first; its generated VASTO_SERVICE_TOKEN is in that repo's .env.")
    print("  Paste that token below. Input is hidden and the token will not be displayed.")
    try:
        token = getpass("  Pwaninet service token: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nToken setup cancelled; no token was written.", file=sys.stderr)
        return 130
    if not token or "\n" in token or "\r" in token:
        print("A non-empty, single-line token is required.", file=sys.stderr)
        return 2

    current = env_path.read_text() if env_path.exists() else ""
    lines = current.splitlines()
    pattern = re.compile(rf"^{re.escape(KEY)}=")
    replaced = False
    output: list[str] = []
    for line in lines:
        if pattern.match(line):
            if not replaced:
                output.append(f"{KEY}={token}")
                replaced = True
        else:
            output.append(line)
    if not replaced:
        output.extend(("", f"{KEY}={token}"))

    mode = (env_path.stat().st_mode & 0o777) if env_path.exists() else 0o600
    fd, temp_name = tempfile.mkstemp(prefix=f".{env_path.name}.", dir=env_path.parent)
    try:
        with os.fdopen(fd, "w") as temp_file:
            temp_file.write("\n".join(output).rstrip() + "\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.chmod(temp_name, mode & 0o600)
        os.replace(temp_name, env_path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    print("  Saved Pwaninet service token to .env (value hidden).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
