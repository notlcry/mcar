# mcar Runtime Manual Check (2026-02-17)

## Context
- Runtime: Node v24.13.1 + Python 3.12 venv (`.venv-py312`)
- Note: This check was executed even though Gate A build is failing, for additional runtime evidence.

## Service startup findings
- Service can start under Node 24 after rebuilding `better-sqlite3`.
- `sensor` module repeatedly fails: `ModuleNotFoundError: No module named 'common'`.
- `button` health check repeatedly errors: `TypeError: object dict can't be used in 'await' expression`.

## API status checks
- 200 OK: `/api/status`, `/api/modules`, `/api/capabilities`, `/api/health`, `/api/watchdog`, `/api/metrics`, `/api/audit`, `/api/sessions`, `/api/rules/status`, `/api/invoke`, `/api/stop`, `/api/mode`.
- `POST /api/chat` with `{"text":"你好"}` -> 200 (`{"response": ... }`).
- `POST /api/chat` with `{"message":"你好"}` -> 400 (`{"error":"text required"}`).

## Negative checks
- Invalid capability (`tool.invalid.not_exist`) -> HTTP 200 with `success=false` and `E_NOT_FOUND` (expected behavior).
- Invalid mode (`invalid`) -> HTTP 400 (expected behavior).
- Out-of-range motion input (`speed=101`, `duration_ms=99999`) -> **HTTP 200 + success=true** (unexpected; should be rejected by contract validation).

## Runtime health evidence
- `/api/watchdog`: `sensor` has `permanentlyFailed=true` and `restartCount=5`.
- `/api/health`: `overall="degraded"`, `button` reported offline due health check failure.

## Conclusion
- Runtime evidence confirms major Gate B defects despite basic endpoint reachability:
  1. Sensor module import/path issue.
  2. Button health handler async contract bug.
  3. Motion input boundary validation not enforced.
