# Repository Guidelines

## Project Structure & Module Organization
- `core/`: TypeScript orchestration runtime, web API, safety/audit/memory logic, and Vitest suites.
- `modules/`: Python hardware/IO modules (`voice`, `motion`, `sensor`, `display`, `button`, `mock`) plus shared IPC helpers in `modules/common/`.
- `modules/tests/`: Pytest-based module tests.
- `deploy/`: Raspberry Pi install and systemd assets (`install.sh`, `mcar.service`).
- `docs/`: deployment and manual verification guides.
- `legacy/`: historical implementation and migration references; avoid new feature work here.

## Build, Test, and Development Commands
- Core setup and run:
  - `cd core && npm install`
  - `npm run dev` (run orchestrator in dev mode)
  - `npm run build` (compile TypeScript to `core/dist/`)
- Core tests:
  - `cd core && npm test` (Vitest once)
  - `npm run test:coverage` (coverage report)
- Python modules:
  - `cd modules && pip3 install -e ".[dev]"`
  - On Raspberry Pi with hardware: `pip3 install -e ".[hw,voice,display,dev]"`
  - `cd modules && pytest`
- Full device install: `./deploy/install.sh`

## Coding Style & Naming Conventions
- TypeScript: ESM, 2-space indentation, double quotes, explicit types on public APIs.
- Python: PEP 8 with Ruff settings (`line-length = 100`, target `py311`).
- File naming:
  - TS files use kebab-case (e.g., `session-controller.ts`).
  - Python tests use `test_*.py`; module entrypoints stay as `module.py`.
- Capability IDs follow `tool.<module>.<action>` (e.g., `tool.voice.recognize`).

## Testing Guidelines
- Core tests live in `core/tests/unit/` and `core/tests/integration/` using Vitest.
- Python tests live in `modules/tests/` using Pytest (+ `pytest-asyncio` where needed).
- Add/update tests with behavior changes; include at least one failure-path test for new capabilities.

## Commit & Pull Request Guidelines
- Prefer Conventional Commit prefixes used in history (`feat:`, `refactor:`, `fix:`).
- Keep commits focused by layer (`core`, `modules`, `deploy`, `docs`).
- PRs should include:
  - concise problem/solution summary,
  - linked issue/task,
  - test evidence (`npm test`, `pytest`, or manual API checks),
  - hardware impact notes (GPIO/I2C/audio changes) when applicable.

## Security & Configuration Tips
- Never commit secrets. Use `.ai_pet_env` (from `.ai_pet_env.example`) for API keys.
- Validate risky behavior through policy/stop flows before enabling physical movement commands.
