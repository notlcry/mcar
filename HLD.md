
# 树莓派 Agent 交互机器人系统初步设计文档（HLD）

## 0. 设计原则

1. **能力即插件**：任何硬件/服务能力都以 Capability Module 形式接入，Agent 只看“能力声明”，不耦合实现。
2. **安全优先**：危险能力必须有“硬门禁”（代码级）、可急停、可降级；不能依赖 prompt 自觉。
3. **记忆可控**：结构化、可审计、可撤销；默认最小化注入模型上下文。
4. **故障隔离**：单模块崩溃不影响核心；核心崩溃不导致危险动作持续。
5. **可测试**：核心逻辑可在无硬件环境用 mock modules 回归。

---

## 1. 系统总体架构

### 1.1 逻辑组件

* **Orchestrator（编排核心）**

  * 负责：会话状态机、路由输入、调用 Agent、执行能力、写日志、更新记忆
* **Agent Runtime（LLM 适配与决策）**

  * 负责：将用户输入 + 上下文 + 能力清单 → 产出（文本回复 + tool/skill 调用计划）
  * 可替换：Gemini/其他模型
* **Capability Registry（能力注册表）**

  * 负责：加载/管理模块、汇总能力声明、提供能力发现接口
* **Capability Executor（能力执行器）**

  * 负责：按声明调用模块，做参数校验、速率限制、超时与幂等、结果标准化
* **Safety Policy Engine（安全策略引擎）**

  * 负责：对危险能力进行门禁（状态条件/权限/确认/冷却/阈值），可作为执行器的前置拦截器
* **Memory Service（记忆服务）**

  * 负责：结构化记忆的写入/检索/撤销/导入导出，注入策略
* **State Service（状态服务）**

  * 负责：统一状态视图（模式/健康/风险/最近动作），供 UI 与 Agent 使用
* **Audit & Telemetry（审计与遥测）**

  * 负责：结构化事件日志、指标、会话回放数据

### 1.2 物理部署（进程边界建议）

* `core`：Orchestrator + Registry + Executor + Policy + Memory + State（一个主进程）
* `modules/*`：能力模块（可同进程加载或独立进程 RPC；首期建议“独立进程优先”用于隔离）
* `ui`（可选）：Web 控制台/调试台

> 设计上支持两种形态：
>
> * **In-process 插件**（性能好，隔离弱）
> * **Out-of-process 模块服务**（隔离强，稍复杂）
>   首期建议把“危险硬件”模块独立进程化，其他可同进程。

---

## 2. 关键数据流

### 2.1 语音交互主链路

1. Audio In → ASR（云）→ `UserText`
2. Orchestrator 读取：Session Memory + 注入的 Long-term/Device Memory + State Snapshot + Capability List
3. Agent Runtime 调用模型 → 输出：

   * `assistant_text`（可选）
   * `action_plan`（0..N 个工具调用/技能调用/澄清问题）
4. Orchestrator 通过 Safety Policy Engine 逐条审批 action_plan
5. Executor 调用对应模块执行 → 返回结果
6. Orchestrator 汇总结果：

   * 生成最终回复（文本→TTS）
   * 写审计日志
   * 触发记忆写入（显式/隐式提议）
   * 更新 State（最近动作、错误等）

### 2.2 “停”/急停链路（最高优先级）

* 输入侧（语音/按钮/UI）触发 `STOP_EVENT`
* Orchestrator 立即：

  * 取消当前执行队列
  * 调用所有具备 `stop()` 或 `cancel()` 能力的模块
  * 设置全局 `safety_lock` 冷却窗口（例如 2 秒）
  * 记录审计事件（来源、时间、被中断任务）
* 注意：此链路不得依赖模型推理。

---

## 3. 能力扩展机制设计

### 3.1 能力模块接口（Module Contract）

每个模块必须实现：

* `manifest()`：返回模块元信息（id、版本、权限需求、健康检查端点等）
* `capabilities()`：返回能力声明列表（tools/skills）
* `invoke(capability_id, input, context)`：执行能力
* `health()`：返回模块健康状态（建议）
* 可选：

  * `cancel(invocation_id)`：中断执行
  * `stop()`：硬停止（危险模块强烈建议实现）

