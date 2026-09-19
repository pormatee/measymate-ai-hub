# MEasyMate AI Hub V1 — Phase 2 Termux Baseline

Provider-neutral AI Hub for Android + Termux.

Current capabilities:
- `GET /health`
- `POST /v1/ai/generate`
- DeepSeek adapter behind provider router
- Bearer client authentication
- Authenticated identity -> `client_id` + `product_id`
- Per-client requests/minute rate limit
- Per-client daily request quota
- Quota/rate checks happen before provider call
- Raw client token is never stored in server registry; SHA-256 hash only
- Python standard library only

Important: Phase 2 limiter state is in memory and resets when the Hub restarts. This is development-only until persistent storage/hardening is added.

## Test

```sh
bash run_tests.sh
```

## Create one local development client

```sh
python scripts/create_dev_client.py
```

This preserves your existing `.env`, adds `AI_HUB_CLIENTS_JSON`, and writes the one-time client token to `.client-token`. Both `.env` and `.client-token` are gitignored.

## Run

```sh
python -m app.main
```

## Live request from another Termux session

```sh
TOKEN=$(cat .client-token)
curl -s -X POST http://127.0.0.1:8000/v1/ai/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"profile":"standard","messages":[{"role":"user","content":"ตอบสั้นๆว่า Phase 2 auth สำเร็จ"}],"options":{"max_output_tokens":100}}'
```
