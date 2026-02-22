# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

mcar 是一个运行在树莓派上的 Agent 交互机器人系统，采用 Robot-first 设计理念（语音优先交互）。系统通过外部大模型 API（Gemini）进行推理，具备语音交互、硬件能力扩展、持久记忆和安全门禁等核心功能。

- **目标平台**: Raspberry Pi 4B + Raspberry Pi OS 64-bit
- **语言**: TypeScript (core) + Python (modules)
- **LLM**: Google Gemini API（外部调用，不在本地运行）
- **许可**: MIT

## Repository Structure

- `Req.md` — 需求文档（PRD/RFC），定义功能性与非功能性需求
- `HLD.md` — 高层设计文档，定义系统架构、组件职责、数据流
- `Spec.md` — 详细规格：Capability Spec（JSON Schema）、错误码规范、幂等策略、Memory Spec
- `core/` — TypeScript 核心系统（Orchestrator, Agent, Safety, Memory, Web）
- `modules/` — Python 能力模块（mock, voice, display, motion, sensor, button）
- `deploy/` — 部署配置（systemd service, install script）
- `legacy/` — 上一代实现，**仅作参考**
- `.ai_pet_env.example` — 环境变量模板

## Architecture

系统按 HLD.md 设计，核心组件：

| 组件 | 职责 |
|------|------|
| **Orchestrator** | 会话状态机（FSM: IDLE→LISTENING→THINKING→PLANNING→CONFIRMING→EXECUTING→RESPONDING）、路由、调度 |
| **Agent Runtime** | LLM 适配层，将输入+上下文+能力清单送入模型，产出文本回复和 action_plan |
| **Capability Registry** | 能力模块加载/管理/发现 |
| **Capability Executor** | 参数校验、速率限制、超时控制、幂等去重、并发控制（max_in_flight + mutex_group）、结果标准化 |
| **Safety Policy Engine** | 风险分级门禁（READ_ONLY/NORMAL/DANGEROUS）、确认流程、急停、冷却窗口 |
| **Memory Service** | 结构化记忆的写入/检索/撤销/注入策略、TTL 过期清理 |
| **State Service** | 统一状态视图（模式/健康/风险/最近动作） |

### Key Design Principles

1. **能力即插件**: 硬件/服务能力以 Capability Module 形式接入，Agent 只看能力声明
2. **安全优先**: 危险能力有代码级硬门禁、急停、降级；不依赖 prompt 自觉
3. **记忆可控**: 结构化、可审计、可撤销；默认最小化注入上下文
4. **故障隔离**: 单模块崩溃不影响核心；Watchdog 自动重启崩溃模块

### Capability Module Contract

每个模块必须实现: `manifest()`, `capabilities()`, `invoke(capability_id, input, context)`, `health()`。
危险模块强烈建议实现 `stop()` 和 `cancel(invocation_id)`。

能力风险分级: `READ_ONLY`（默认允许）→ `NORMAL`（参数边界+速率限制）→ `DANGEROUS`（确认/权限/状态门禁）。

### Error Codes

统一错误码前缀: `E_INPUT_*`, `E_STATE_*`, `E_POLICY_*`, `E_RATE_*`, `E_TIMEOUT`, `E_CANCELLED`, `E_NOT_FOUND`, `E_DEPENDENCY_*`, `E_INTERNAL`, `E_DUPLICATE`, `E_CONCURRENCY`。

### Memory Types

- **Session Memory**: 单次会话上下文
- **Long-term Memory**: 跨会话持久化（preference/fact/rule/task/incident 等）
- **Device Memory**: 硬件相关（校准/限制/故障历史/能力清单）

## M2 Components (Voice + Display + Web + Stability)