### 3.2 能力声明（Capability Spec）

统一为结构化 JSON（或等价结构），核心字段与需求一致，额外补充执行控制字段：

* `id`, `name`, `type`, `version`
* `inputs_schema`（JSON Schema 风格）
* `outputs_schema`
* `risk_level`: READ_ONLY | NORMAL | DANGEROUS
* `constraints`：

  * `timeout_ms`
  * `rate_limit`（qps/burst）
  * `idempotency`（是否支持幂等键）
  * `max_duration_ms`（适用于动作类）
* `required_state_predicates`：如 `obstacle=false`
* `permissions`：角色/模式/确认需求
* `observability`：必须记录哪些字段（脱敏规则）

### 3.3 Skill 形态

Skill 是能力单元的一种，但其实现可以是：

* **脚本型 Skill**：由多个 Tool 编排（顺序/条件/重试），由 Orchestrator 执行
* **模块内 Skill**：模块内部封装复杂逻辑，对外暴露一个 `invoke`

首期建议：**脚本型 Skill**优先，便于复用与调试；复杂硬件时可封进模块。

---

## 4. 记忆系统初步设计

### 4.1 存储模型

* **Session Store**：每会话事件流（对话轮次、调用、结果）——用于回放/调试
* **Memory Store**：结构化记忆条目（Long-term + Device）
* **Index**：

  * keyword 索引（字段/标签）
  * semantic 索引（向量或等价检索手段，具体实现可替换）

### 4.2 写入流程（两阶段）

* **显式写入**：

  1. 用户说“记住…”
  2. Orchestrator 生成 Memory Draft（结构化）
  3. 用户确认 → commit
* **隐式写入（提议）**：

  1. Orchestrator/Agent 产生“候选记忆”
  2. 以一句话询问：“我可以记住 X 吗？”
  3. 用户同意 → commit；不同意 → discard
* **撤销/删除**：必须可按 id/type/tag 删除，并记录审计。

### 4.3 注入策略（Context Injection Policy）

* 每次请求前，Memory Service 返回“注入包”：

  * 相关条目列表（按相关性排序）
  * 每条条目带 `privacy_level` 与 `allowed_in_context` 判定
* 注入限制：

  * 条数上限（例如 5 条）
  * 字段脱敏（例如不注入精确位置、API key、隐私内容）
  * 风险规则（危险能力执行时优先注入设备约束/安全规则）

---

## 5. 安全策略引擎（Policy Engine）初步设计

### 5.1 风险分级执行模型

* READ_ONLY：默认允许（仍审计）
* NORMAL：允许，但要通过参数边界与速率限制
* DANGEROUS：必须通过以下组合策略之一（可配置）：

  * `confirm_required`：用户确认
  * `role_required`：管理员/白名单
  * `state_gate`：状态条件满足（例如 obstacle=false）
  * `cooldown`：急停后冷却禁止

### 5.2 “硬门禁”职责

Policy Engine 对每一次 `invoke` 做：

* 参数校验（范围/类型/枚举）
* 状态门禁（required_state_predicates）
* 频率限制/冷却窗口
* 确认流程（生成待确认 action，进入 CONFIRM 状态）
* 幂等保护（避免重试导致重复危险动作）

---

## 6. Orchestrator 会话状态机（FSM）

### 6.1 状态定义

* `IDLE`：待命
* `LISTENING`：接收输入（语音/文本）
* `THINKING`：调用模型推理
* `PLANNING`：解析 action plan、可能补充 state/memory
* `CONFIRMING`：等待用户确认危险动作
* `EXECUTING`：执行能力调用序列
* `RESPONDING`：生成输出（TTS/文本）
* `ERROR`：错误处理与降级
* `STOPPED`：被急停中断后的短暂锁定/冷却

### 6.2 转移要点

