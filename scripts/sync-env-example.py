#!/usr/bin/env python3
"""Append variables added to .env.example without changing local values."""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path


ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=")


def keys(text: str) -> set[str]:
    return {match.group(1) for line in text.splitlines() if (match := ASSIGNMENT.match(line))}


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: sync-env-example.py EXAMPLE ENV_FILE", file=sys.stderr)
        return 2

    example_path, env_path = map(Path, sys.argv[1:])
    example = example_path.read_text()
    current = env_path.read_text() if env_path.exists() else ""
    missing = [line for line in example.splitlines() if (match := ASSIGNMENT.match(line)) and match.group(1) not in keys(current)]
    if not missing:
        print("Environment fields are up to date.")
        return 0

    addition = "\n# New fields copied from .env.example; review values before use.\n" + "\n".join(missing) + "\n"
    updated = current.rstrip() + "\n" + addition if current.strip() else addition.lstrip()
    mode = 0o600
    if env_path.exists():
        mode = env_path.stat().st_mode & 0o777
    fd, temp_name = tempfile.mkstemp(prefix=f".{env_path.name}.", dir=env_path.parent)
    try:
        with os.fdopen(fd, "w") as temp_file:
            temp_file.write(updated)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.chmod(temp_name, mode)
        os.replace(temp_name, env_path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    print(f"Added {len(missing)} missing environment field(s); existing values were preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
