#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ENV_PATH = Path(".env")

def read_env() -> dict[str, str]:
    result = {}
    if not ENV_PATH.exists():
        return result
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        result[k] = v
    return result

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
        out.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")

def main():
    if len(sys.argv) < 3:
        raise SystemExit("Usage: manage_coach_ai.py product OFF|AUTO|ON  OR  license LICENSE_ID ON|OFF")
    env = read_env()
    kind = sys.argv[1].lower()

    if kind == "product":
        mode = sys.argv[2].upper()
        if mode not in {"OFF", "AUTO", "ON"}:
            raise SystemExit("Mode must be OFF, AUTO or ON")
        data = json.loads(env.get("AI_HUB_PRODUCTS_JSON", "[]"))
        found = False
        for item in data:
            if item.get("product_id") == "coach":
                item["ai_mode"] = mode
                item["ai_enabled"] = mode != "OFF"
                found = True
        if not found:
            raise SystemExit("Coach product policy not found")
        update_env("AI_HUB_PRODUCTS_JSON", json.dumps(data, separators=(",", ":")))
        print(f"Coach product AI mode set to {mode}. Restart AI Hub to apply.")
        return

    if kind == "license":
        if len(sys.argv) < 4:
            raise SystemExit("Usage: manage_coach_ai.py license LICENSE_ID ON|OFF")
        license_id = sys.argv[2]
        state = sys.argv[3].upper()
        if state not in {"ON", "OFF"}:
            raise SystemExit("State must be ON or OFF")
        data = json.loads(env.get("AI_HUB_ENTITLEMENTS_JSON", "[]"))
        found = False
        for item in data:
            if item.get("license_id") == license_id and item.get("product_id") == "coach":
                item["ai_enabled"] = state == "ON"
                found = True
        if not found:
            raise SystemExit("Coach entitlement not found")
        update_env("AI_HUB_ENTITLEMENTS_JSON", json.dumps(data, separators=(",", ":")))
        print(f"{license_id} Coach AI set to {state}. Restart AI Hub to apply.")
        return

    raise SystemExit("Unknown command")

if __name__ == "__main__":
    main()
