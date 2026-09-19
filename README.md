# MEasyMate AI Hub V1 — Phase 1 Termux Baseline v2

Minimal provider-neutral AI Hub baseline for Android + Termux.

- Python standard library only — no pip install required
- `GET /health`
- `POST /v1/ai/generate`
- DeepSeek provider adapter behind a provider router
- DeepSeek API key is read only from server environment or local `.env`
- `.env` is ignored by Git
- No authentication/rate limit yet (planned Phase 2)

Run tests:

```sh
bash run_tests.sh
```

Run local server:

```sh
python -m app.main
```