| 组件 | 位置 | 说明 |
|------|------|------|
| **Voice Module** | `modules/voice/` | ASR (Google STT) + TTS (Edge TTS) + 唤醒词 (Porcupine)，mock fallback |
| **Display Module** | `modules/display/` | SSD1306 OLED 128x64 表情/文本渲染，mock fallback |
| **Sensor Module** | `modules/sensor/` | HC-SR04 超声波 + IR 红外障碍物检测，mock fallback |
| **Mode System** | `core/src/state/` | 5 种模式 (normal/safety/kid/debug/mute)，速度上限联动 |
| **Voice Loop** | `core/src/orchestrator/voice-loop.ts` | 唤醒词→ASR→Agent→TTS 语音交互循环 |
| **CONFIRMING Flow** | `core/src/orchestrator/action-dispatcher.ts` | 危险操作确认流程 + 确认/拒绝关键词 |
| **Memory Proposal** | `core/src/agent/tool-adapter.ts` | Agent 隐式记忆提议 (tool.memory.propose/list) |
| **API Degradation** | `core/src/agent/degradation-handler.ts` | 连续 3 次 API 失败→离线模式→基本命令解析 |
| **Web Console** | `core/src/web/` | Express + WebSocket，REST API + 单文件 UI (port 8080) |

## M3 Components (Skill System + Management + Monitoring)

| 组件 | 位置 | 说明 |
|------|------|------|
| **Skill Engine** | `core/src/skill/skill-engine.ts` | 多工具组合技能引擎：条件执行、参数替换、重试、取消 |
| **Built-in Skills** | `core/src/skill/builtin-skills.ts` | 内置技能：self_check、night_mode、patrol |
| **Memory Management** | `core/src/agent/tool-adapter.ts` | Agent 记忆删除/清除工具 (tool.memory.delete/clear) |
| **Memory Export** | `core/src/memory/memory-export.ts` | 记忆导出/导入（JSON 格式备份） |
| **Audit Store** | `core/src/audit/audit-store.ts` | SQLite 持久化审计日志，支持按 trace/type 查询 |
| **Health Monitor** | `core/src/health/health-monitor.ts` | 定时模块健康检查，聚合系统健康状态 |

## M4 Components (Production Readiness)

| 组件 | 位置 | 说明 |
|------|------|------|
| **Session Recorder** | `core/src/audit/session-recorder.ts` | 会话事件流录制与回放，支持按 session ID 检索 |
| **Cleanup Scheduler** | `core/src/health/cleanup-scheduler.ts` | 定时清理过期记忆 (TTL) + 审计日志轮转 (默认 30 天) |
| **Module Watchdog** | `core/src/health/module-watchdog.ts` | 模块进程守护：崩溃检测、指数退避重启、永久失败标记 |
| **Deploy Config** | `deploy/` | systemd service 文件 + 安装脚本 |

## M5 Components (Executor Enhancement + Automation)

| 组件 | 位置 | 说明 |
|------|------|------|
| **Concurrency Control** | `core/src/capability/executor.ts` | max_in_flight 限制 + mutex_group 互斥锁（如 motion 组防止同时前进和后退） |
| **Audit Redactor** | `core/src/audit/redactor.ts` | 字段级审计脱敏：MASK/HASH/DROP，支持嵌套 json_path |
| **Rule Engine** | `core/src/automation/rule-engine.ts` | 基于 memory(type=rule) 的自动化引擎：time_range/state 条件 → set_mode/invoke 动作 |
| **Watchdog API** | `core/src/web/server.ts` | GET /api/watchdog 模块进程状态 |
| **Enhanced Context** | `core/src/orchestrator/context-builder.ts` | 上下文注入增强：可选注入模块健康状态 |

## M6 Components (Security Hardening + Observability + DX)

