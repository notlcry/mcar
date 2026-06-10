# mcar API & Capability Contract Checklist

Release gate input for Gate B/C. Validate in this priority order:
1. `modules/*/capabilities.json`
2. `modules/robot_service/api.py` and `modules/robot_service/models.py`
3. `docs/TESTING.md`

## Core API Routes (must be reachable)
- `GET /api/status`
- `GET /api/modules`
- `GET /api/capabilities`
- `GET /api/health`
- `GET /api/watchdog`
- `GET /api/metrics`
- `GET /api/audit`
- `GET /api/sessions`
- `GET /api/rules/status`
- `POST /api/chat`
- `POST /api/invoke`
- `POST /api/voice/run_once`
- `POST /api/stop`
- `POST /api/mode`

## Capability Parameter Corrections (must use exact names)
- Chat API (`POST /api/chat`) payload:
  - use `text` (NOT `message`)
- Motion capabilities (`tool.motion.forward/backward/turn_left/turn_right`):
  - use `duration_ms` (NOT `duration`)
- Voice ASR (`tool.voice.recognize`):
  - use `timeout_s` (NOT `duration`)
- Voice E2E probe (`POST /api/voice/run_once`) payload:
  - use optional `source` to tag audit events
- Infrared sensor (`tool.sensor.infrared`) output keys:
  - `left_obstacle`, `right_obstacle`

## Negative Contract Cases (must fail)
- Unknown capability ID via `/api/invoke`
- Out-of-range motion input (e.g. `speed=101`, `duration_ms>5000`)
- Invalid mode via `/api/mode`

## Gate Decision Rules
- Contract mismatch on route, method, required field, or output key = **No-Go**.
- Hardware unavailable can be marked `N/A-HW-MISSING`, but contract mismatches cannot.
