# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

mcar 是一个运行在树莓派上的 Agent 交互机器人系统，采用 Robot-first 设计理念（语音优先交互）。系统通过外部大模型 API（Gemini）进行推理，具备语音交互、硬件能力扩展、持久记忆和安全门禁等核心功能。

- **目标平台**: Raspberry Pi 4B + Raspberry Pi OS 64-bit
- **语言**: Python Robot Service + Python hardware modules；`core/` 只保留历史 TypeScript runtime 与静态 Web UI 资产
- **LLM**: Pydantic AI provider（默认 Gemini，可切换 OpenAI/Anthropic/OpenRouter 等外部 API）
- **许可**: MIT

## Repository Structure

- `Req.md` — 需求文档（PRD/RFC），定义功能性与非功能性需求
- `HLD.md` — 高层设计文档，定义系统架构、组件职责、数据流
- `Spec.md` — 详细规格：Capability Spec（JSON Schema）、错误码规范、幂等策略、Memory Spec
- `modules/robot_service/` — 当前主运行时（FastAPI, Pydantic AI agent, safety, memory, audit, skills, rules）
- `modules/` — Python 能力模块（mock, voice, display, motion, sensor, button）
- `core/` — 历史 TypeScript runtime；当前部署不再依赖 Node/core 构建
- `deploy/` — 部署配置（systemd service, install script）
- `legacy/` — 上一代实现，**仅作参考**
- `.ai_pet_env.example` — 环境变量模板

## Architecture

系统按 HLD.md 设计，当前主入口是 `python -m robot_service`：

| 组件 | 职责 |
|------|------|
| **RobotService** | 会话/状态/工具调用编排，所有能力调用先过 safety 和 guards |
| **RobotAgent** | Pydantic AI agent 边界，负责 LLM 对话和强类型工具调用 |
| **CapabilityRegistry** | 从 Python 模块加载/管理/发现能力 |
| **SafetyRouter + ExecutionGuards** | JSON Schema 校验、模式/速度/障碍物/急停/并发/冷却/幂等门禁 |
| **MemoryStore + AuditStore** | SQLite 持久记忆和审计事件 |
| **SkillEngine + RuleEngine** | 内置技能编排与 memory(type=rule) 自动化 |

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
| **Voice Module** | `modules/voice/` | Provider ASR + TTS (Edge TTS) + 唤醒词 (Porcupine)，mock fallback |
| **Display Module** | `modules/display/` | SSD1306 OLED 128x64 表情/文本渲染，mock fallback |
| **Sensor Module** | `modules/sensor/` | HC-SR04 超声波 + IR 红外障碍物检测，mock fallback |
| **Mode System** | `modules/robot_service/state.py` | 5 种模式 (normal/safety/kid/debug/mute)，速度上限联动 |
| **Agent Boundary** | `modules/robot_service/agent.py` | Pydantic AI 工具和 LLM 不可用时的降级回复 |
| **Safety Flow** | `modules/robot_service/safety.py` | 运动/语音/急停等硬门禁 |
| **Memory API** | `modules/robot_service/storage.py` + `api.py` | 记忆 CRUD、搜索、导入导出 |
| **Web Console** | `modules/robot_service/api.py` | FastAPI + WebSocket，复用单文件 UI (port 8080) |

## Runtime Components

| 组件 | 位置 | 说明 |
|------|------|------|
| **Robot Service** | `modules/robot_service/service.py` | 主编排层，统一处理 invoke/chat/stop/status |
| **FastAPI API** | `modules/robot_service/api.py` | REST/WebSocket/API 兼容层 |
| **Pydantic AI Agent** | `modules/robot_service/agent.py` | typed tools、模型 provider、LLM 降级 |
| **Voice Session** | `modules/robot_service/voice_session.py` | 唤醒词后执行 ASR → Agent chat → TTS → 恢复监听 |
| **Adapters** | `modules/robot_service/adapters.py` | 把现有 Python 模块包装成统一调用接口 |
| **Safety** | `modules/robot_service/safety.py` | 参数 schema、模式、障碍物、急停、并发、冷却、幂等 |
| **Storage** | `modules/robot_service/storage.py` | SQLite memory/audit store |
| **Skills/Rules** | `modules/robot_service/skills.py`, `rules.py` | 内置技能和 memory-backed automation |

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
- `GET /api/metrics` — 指标兼容端点，当前可返回空列表
- `GET /api/sessions` — 会话列表
- `GET /api/sessions/:id/replay` — 会话回放兼容端点
- `GET /api/watchdog` — in-process 模块状态
- `GET /api/rules/status` — 规则引擎状态
- `POST /api/rules/evaluate` — 手动触发规则评估

### Running Tests

```bash
# Python module and Robot Service tests
cd modules && pytest -q

# Run single test file
cd modules && pytest tests/test_robot_service_safety.py -q

# Compile Robot Service
python -m compileall modules/robot_service
```

### Deployment

```bash
# Install on Raspberry Pi
chmod +x deploy/install.sh
./deploy/install.sh

# Manual start
python -m robot_service --mock

# systemd (after install.sh)
sudo systemctl start mcar
journalctl -u mcar -f
```

## Environment Setup

```bash
# 复制环境变量模板并填入 API keys
cp .ai_pet_env.example .ai_pet_env
# LLM 配置（任选 Pydantic AI 支持的 provider）:
#   GEMINI_API_KEY / GOOGLE_API_KEY — Google Gemini
#   OPENAI_API_KEY — OpenAI
#   ANTHROPIC_API_KEY — Anthropic
#   PROXY_API_KEY + LLM_PROVIDER=openai-compatible + LLM_MODEL=gpt-5.5 + LLM_BASE_URL
# 语音: PICOVOICE_ACCESS_KEY, VOICE_ASR_PROVIDER, DASHSCOPE_API_KEY, QWEN3_ASR_URL
# 可选: WEB_PORT, WEB_HOST, LLM_BASE_URL, LLM_HTTP_TRUST_ENV
```

## Development Notes

- 急停链路（STOP_EVENT）不得依赖模型推理，必须硬编码最高优先级
- 所有能力调用必须经过 `RobotService.invoke()`，不要绕过 `SafetyRouter`
- 记忆和审计写入 SQLite，测试需要用 `data_dir=tmp_path` 隔离
- 幂等策略: 运动/高风险动作推荐 `DEDUP_ONLY` + 短 TTL
- 并发控制: 运动类能力建议设 `max_in_flight: 1` + `mutex_group: "motion"` 防止冲突
- 新模块脚手架: `./scripts/new-module.sh <module_id> [description]` 自动生成模块代码和测试
- Voice 模块 recognize/synthesize 配置了 retry_policy（E_TIMEOUT + E_DEPENDENCY_NETWORK），synthesize 限制 max_in_flight:1 防音频重叠
- ASR provider 默认 `auto`: 阿里云 Fun-ASR → 阿里云 NLS → 本机 Qwen3-ASR → Whisper → Google STT
- 本机 Qwen3-ASR 推荐部署在 Mac，通过 `scripts/qwen3_asr_server.py` 提供 `/transcribe`
- Whisper ASR 通过 HTTP POST 到局域网服务（WHISPER_URL），使用 `urllib` 绕过系统代理（ProxyHandler({})）
- Button 模块通过 GPIO 中断检测按钮（BCM17, FALLING edge, 200ms 去抖）
- systemd 直接运行 `.venv/bin/python -m robot_service`