* 任意状态收到 STOP_EVENT → `STOPPED`（优先级最高）
* `CONFIRMING` 收到“确认/取消”→ 回到 `EXECUTING` 或 `RESPONDING`
* 模型不可用 → `ERROR` → 降级策略（只读能力 + 提示）

---

## 7. 模型与工具调用协议（LLM Interface）

### 7.1 输入给模型的上下文构成

* system rules（安全条款、风格、能力使用原则）
* 当前模式（safety/kid/debug/mute…）
* 注入的记忆包（经隐私过滤）
* 当前状态快照（健康/风险/模式）
* 能力清单（名称、描述、参数 schema、风险级别）

### 7.2 模型输出约束

模型输出必须被解析为以下之一：

* `clarify_question`：需要澄清
* `assistant_text`：仅回复
* `action_plan`：工具调用列表（可含参数）
* `memory_proposal`：隐式记忆提议（由系统再询问用户是否写入）

> 设计要求：即便模型直接输出工具调用，也必须经过 Policy Engine 批准。

---

## 8. 观测、审计与回放设计

### 8.1 事件模型（Audit Event）

统一事件结构（示例字段）：

* `trace_id`（一次用户请求链路）
* `event_type`：USER_INPUT / LLM_CALL / PLAN / INVOKE / RESULT / MEMORY_WRITE / STOP / ERROR
* `timestamp`
* `payload`（结构化，支持脱敏）
* `severity`：INFO/WARN/ERROR

### 8.2 回放能力（Replay）

* 保存每次会话的事件流（可选保存音频引用）
* 支持“用同样输入 + mock 能力模块”重跑一次以复现问题

---

## 9. 配置与管理面（Control Plane）

### 9.1 配置项

* 模型提供商与 key（密钥不写日志）
* 模式策略（危险能力是否默认确认）
* 记忆注入上限与隐私策略
* 模块白名单/权限策略
* 日志级别与保留策略

### 9.2 管理操作

* 启用/禁用模块
* 列出能力清单
* 查看/删除记忆
* 导出审计日志与记忆备份

---

## 10. 可测试性设计

### 10.1 Mock Modules

* 提供一组 mock 能力模块（例如 fake_led、fake_sensor、fake_motion）
* 可在 CI 中覆盖：

  * 危险能力必须确认
  * 急停优先级
  * 模型不可用降级
  * 记忆写入/撤销流程

### 10.2 策略单元测试

* Policy Engine 的边界条件（参数范围、冷却、状态门禁）
* 幂等与防重复执行

---

## 11. 初期里程碑（实现规划，不是实现细节）

### M1：最小可跑通闭环

* 输入：语音/文本（二选一可先）
* Agent：模型调用 + 工具调用协议跑通
* 模块：至少 3 个能力（其中 1 个为硬件或硬件模拟）
* 记忆：显式写入 + 查询 + 删除
* 安全：STOP_EVENT + 危险能力确认
* 审计：事件日志链路

### M2：扩展与稳定

* 模块隔离完善（危险模块 out-of-process）
* 设备记忆联动（校准/约束进入 policy）
* 隐式记忆提议
* UI/控制台（可选）

---

## 12. 开放问题（需要你拍板的“形态选择”）

你之前提“像 OpenClaw，但另一种形式”。从设计落地角度，需要你定一个主形态（会影响 UI 与资源管理方式，但不影响核心架构）：

1. **Robot-first**：语音优先，UI 仅做调试与管理
2. **Workspace-first**：有一个“工作台”管理技能/记忆/模块，机器人是执行节点
3. **Skill-first**：能力/技能生态优先，机器人只是一个能力宿主

你不选也行：我默认按 **Robot-first** 推进（最贴近“交互机器人”）。

---

如果你希望我把这份 HLD 再往下推进到“下一层设计”（Still not code）我可以补两份非常关键的附录（你选一个先做）：

1. **Capability Spec 标准（JSON Schema 版）+ 错误码规范 + 幂等策略**
2. **Memory Spec（字段、类型、注入策略、隐私规则）+ 记忆治理流程图**