| 组件 | 位置 | 说明 |
|------|------|------|
| **Retry Policy** | `core/src/capability/executor.ts` | IPC invoke 重试循环：指数退避、可重试错误过滤、并发槽保持 |
| **Performance Tracker** | `core/src/observability/performance-tracker.ts` | 操作延迟记录与百分位指标（p50/p95/p99），maxEntries 防内存膨胀 |
| **Incident Recorder** | `core/src/observability/incident-recorder.ts` | 自动捕获 module_crash/tool_error/api_degradation 为 incident 记忆，60s 去重，7天 TTL |
| **Module Template** | `modules/template/` + `scripts/new-module.sh` | 模块脚手架生成器：snake_case → PascalCase，生成 module.py/capabilities.json/测试 |
| **Metrics API** | `core/src/web/server.ts` | GET /api/metrics 返回所有操作的延迟百分位指标 |
| **Audit duration_ms** | `core/src/audit/types.ts` | AuditEvent 支持 duration_ms 字段 + AuditLogger.timed() 便利方法 |

## M7 Components (Integration Fix + Security Hardening + Memory Proposal)

| 组件 | 位置 | 说明 |
|------|------|------|
| **IncidentRecorder TTL Fix** | `core/src/observability/incident-recorder.ts` | TTL 单位修复：ms→s，确保 7 天过期生效 |
| **IncidentRecorder → AgentRuntime** | `core/src/agent/agent-runtime.ts` | 工具执行错误自动记录 incident 记忆 |
| **Dispatch PerformanceTracker** | `core/src/orchestrator/action-dispatcher.ts` | dispatch.cycle 端到端延迟记录 |
| **Privacy Filter Tests** | `core/tests/unit/memory-service.test.ts` | 隐私过滤安全关键路径测试覆盖 |
| **Voice Retry + Concurrency** | `modules/voice/capabilities.json` | recognize/synthesize 增加 retry_policy，synthesize 增加 max_in_flight:1 |
| **Memory Proposal Closure** | `core/src/orchestrator/action-dispatcher.ts` | Agent 记忆提议→用户确认→MemoryService 写入闭环 |
| **ContextBuilder Unification** | `core/src/agent/prompt-builder.ts` | PromptBuilder 通过 ContextBuilder 获取上下文，消除重复，支持模块健康注入 |

## M8 Components (Feature Completion + E2E Tests)

| 组件 | 位置 | 说明 |
|------|------|------|
| **Motion Module Tests** | `modules/tests/test_motion_module.py` | 运动模块完整测试覆盖：驱动、invoke、急停、Spec 验证 |
| **Keyword Extractor** | `core/src/memory/keyword-extractor.ts` | 轻量级中英文关键词提取 + 相关性评分（无外部 NLP 依赖） |
| **Relevance Search** | `core/src/memory/memory-store.ts` | searchRelevant 基于关键词标签的语义相关检索 |
| **Button Module** | `modules/button/` | GPIO 物理急停按钮模块：中断检测、去抖、mock 兜底、IPC emergency_stop 事件 |
| **Session Summarizer** | `core/src/agent/session-summarizer.ts` | 长对话压缩：LLM 摘要优先 + 本地关键词兜底，保留最近 N 轮 |
| **E2E Flow Tests** | `core/tests/integration/e2e-flow.test.ts` | 端到端集成测试：文本流、急停、确认流、记忆提议、模式策略 |

## M9 Components (Multi-turn Voice + Whisper ASR + DashScope LLM)

