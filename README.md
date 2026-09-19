# MEasyMate AI Hub V1 — Coach Entitlement Reference

Coach is the first MEasyMate product using the central AI entitlement contract.

## Current capabilities

- `GET /health`
- `GET /v1/ai/status` — authenticated Coach checks whether AI is available
- `POST /v1/ai/generate`
- Bearer installation/client authentication
- Identity bound server-side to `client_id` + `license_id` + `product_id`
- Product-level AI kill switch: `OFF / AUTO / ON`
- Per-license AI entitlement: plan, on/off, expiry, monthly token quota
- Per-client request/minute and daily request quota
- Monthly token usage shared across installations that use the same license
- `coach-understanding` AI profile for Coach language/context assistance
- Provider key remains server-side only
- Coach can fall back to No-AI Core when status says AI is unavailable

Important: quota/token counters are still **in memory** and reset when the Hub process restarts. This branch is a field-trial/development entitlement baseline, not yet the paid production billing backend. Persistent storage/admin payment activation is the next hardening step.

## Create a Coach development entitlement

```sh
python scripts/create_dev_client.py
```

This creates:
- `product_id=coach`
- `license_id=COACH-DEV-001`
- AI mode `AUTO`
- plan `COACH_AI_TRIAL`
- 30-day expiry
- 200,000 token/month development quota
- one installation token in `.client-token`

`.env` and `.client-token` are gitignored.

## Test

```sh
bash run_tests.sh
```

## Run

```sh
python -m app.main
```

## Check Coach AI status

```sh
TOKEN=$(cat .client-token)
curl -s http://127.0.0.1:8000/v1/ai/status   -H "Authorization: Bearer $TOKEN"
```

## Coach understanding request

```sh
TOKEN=$(cat .client-token)
curl -s -X POST http://127.0.0.1:8000/v1/ai/generate   -H "Authorization: Bearer $TOKEN"   -H "Content-Type: application/json"   -d '{"profile":"coach-understanding","messages":[{"role":"user","content":"พนักงานเพิ่งทำรุ่นนี้ครั้งแรก ยังไม่ได้สอนงาน"}],"options":{"max_output_tokens":120}}'
```

## Owner control

Global Coach AI:

```sh
python scripts/manage_coach_ai.py product OFF
python scripts/manage_coach_ai.py product AUTO
python scripts/manage_coach_ai.py product ON
```

Per-license AI:

```sh
python scripts/manage_coach_ai.py license COACH-DEV-001 OFF
python scripts/manage_coach_ai.py license COACH-DEV-001 ON
```

Restart the Hub after changing `.env`.

## Contract

AI assists Core Coach with understanding language, context, information type, coherence, and candidate next questions. AI does **not** decide Root Cause, pass Root Cause gates, choose corrective action, or close the case. Those remain under Core Coach + user control.

## Phase 4 — Coach Browser Bridge

- `POST /v1/coach/understand` accepts bounded Coach context, not arbitrary chat messages.
- The Hub injects a locked Coach Understanding system prompt server-side.
- Provider output is normalized to an **UNTRUSTED proposal** and forbidden decision fields are discarded.
- `AI_HUB_CORS_ORIGINS_JSON` controls browser origins. For local Android HTML use `["null"]`; production should list only exact HTTPS origins.
- Coach continues to use the deterministic offline Core when the Hub is unavailable or AI entitlement is off.
