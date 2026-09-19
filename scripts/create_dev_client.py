#!/usr/bin/env python3
import hashlib
import json
import os
import secrets
from pathlib import Path

ENV_PATH = Path(".env")
TOKEN_PATH = Path(".client-token")


def update_env(key: str, value: str) -> None:
    lines = []
    found = False
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        if line.startswith(f"{key}="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        if out and out[-1] != "":
            out.append("")
        out.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    token = "mmh_" + secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    registry = [{
        "client_id": "termux-dev-client",
        "product_id": "ai-hub-test",
        "token_sha256": digest,
        "enabled": True,
        "requests_per_minute": 10,
        "daily_request_quota": 100,
    }]
    update_env("AI_HUB_CLIENTS_JSON", json.dumps(registry, separators=(",", ":")))
    TOKEN_PATH.write_text(token + "\n", encoding="utf-8")
    os.chmod(TOKEN_PATH, 0o600)
    os.chmod(ENV_PATH, 0o600)
    print("Development client created.")
    print("Server registry stores only SHA-256 token hash.")
    print("Plain token saved locally in .client-token (gitignored, chmod 600).")


if __name__ == "__main__":
    main()