| 组件 | 位置 | 说明 |
|------|------|------|
| **Multi-turn Voice Session** | `core/src/orchestrator/voice-loop.ts` | 唤醒词后进入连续对话循环（ASR→Agent→TTS→ASR...），ASR 超时自动退出回到唤醒词等待 |
| **FSM RESPONDING→LISTENING** | `core/src/orchestrator/session-controller.ts` | 新增 RESPONDING→LISTENING 合法转换，支持多轮对话不回 IDLE |
| **Whisper ASR** | `modules/voice/driver.py` | 局域网 Whisper HTTP ASR 替代 Google STT，绕过代理，支持中文 |
| **Whisper Hallucination Filter** | `modules/voice/driver.py` | 三层过滤：RMS 能量检测（<300=静音）、短音频过滤（<0.5s）、已知幻觉短语检测 |
| **DashScope/Qwen LLM** | `core/src/agent/agent-runtime.ts` | 阿里云百炼 DashScope OpenAI 兼容 API，resolveModel() 自动构建自定义 Provider |
| **Voice Output Cleaning** | `core/src/orchestrator/action-dispatcher.ts` | cleanResponseForVoice()：剥离 `<think>` 思考块、emoji、markdown，截断至 200 字 |
| **TTS Volume Boost** | `modules/voice/driver.py` | ffmpeg +8dB 音量增益，解决树莓派扬声器音量不足 |
| **systemd Service** | `deploy/mcar.service` | 完整 systemd 配置：venv PATH、EnvironmentFile、KillMode=control-group 确保子进程清理 |
| **System Prompt 优化** | `core/src/agent/prompt-builder.ts` | Voice Output Rules：简短回复（≤50字）、口语化中文、禁止 emoji/思考过程 |

### Next Phase: soul.md

下一阶段任务：编写 `soul.md`，定义机器人的人格与行为准则：
- **Identity**: 身份定义（名字、角色、定位）
- **Mission**: 使命与目标
- **Values**: 核心价值观
- **Voice & Style**: 语言风格、语气、表达方式
- **Memory**: 记忆策略与人格一致性

### Web API Endpoints

**核心端点：**
- `GET /api/status` — 状态快照
- `GET /api/capabilities` — 能力列表
- `POST /api/invoke` — 调用能力
- `POST /api/stop` — 急停
- `POST /api/mode` — 模式切换
- `POST /api/chat` — 文本对话
- `WS /ws` — 实时推送

**记忆管理：**
- `GET /api/memories` — 记忆列表
- `GET /api/memories/search?q=keyword` — 关键词搜索
- `DELETE /api/memories/:id` — 删除记忆
- `POST /api/memories/clear` — 按类型清除
- `GET /api/memories/export` — 导出记忆
- `POST /api/memories/import` — 导入记忆

**模块管理：**
- `GET /api/modules` — 模块列表
- `POST /api/modules/:id/enable` — 启用模块
- `POST /api/modules/:id/disable` — 禁用模块

**技能系统：**
- `GET /api/skills` — 技能列表
- `POST /api/skills/:id/execute` — 执行技能

**审计、健康、会话与自动化：**
- `GET /api/audit` — 审计日志（最近 100 条）
- `GET /api/audit/export` — 导出全部审计日志
- `GET /api/health` — 系统健康状态
- `GET /api/metrics` — 操作延迟百分位指标（p50/p95/p99）
- `GET /api/sessions` — 会话列表
- `GET /api/sessions/:id/replay` — 会话回放
- `GET /api/watchdog` — 模块进程状态
- `GET /api/rules/status` — 规则引擎状态
- `POST /api/rules/evaluate` — 手动触发规则评估

### Running Tests

```bash
# TypeScript (272 tests)
cd core && npx vitest run

# Python (103 tests)
python -m pytest modules/tests/ -v

# Run single test file
cd core && npx vitest run tests/unit/skill-engine.test.ts
```

### Deployment

```bash
# Install on Raspberry Pi
chmod +x deploy/install.sh
./deploy/install.sh

# Manual start
cd core && node dist/index.js

# systemd (after install.sh)
sudo systemctl start mcar
journalctl -u mcar -f
```

## Environment Setup

```bash
# 复制环境变量模板并填入 API keys
cp .ai_pet_env.example .ai_pet_env
# LLM 配置（二选一）:
#   GEMINI_API_KEY — Google Gemini
#   DASHSCOPE_API_KEY + LLM_PROVIDER=dashscope + LLM_MODEL=qwen-plus — 阿里云百炼
# 语音: PICOVOICE_ACCESS_KEY, WHISPER_URL (局域网 Whisper 服务地址)
# 可选: WEB_PORT, WEB_HOST, LLM_BASE_URL

# systemd 部署需要单独的 env 文件（不含 export 前缀）:
# .ai_pet_env.systemd — 纯 KEY=value 格式，systemd EnvironmentFile 不支持 export
```

