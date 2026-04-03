# StratifyAI Phase 15 Security Runbook

This runbook captures the security baseline introduced in Phase 15 and how to operate it safely in staging and production.

## 1. Threat model assumptions

- Public clients can reach API endpoints and WebSocket stream endpoint.
- Provider API keys and bearer auth tokens are high-value secrets and must never appear in logs or API error payloads.
- Clients may send malformed, oversized, or hostile JSON payloads.
- Anonymous traffic and shared IP traffic are expected.
- Browser clients must be restricted by CORS in production.

## 2. Security controls implemented

- Error sanitization before logging and response details.
- HTTP rate limiting keyed by hashed bearer token when present, with IP fallback.
- WebSocket request bucket keyed by hashed bearer token when present, with IP fallback.
- WebSocket payload size guard and message content validation.
- Safer CORS defaults with explicit allow-all override.
- CI dependency vulnerability scan with pip-audit.

## 3. Environment configuration

Use these variables in production:

- STRATIFYAI_API_KEY: required for API auth.
- CORS_ALLOWED_ORIGINS: required allowlist for browser origins.
- CORS_ALLOW_ALL: keep false in production.

Recommended production values:

- STRATIFYAI_API_KEY: a long random secret.
- CORS_ALLOWED_ORIGINS: https://app.example.com,https://admin.example.com
- CORS_ALLOW_ALL: false

Recommended staging values:

- STRATIFYAI_API_KEY: separate non-production secret.
- CORS_ALLOWED_ORIGINS: staging app origins only.
- CORS_ALLOW_ALL: false

Local development defaults:

- If STRATIFYAI_API_KEY is unset, auth is disabled.
- If CORS_ALLOWED_ORIGINS is unset, localhost origins are allowed.
- CORS_ALLOW_ALL can be set true only for temporary local testing.

## 4. Startup checklist

1. Activate environment.
   - source .venv/bin/activate
2. Confirm security env vars are set.
   - echo $STRATIFYAI_API_KEY
   - echo $CORS_ALLOWED_ORIGINS
   - echo $CORS_ALLOW_ALL
3. Start API.
   - uv run uvicorn api.main:app --host 0.0.0.0 --port 8080
4. Validate health endpoint.
   - curl -s http://localhost:8080/api/health

## 5. Security verification commands

API auth checks:

- Missing token should fail:
  - curl -i http://localhost:8080/api/providers
- Invalid token should fail:
  - curl -i -H "Authorization: Bearer invalid" http://localhost:8080/api/providers
- Valid token should pass:
  - curl -i -H "Authorization: Bearer $STRATIFYAI_API_KEY" http://localhost:8080/api/providers

CORS checks:

- Preflight should include expected allow-origin for configured origins:
  - curl -i -X OPTIONS http://localhost:8080/api/chat -H "Origin: https://app.example.com" -H "Access-Control-Request-Method: POST"

Dependency vulnerability scan:

- uvx pip-audit -r requirements.txt

Test suite checks for hardening:

- uv run pytest tests/test_phase80_hardening.py -q
- uv run pytest tests/test_phase80_critical.py -q

## 6. Operational guidance

Rate limiting:

- Authenticated traffic is grouped by hashed token key.
- Unauthenticated traffic is grouped by client IP.
- If clients report 429 responses, verify whether one shared API key is reused across many clients.

WebSocket input constraints:

- Very large payloads are rejected.
- Message role must be one of system, user, assistant.
- Message content with disallowed control characters is rejected.

Error handling and logging:

- Key-like values should be redacted in logs and API error detail payloads.
- If a raw key appears in logs, treat as incident and rotate affected credentials immediately.

## 7. Incident response quick actions

1. Rotate secrets immediately.
   - STRATIFYAI_API_KEY
   - provider keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
2. Tighten CORS to known origins.
3. Increase monitoring on 401, 403, 413, and 429 responses.
4. Re-run tests and vulnerability scan.
   - uv run pytest tests/test_phase80_hardening.py -q
   - uvx pip-audit -r requirements.txt
5. Capture timeline and affected endpoints for post-incident review.

## 8. Release gate for production

Ship only when all are true:

- STRATIFYAI_API_KEY is configured.
- CORS_ALLOWED_ORIGINS is configured and limited.
- CORS_ALLOW_ALL is false.
- tests/test_phase80_hardening.py passes.
- pip-audit reports no unapproved vulnerabilities.
