# Gate B Manual API Checks (2026-02-18)

- Environment:
  - Node: `v24.13.1`
  - Python venv: `/Users/xiaorain/code/mcar/.venv-py312`
  - Service: `node /Users/xiaorain/code/mcar/core/dist/index.js`

## Results

- `POST /api/chat` with `{"text":"你好"}` -> `200`, response present.
- `POST /api/chat` with `{"message":"你好"}` -> `400`, `{"error":"text required"}`.
- `POST /api/mode` with `{"mode":"mute"}` -> `200`, `{"ok":true,"mode":"mute"}`.
- `POST /api/mode` with `{"mode":"invalid"}` -> `400`, invalid mode rejected.
- `POST /api/stop` with `{}` -> `200`, emergency stop triggered.
- `POST /api/invoke` with `input` payload -> `200`, success true.
- `POST /api/invoke` with `params` payload -> `200`, success true.
- `POST /api/invoke` with out-of-range motion params -> `200`, `success:false` with `E_INPUT_SCHEMA`.

## Conclusion

- Missing Gate B endpoints from scripted checks are verified.
- Contract behavior matches current docs and negative-path expectations.
