#!/usr/bin/env python3
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

ENV_PATH = Path(".env")
TOKEN_PATH = Path(".client-token")

def update_env(key: str, value: str) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    out, found = [], False
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
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    clients = [{
        "client_id": "coach-dev-installation-1",
        "license_id": "COACH-DEV-001",
        "product_id": "coach",
        "token_sha256": digest,
        "enabled": True,
        "requests_per_minute": 10,
        "daily_request_quota": 100,
    }]
    products = [{
        "product_id": "coach",
        "ai_enabled": True,
        "ai_mode": "AUTO",
        "allowed_profiles": ["coach-understanding"],
    }]
    entitlements = [{
        "license_id": "COACH-DEV-001",
        "product_id": "coach",
        "plan": "COACH_AI_TRIAL",
        "ai_enabled": True,
        "expires_at": expires,
        "monthly_token_quota": 200000,
    }]
    update_env("AI_HUB_CLIENTS_JSON", json.dumps(clients, separators=(",", ":")))
    update_env("AI_HUB_PRODUCTS_JSON", json.dumps(products, separators=(",", ":")))
    update_env("AI_HUB_ENTITLEMENTS_JSON", json.dumps(entitlements, separators=(",", ":")))
    TOKEN_PATH.write_text(token + "\n", encoding="utf-8")
    os.chmod(TOKEN_PATH, 0o600)
    os.chmod(ENV_PATH, 0o600)
    print("Coach development entitlement created.")
    print("Product: coach | AI mode: AUTO | Plan: COACH_AI_TRIAL | 30 days | 200000 tokens/month.")
    print("Server stores token hash only; raw token saved in .client-token (gitignored).")

if __name__ == "__main__":
    main()
