# mcar 树莓派 Codex 测试执行手册

## 1. 目标
在树莓派上让 Codex 完成发布前全量验收（重点 Gate C），并产出可审计的 Go/No-Go 报告。

## 2. 前置条件
- 代码已在树莓派上拉到最新（建议干净工作区）。
- `GEMINI_API_KEY` 已在 `.ai_pet_env` 配置。
- 具备硬件时执行全量；缺失硬件允许标记 `N/A-HW-MISSING`。
- 安全前置：运动测试前抬轮离地，急停按钮可触达。

## 3. 给 Codex 的一次性指令（直接粘贴）
```text
请在当前仓库执行 mcar 发布前真机验收，按 Gate P/A/B/C 顺序执行并输出 Go/No-Go 报告。
硬性要求：
1) 契约优先级：modules/*/capabilities.json > core/src/web/server.ts > docs/TESTING.md。
2) 参数/字段必须使用：
   - /api/chat: text
   - tool.motion.*: duration_ms
   - tool.voice.recognize: timeout_s
   - tool.sensor.infrared 返回 left_obstacle/right_obstacle
3) 失败即阻断；硬件缺失仅可记 N/A-HW-MISSING，且必须写风险说明。
4) 执行并保存证据到 docs/verification/run-YYYY-MM-DD_HH-MM-SS/：
   - 命令日志
   - API 响应 JSON
   - 最终 report.md（PASS/FAIL/NA 明细 + 阻断问题 + 复测建议）
5) 除非我明确同意，不要删除或回滚我的现有改动。
```

## 4. 执行顺序（你可口头监督）
1. Gate P（环境）
- 检查 `node -v`、`python3 -V`、`.ai_pet_env`、关键 key。
- 推荐 Python 3.12：`uv venv .venv-py312 --python 3.12`，并激活。

2. Gate A（自动化）
- `cd core && npm install && npm run build && npm test && npm run test:coverage`
- `cd modules && uv pip install --python "$(command -v python)" ".[dev]" && pytest -q`

3. Gate B（服务+契约）
- 启动服务：`cd core && node dist/index.js`
- 验证核心 API：`/api/status /api/modules /api/capabilities /api/health /api/watchdog /api/metrics /api/audit /api/sessions /api/rules/status /api/chat /api/invoke /api/stop /api/mode`
- 负向用例必须覆盖：无效 capability、越界 `duration_ms`、非法 mode。

4. Gate C（真机 T1-T10）
- 严格执行 `docs/TESTING.md` 全表（48 项）。
- 必测链路：Web/物理急停、模式切换、运动、传感器、记忆导入导出、审计导出、会话回放、规则评估。

## 5. 交付标准
- Go：Gate A/B/C 全通过，且无未解释高风险 N/A。
- No-Go：任一 Gate 失败、急停失败、契约不一致。
- 最终报告必须包含：
  - 总体结论（Go/No-Go）
  - 执行范围与环境
  - 通过/失败/N-A 明细（含原因码）
  - 阻断问题清单（按优先级）
  - 复测建议（可执行命令）