## Development Notes

- 急停链路（STOP_EVENT）不得依赖模型推理，必须硬编码最高优先级
- 模块进程由 ModuleWatchdog 管理，崩溃后自动重启（指数退避，最多 5 次）
- 记忆注入上下文有条数上限（默认 5 条），敏感信息默认不自动注入
- 幂等策略: 运动/高风险动作推荐 `DEDUP_ONLY` + 短 TTL
- CleanupScheduler 每小时自动清理过期记忆和 30 天前的审计日志
- 并发控制: 运动类能力建议设 `max_in_flight: 1` + `mutex_group: "motion"` 防止冲突
- 审计脱敏: 通过 `ObservabilitySpec.redaction` 配置字段级 MASK/HASH/DROP 规则
- RuleEngine 定时扫描 type=rule 记忆，支持 time_range/state 条件触发 set_mode/invoke
- 重试策略: 通过 `ConstraintsSpec.retry_policy` 配置 retriable_errors/max_retries/backoff_ms，指数退避
- PerformanceTracker 默认最多保留 1000 条记录/操作，通过 GET /api/metrics 查看延迟指标
- IncidentRecorder 自动捕获模块崩溃/工具错误/API降级为 incident 记忆，60s 去重窗口，7天自动过期
- 新模块脚手架: `./scripts/new-module.sh <module_id> [description]` 自动生成模块代码和测试
- IncidentRecorder TTL 以秒为单位传给 MemoryStore（与 cleanExpired SQL 一致）
- AgentRuntime 构造时接收 IncidentRecorder，工具执行错误自动写 incident 记忆
- ActionDispatcher 通过 requestMemoryConfirmation() 支持记忆提议闭环：确认→写入，拒绝/超时→丢弃
- PromptBuilder 通过 ContextBuilder 统一获取上下文（记忆/状态/能力/模块健康），消除与 ContextBuilder 的重复调用
- Voice 模块 recognize/synthesize 配置了 retry_policy（E_TIMEOUT + E_DEPENDENCY_NETWORK），synthesize 限制 max_in_flight:1 防音频重叠
- Button 模块通过 GPIO 中断检测按钮（BCM17, FALLING edge, 200ms 去抖），按下后发 IPC emergency_stop 事件触发 StopHandler
- SessionSummarizer 在消息超过阈值（默认 20）时压缩历史：LLM 摘要优先，失败回退本地关键词提取
- MemoryService.searchRelevant() 基于关键词匹配 tag（权重 3）和 summary（权重 1）进行相关性排序
- 多轮语音对话：唤醒后进入 ASR→Agent→TTS 循环，期间暂停唤醒词检测，ASR 超时即退出循环恢复唤醒词
- Whisper ASR 通过 HTTP POST 到局域网服务（WHISPER_URL），使用 `urllib` 绕过系统代理（ProxyHandler({})）
- Whisper 幻觉过滤：RMS 能量 < 300 判为静音跳过、音频 < 0.5s 跳过、已知幻觉短语（"谢谢观看"等）过滤
- DashScope/Qwen 通过 OpenAI 兼容 API 接入，resolveModel() 先查 pi-ai 内置注册表，未找到则构建自定义 Model 对象
- cleanResponseForVoice() 在 ActionDispatcher 中清洗 LLM 回复：去 `<think>` 块、去 emoji/markdown、截断 200 字
- systemd 部署注意：EnvironmentFile 不支持 `export` 前缀和 shell 变量展开，需用 `.ai_pet_env.systemd` 纯 KEY=value 格式
- systemd KillMode=control-group 确保 stop 时杀掉所有子进程（Python 模块进程）
