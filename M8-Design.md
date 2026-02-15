# M8 设计文档：剩余功能补全 + 体验闭环

## 0. 背景与现状

### 已完成里程碑

| 里程碑 | 内容 | 测试 |
|--------|------|------|
| **M0** | IPC 通信、ModuleBridge、MockModule、CapabilityRegistry/Executor、PolicyEngine、MemoryService/Store、StateService、AuditLogger | — |
| **M1** | AgentRuntime (Gemini)、SessionController FSM、ActionDispatcher、PromptBuilder、ToolAdapter（能力→Agent 工具）| — |
| **M2** | Voice/Display/Sensor 模块、Mode System、VoiceLoop、CONFIRMING 确认流、隐式记忆提议、API 降级、Web Console | — |
| **M3** | SkillEngine（多工具组合）、内置技能 (self_check/night_mode/patrol)、记忆删除/清除工具、记忆导出/导入、AuditStore (SQLite)、HealthMonitor | — |
| **M4** | SessionRecorder (会话回放)、CleanupScheduler (TTL清理+审计轮转)、ModuleWatchdog (进程守护)、Deploy 配置 | — |
| **M5** | 并发控制 (max_in_flight + mutex_group)、审计脱敏 (Redactor)、RuleEngine (自动化规则)、上下文注入增强 | — |
| **M6** | IPC 重试策略、PerformanceTracker (p50/p95/p99)、IncidentRecorder、模块脚手架生成器、Metrics API、审计 duration_ms | — |
| **M7** | IncidentRecorder TTL 修复、AgentRuntime 接入 IncidentRecorder、dispatch 延迟追踪、隐私过滤测试、Voice retry+concurrency、记忆提议闭环、ContextBuilder 统一 | ✅ |
| **M8** | Motion 模块测试、关键词语义检索 (searchRelevant)、物理急停按钮模块、会话摘要压缩、E2E 集成测试、部署文档+测试指南 | ✅ |
| **合计** | 272 TS + 103 Python = **375 个测试全部通过** | ✅ |

### 需求覆盖率

对照 Req.md / HLD.md / Spec.md 做逐项打勾：

| 需求章节 | 条目 | 状态 |
|----------|------|------|
| 4.1.1 语音交互 | 唤醒词→ASR→Agent→TTS 循环 | ✅ 已实现 |
| 4.1.1 停止词优先级 | 硬编码最高优先级，不经模型 | ✅ 已实现 |
| 4.1.2 文本交互 | CLI + Web /api/chat | ✅ 已实现 |
| 4.1.3 Web 控制台 | Express + WebSocket，REST API + 单文件 UI | ✅ 已实现 |
| 4.2.1 意图理解/规划 | Gemini Agent + tool calling | ✅ 已实现 |
| 4.2.2 工具/技能调用 | CapabilityRegistry + SkillEngine | ✅ 已实现 |
| 4.2.3 反馈与对话 | Agent 自然语言回复 + 确认流 | ✅ 已实现 |
| 4.3.1 能力单元模型 | CapabilitySpec JSON Schema（全字段） | ✅ 已实现 |
| 4.3.2 扩展模块 | Python 模块 + IPC + 脚手架生成器 | ✅ 已实现 |
| 4.3.3 能力组合 | SkillEngine 脚本型 Skill | ✅ 已实现 |
| 4.4.1 会话记忆 | Agent messages (pi-agent-core 内置) | ✅ 已实现 |
| 4.4.1 长期记忆 | MemoryStore (SQLite) | ✅ 已实现 |
| 4.4.1 设备记忆 | type=device 条目 | ✅ 已实现 |
| 4.4.2 记忆条目模型 | 全字段（id/type/content/source/confidence/privacy/tags/links/ttl） | ✅ 已实现 |
| 4.4.3 显式写入 | "记住 X" → 确认 → 写入 | ✅ 已实现 |
| 4.4.3 隐式写入(提议) | tool.memory.propose → 确认 → 写入 (M7 闭环) | ✅ 已实现 |
| 4.4.4 关键词检索 | LIKE 搜索 | ✅ 已实现 |
| 4.4.4 语义检索 | 关键词标签增强检索 (searchRelevant) | ✅ 已实现 |
| 4.4.5 记忆管理 | 查询/删除/清空/导出/导入 | ✅ 已实现 |
| 4.5 状态视图 | StateService (mode/health/obstacle/battery/safetyLock/lastAction) | ✅ 已实现 |
| 6.1 风险分级 | READ_ONLY/NORMAL/DANGEROUS + PolicyEngine | ✅ 已实现 |
| 6.2 急停-语音 | 停止词硬编码 → StopHandler → broadcastStop | ✅ 已实现 |
| 6.2 急停-物理按钮 | GPIO 物理按钮 (modules/button/) | ✅ 已实现 |
| 6.3 API 降级 | DegradationHandler (3次失败→离线模式→基本命令解析) | ✅ 已实现 |
| 6.3 模块故障隔离 | ModuleWatchdog (崩溃→指数退避重启→永久失败标记) | ✅ 已实现 |
| 6.3 幂等/防重复 | DEDUP_ONLY + IDEMPOTENT 策略 | ✅ 已实现 |
| 6.4 审计可追溯 | AuditLogger + AuditStore + 导出 | ✅ 已实现 |
| 6.4 回放 | SessionRecorder + /api/sessions/:id/replay | ✅ 已实现 |
| 7 性能可观测 | PerformanceTracker + /api/metrics | ✅ 已实现 |
| 7 自动恢复 | systemd service + watchdog | ✅ 已实现 |
| 8.1 会话摘要/压缩 | SessionSummarizer (LLM + 本地兜底) | ✅ 已实现 |
| 8.2 备份/恢复 | 记忆导出/导入 + 审计导出 | ✅ 已实现 |

### 剩余缺口汇总

按优先级排列：

| # | 缺口 | 影响 | 优先级 |
|---|------|------|--------|
| G1 | Motion 模块无 Python 测试 | 5 个能力完全无覆盖，安全关键路径（运动）无保障 | **P0** |
| G2 | 语义检索 (Req 4.4.4) | "语义相关检索"是需求 MUST，当前仅 LIKE 搜索 | **P1** |
| G3 | 物理急停按钮 (Req 6.2) | 安全双通道（语音+物理）建议，树莓派部署必备 | **P1** |
| G4 | 会话摘要/压缩 | 长对话 token 膨胀，LLM 成本高 | **P2** |
| G5 | 情感引擎 (legacy 功能) | 提升交互体验，非功能需求 | **P3** |
| G6 | E2E 集成测试 | 端到端链路验证缺失 | **P2** |

---

## 1. 架构总览

M8 新增/修改的组件在现有架构中的位置：

```
┌──────────────────────────────────────────────────────────┐
│                     Orchestrator                          │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────────┐  │
│  │VoiceLoop    │ │ActionDispatch│ │SessionController  │  │
│  │             │ │  +PerfTracker│ │  FSM              │  │
│  │             │ │  +MemService │ │                   │  │
│  └─────────────┘ └──────────────┘ └───────────────────┘  │
│  ┌──────────────────────┐  ┌────────────────────────────┐│
│  │ContextBuilder        │  │SessionSummarizer [NEW-G4]  ││
│  │  +watchdog           │  │  LLM-based summary         ││
│  └──────────────────────┘  └────────────────────────────┘│
├──────────────────────────────────────────────────────────┤
│                     Agent Runtime                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │
│  │AgentRuntime  │ │PromptBuilder │ │ToolAdapter       │  │
│  │+incidentRec  │ │ via CtxBuild │ │+incidentRecorder │  │
│  └──────────────┘ └──────────────┘ └──────────────────┘  │
├──────────────────────────────────────────────────────────┤
│                   Capability Layer                         │
│  ┌──────────┐ ┌────────────┐ ┌────────────┐ ┌─────────┐ │
│  │Registry  │ │Executor    │ │PolicyEngine│ │SkillEng │ │
│  └──────────┘ └────────────┘ └────────────┘ └─────────┘ │
├──────────────────────────────────────────────────────────┤
│                    Memory Layer                            │
│  ┌──────────────────┐  ┌───────────────────────────────┐ │
│  │MemoryService     │  │EmbeddingIndex [NEW-G2]        │ │
│  │  +SemanticSearch  │  │  SQLite FTS5 + 轻量嵌入       │ │
│  └──────────────────┘  └───────────────────────────────┘ │
├──────────────────────────────────────────────────────────┤
│              Python Modules (IPC)                          │
│  ┌──────┐┌───────┐┌───────┐┌──────┐┌──────┐┌─────────┐ │
│  │mock  ││voice  ││display││motion││sensor││button   │ │
│  │      ││       ││       ││      ││      ││[NEW-G3] │ │
│  └──────┘└───────┘└───────┘└──────┘└──────┘└─────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Phase 1: Motion 模块测试补全 [P0, S]

### 问题

`modules/motion/` 有完整实现（5 个能力、mock 模式、PCA9685 驱动），但 `modules/tests/` 中无 `test_motion_module.py`。运动是安全关键路径，必须有测试覆盖。

### 设计

参照 `test_voice_module.py` 和 `test_sensor_module.py` 的模式：
- fixture 创建 mock 模式的 MotionDriver 和 MotionModule
- 测试 manifest、capabilities、invoke 每个能力、stop、error cases

### 实现

**新增文件**: `modules/tests/test_motion_module.py`

```python
"""Tests for the Motion module capabilities (mock mode)."""
from motion.driver import MotionDriver
from motion.module import MotionModule

class TestMotionModuleManifest:
    def test_manifest(self, motion_module):
        manifest = motion_module.manifest()
        assert manifest["module_id"] == "motion"
        assert "tool.motion.forward" in manifest["capabilities"]
        # ... 5 capabilities

    def test_capabilities(self, motion_module):
        caps = motion_module.capabilities()
        assert len(caps) == 5

    def test_capabilities_have_mutex_group(self, motion_module):
        caps = motion_module.capabilities()
        for cap in caps:
            if cap["capability_id"] != "tool.motion.stop":
                assert cap["constraints"]["concurrency"]["mutex_group"] == "motion"

class TestMotionDriverMovement:
    async def test_forward_mock(self, motion_driver):
        result = await motion_driver.forward(speed=30, duration_ms=500)
        assert result["ok"] is True

    async def test_backward_mock(self, motion_driver):
        result = await motion_driver.backward(speed=30, duration_ms=500)
        assert result["ok"] is True

    async def test_turn_left_mock(self, motion_driver):
        result = await motion_driver.turn_left(speed=30, duration_ms=500)
        assert result["ok"] is True

    async def test_turn_right_mock(self, motion_driver):
        result = await motion_driver.turn_right(speed=30, duration_ms=500)
        assert result["ok"] is True

class TestMotionModuleInvoke:
    async def test_invoke_forward(self, motion_module):
        result = await motion_module.invoke("tool.motion.forward", {"speed": 30, "duration_ms": 500}, {})
        assert result["ok"] is True

    async def test_invoke_stop(self, motion_module):
        result = await motion_module.invoke("tool.motion.stop", {}, {})
        assert result["ok"] is True

    async def test_invoke_unknown(self, motion_module):
        # Should raise ValueError
        ...

class TestMotionDriverEmergencyStop:
    async def test_stop(self, motion_driver):
        await motion_driver.stop()
        # verify motors stopped

class TestMotionCapabilitiesSpec:
    def test_forward_has_obstacle_predicate(self, motion_module):
        caps = motion_module.capabilities()
        fwd = next(c for c in caps if c["capability_id"] == "tool.motion.forward")
        preds = fwd["required_state_predicates"]
        assert any(p["key"] == "obstacle" for p in preds)

    def test_all_movement_dedup_only(self, motion_module):
        caps = motion_module.capabilities()
        for cap in caps:
            if cap["capability_id"] != "tool.motion.stop":
                assert cap["idempotency"]["mode"] == "DEDUP_ONLY"
```

**预计新增**: ~15 个测试

---

## 3. Phase 2: 语义检索 [P1, M]

### 问题

Req.md 4.4.4 要求"语义相关检索"，当前 MemoryStore 仅支持 SQL `LIKE` 关键词搜索。对于"用户问运动相关问题时，自动检索出运动限制记忆"的场景，关键词匹配不够。

### 方案评估

| 方案 | 优势 | 劣势 | 适合 |
|------|------|------|------|
| A: 外部向量数据库 (ChromaDB) | 语义质量好 | 依赖额外进程，Pi 资源紧张 | ❌ |
| B: Gemini Embedding API + SQLite | 质量好，无额外进程 | 依赖网络，每次查询需 API 调用 | ⚠️ |
| C: SQLite FTS5 全文索引 | 零依赖，速度快 | 中文分词需 jieba，非真正语义 | ⚠️ |
| **D: 关键词抽取 + 标签匹配** | **零依赖，足够实用** | **非向量语义** | ✅ |

### 选择方案 D：关键词标签增强检索

**理由**：
1. 树莓派资源有限，不宜引入重型向量数据库
2. 记忆条目数量有限（通常 <500 条），不需要向量索引
3. 利用已有的 `tags` 字段 + 能力关联 `links`，可实现"相关性"检索
4. 预留接口，未来可升级到 Embedding 方案

### 设计

在 MemoryStore 层面增加两个增强：

1. **写入时自动打标签**：从 summary + content 抽取关键词作为 tags
2. **检索时相关性排序**：按 tags 交集大小排序

```
MemoryService
  └── searchRelevant(query: string, types?, limit?): MemoryEntry[]
        ├── 从 query 抽取关键词 (splitKeywords)
        ├── 按 tags 交集匹配 + summary LIKE 回退
        └── 按匹配得分排序，返回 top N
```

### 实现

**修改文件**: `core/src/memory/memory-store.ts`

```typescript
/**
 * Search with relevance scoring.
 * Matches tags intersection + keyword fallback.
 */
searchRelevant(queryKeywords: string[], options?: MemorySearchOptions): MemoryEntry[] {
  // 1. 获取候选条目（按类型 + 隐私过滤）
  const candidates = this.search({ ...options, limit: 200 });
  // 2. 对每条计算相关性得分
  //    score = tags交集数 * 2 + summary关键词命中数
  // 3. 按得分降序排序
  // 4. 返回 top limit 条
}
```

**新增文件**: `core/src/memory/keyword-extractor.ts`

```typescript
/**
 * 从文本抽取关键词（轻量方案）。
 * - 中文：按字/词切分（简单正则，无 jieba 依赖）
 * - 英文：按空格切分，去停用词
 * - 返回去重关键词数组
 */
export function extractKeywords(text: string): string[] { ... }
```

**修改文件**: `core/src/memory/memory-service.ts`

```typescript
/**
 * 语义相关检索（关键词标签匹配）。
 */
searchRelevant(query: string, types?: MemoryType[]): MemoryEntry[] {
  const keywords = extractKeywords(query);
  return this.store.searchRelevant(keywords, {
    types,
    includePrivate: false,
    limit: this.maxInjectionCount,
  });
}
```

**修改文件**: `core/src/memory/memory-service.ts` → `getInjectionContext`

```typescript
// 现有逻辑之后，追加相关性检索结果
if (entries.length < this.maxInjectionCount && relatedCapabilityIds?.length) {
  const relevant = this.store.searchRelevant(
    relatedCapabilityIds,  // 使用能力 ID 作为关键词
    { includePrivate: false, limit: this.maxInjectionCount - entries.length }
  );
  entries.push(...relevant);
}
```

**新增测试**: `core/tests/unit/keyword-extractor.test.ts`

1. 中文文本抽取关键词
2. 英文文本抽取关键词
3. 混合文本
4. 空文本返回空数组

**新增测试**: `core/tests/unit/memory-service.test.ts` (追加)

1. searchRelevant 按标签匹配返回相关记忆
2. searchRelevant 不返回 private 记忆
3. 无匹配时返回空数组

**预计新增**: ~8 个测试

---

## 4. Phase 3: 物理急停按钮 [P1, M]

### 问题

Req.md 6.2："强烈建议语音 + 物理双通道"。当前只有语音停止词和 Web API，无物理按钮。树莓派部署时，物理按钮是安全底线。

### 设计

创建独立的 `button` Python 模块，通过 IPC 发送 stop 事件。

```
GPIO Pin (BCM17, pull-up)
  │ FALLING edge
  ▼
ButtonModule
  │ debounce 200ms
  ▼
IPC event: { event_type: "emergency_stop", source: "button", data: {} }
  │
  ▼
ModuleBridge → Orchestrator → StopHandler.triggerStop("button")
```

**关键设计决策**：

1. **独立模块而非核心内嵌**：按"能力即插件"原则，GPIO 按钮是一个模块
2. **事件驱动而非轮询**：GPIO 中断 + 回调，无 CPU 占用
3. **能力声明最小化**：仅 1 个 READ_ONLY 能力（`tool.button.status`）+ stop 事件
4. **Mock 模式**：无 GPIO 时自动降级为 mock（不报错）

### 实现

**新增目录**: `modules/button/`

**新增文件**: `modules/button/module.py`

```python
class ButtonModule(ModuleBase):
    """Physical emergency stop button module.

    Monitors GPIO pin for button press, emits emergency_stop event.
    Falls back to mock mode when RPi.GPIO is not available.
    """

    def __init__(self):
        super().__init__("button")
        self._driver = ButtonDriver(
            gpio_pin=int(os.environ.get("BUTTON_GPIO_PIN", "17")),
            debounce_ms=int(os.environ.get("BUTTON_DEBOUNCE_MS", "200")),
        )

    def manifest(self):
        return {
            "module_id": "button",
            "module_version": "1.0.0",
            "description": "Physical emergency stop button (GPIO)",
            "capabilities": ["tool.button.status"],
            "permissions_required": ["gpio"],
        }

    def capabilities(self):
        return load_capabilities_from_json("button/capabilities.json")

    async def invoke(self, capability_id, input_data, context):
        if capability_id == "tool.button.status":
            return {"ok": True, "pressed": self._driver.is_pressed()}
        raise ValueError(f"Unknown capability: {capability_id}")

    def health(self):
        return {"status": "ok", "gpio_available": self._driver.gpio_available}

    def stop(self):
        self._driver.cleanup()
```

**新增文件**: `modules/button/driver.py`

```python
class ButtonDriver:
    """GPIO button driver with interrupt-based detection."""

    def __init__(self, gpio_pin: int = 17, debounce_ms: int = 200):
        self.gpio_pin = gpio_pin
        self.debounce_ms = debounce_ms
        self.gpio_available = False
        self._pressed = False
        self._callback = None
        self._setup_gpio()

    def _setup_gpio(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(
                self.gpio_pin, GPIO.FALLING,
                callback=self._on_press,
                bouncetime=self.debounce_ms
            )
            self.gpio_available = True
        except (ImportError, RuntimeError):
            # Not on RPi or no GPIO access → mock mode
            self.gpio_available = False

    def _on_press(self, channel):
        self._pressed = True
        if self._callback:
            self._callback()

    def on_press(self, callback):
        """Register callback for button press."""
        self._callback = callback

    def is_pressed(self) -> bool:
        pressed = self._pressed
        self._pressed = False  # Reset after read
        return pressed

    def cleanup(self):
        if self.gpio_available:
            import RPi.GPIO as GPIO
            GPIO.cleanup(self.gpio_pin)
```

**新增文件**: `modules/button/capabilities.json`

```json
[{
  "capability_id": "tool.button.status",
  "name": "Button Status",
  "type": "tool",
  "version": "1.0.0",
  "description": "Check if the physical emergency stop button was pressed.",
  "risk_level": "READ_ONLY",
  "inputs_schema": { "type": "object", "properties": {}, "additionalProperties": false },
  "outputs_schema": {
    "type": "object",
    "properties": {
      "ok": { "type": "boolean" },
      "pressed": { "type": "boolean" }
    },
    "required": ["ok"]
  },
  "constraints": { "timeout_ms": 1000 },
  "required_state_predicates": [],
  "permissions": { "roles_allowed": ["user", "admin"], "confirm_required": false },
  "idempotency": { "mode": "NONE", "key_fields": [], "ttl_ms": 0 },
  "observability": { "audit_level": "MINIMAL", "log_inputs": false, "log_outputs": true, "redaction": [] }
}]
```

**修改文件**: `core/src/index.ts`

- moduleNames 列表加入 `"button"`

**修改文件**: `core/src/safety/stop-handler.ts`

- `triggerStop` source 类型扩展为 `"voice" | "web" | "system" | "button"`

**修改文件**: 模块事件处理

- ModuleBridge 收到 `emergency_stop` 事件时调用 `stopHandler.triggerStop("button")`

**新增测试**: `modules/tests/test_button_module.py`

1. manifest 包含正确的 module_id 和 capabilities
2. mock 模式下 is_pressed() 默认返回 false
3. invoke tool.button.status 返回 ok
4. cleanup 不报错

**预计新增**: ~6 个测试

---

## 5. Phase 4: 会话摘要 [P2, M]

### 问题

长对话 token 膨胀导致：
1. LLM API 成本增长
2. 上下文窗口满后丢失早期信息
3. 无"这次聊了什么"的摘要留存

Legacy 代码有简单的关键词抽取 + 轮次统计摘要。

### 设计

**方案**：LLM 摘要 + 本地关键词兜底

```
AgentRuntime
  │ messages.length > threshold (20轮)
  ▼
SessionSummarizer
  ├── 尝试 LLM 摘要（Gemini API）
  │     输入：最早 N 条 message
  │     输出：1-2 句摘要文本
  │     成功 → 替换早期 messages 为 [system: "之前的对话摘要: ..."]
  │
  └── 失败（API 不可用） → 本地关键词摘要兜底
        提取关键词 + 统计轮次
        "之前讨论了 X、Y、Z，共 15 轮对话"
```

**关键设计决策**：

1. **触发时机**：每次 `prompt()` 前检查，非阻塞
2. **压缩策略**：保留最近 10 轮完整对话 + 压缩更早的为摘要
3. **摘要存储**：作为 system message 注入 Agent，不持久化（会话级）
4. **可配置阈值**：`summarize_after_turns: 20`（默认）

### 实现

**新增文件**: `core/src/agent/session-summarizer.ts`

```typescript
export interface SummarizerConfig {
  readonly summarizeAfterTurns: number;  // default 20
  readonly keepRecentTurns: number;       // default 10
}

export class SessionSummarizer {
  constructor(
    private readonly config: SummarizerConfig,
    private readonly model: Model<any>,
    private readonly apiKey?: string
  ) {}

  /**
   * Check if messages need summarization.
   */
  needsSummarization(messageCount: number): boolean {
    return messageCount > this.config.summarizeAfterTurns;
  }

  /**
   * Summarize early messages and return compressed message list.
   * Keeps recent N turns intact, summarizes the rest.
   */
  async summarize(messages: Message[]): Promise<Message[]> {
    const keepCount = this.config.keepRecentTurns * 2; // user + assistant pairs
    if (messages.length <= keepCount) return messages;

    const toSummarize = messages.slice(0, messages.length - keepCount);
    const toKeep = messages.slice(messages.length - keepCount);

    try {
      const summaryText = await this.llmSummarize(toSummarize);
      const summaryMessage = {
        role: "system",
        content: `Previous conversation summary: ${summaryText}`,
      };
      return [summaryMessage, ...toKeep];
    } catch {
      // Fallback: keyword extraction
      const summaryText = this.localSummarize(toSummarize);
      const summaryMessage = {
        role: "system",
        content: `Previous conversation summary: ${summaryText}`,
      };
      return [summaryMessage, ...toKeep];
    }
  }

  private async llmSummarize(messages: Message[]): Promise<string> {
    // Call Gemini to summarize the conversation
    // Prompt: "Summarize this conversation in 1-2 sentences in the same language..."
  }

  private localSummarize(messages: Message[]): string {
    // Extract keywords from messages, count turns
    // Return: "之前讨论了 X, Y, Z，共 N 轮对话"
  }
}
```

**修改文件**: `core/src/agent/agent-runtime.ts`

```typescript
// 在 prompt() 方法中，调用前检查是否需要摘要
async prompt(text: string): Promise<void> {
  this.agent.setSystemPrompt(this.promptBuilder.build());
  const tools = this.buildTools();
  this.agent.setTools(tools);

  // 会话摘要压缩
  if (this.summarizer?.needsSummarization(this.agent.state.messages.length)) {
    const compressed = await this.summarizer.summarize(this.agent.state.messages);
    this.agent.setMessages(compressed);
  }

  await this.agent.prompt(text);
}
```

**新增测试**: `core/tests/unit/session-summarizer.test.ts`

1. 短会话不触发摘要 (< threshold)
2. 长会话触发摘要，保留最近 N 轮
3. LLM 失败时使用本地兜底
4. 摘要后消息数减少
5. 摘要内容作为 system message 存在

**预计新增**: ~6 个测试

---

## 6. Phase 5: E2E 集成测试 [P2, M]

### 问题

当前测试均为单元测试和小范围集成测试。缺少端到端链路验证：
- 用户输入 → FSM 状态转换 → Agent → 工具执行 → 响应
- 危险操作确认流
- 急停中断恢复

### 设计

使用 vitest + mock 模块，构建端到端测试：

```
Test Setup:
  - 真实 SessionController + ActionDispatcher + PolicyEngine
  - Mock AgentRuntime (模拟 LLM 返回)
  - Mock ModuleBridge (无 IPC)
  - 真实 MemoryService (in-memory SQLite)
  - 真实 AuditLogger
```

### 实现

**新增文件**: `core/tests/integration/e2e-flow.test.ts`

```typescript
describe("E2E Flow", () => {
  // Setup: wire all real services with mock agent/bridge

  it("should complete text input → response cycle", async () => {
    // dispatcher.dispatch("你好") → 响应文本
    // FSM: IDLE → THINKING → RESPONDING → IDLE
  });

  it("should handle emergency stop during execution", async () => {
    // dispatch 一个长操作
    // 发送 "停"
    // 验证 FSM → STOPPED，safety lock 激活
  });

  it("should reject dangerous action without confirmation", async () => {
    // 配置一个 DANGEROUS 能力
    // dispatch → PolicyEngine 返回 confirm
    // 验证需要确认
  });

  it("should save memory after proposal confirmation", async () => {
    // requestMemoryConfirmation → dispatch("是")
    // 验证 MemoryService 有新条目
  });

  it("should recover from API degradation", async () => {
    // 模拟 3 次 API 失败 → degraded 模式
    // dispatch 基本命令 → 本地解析成功
    // 模拟 API 恢复 → 退出 degraded
  });
});
```

**预计新增**: ~8 个测试

---

## 7. Phase 6: 全量测试 + 文档更新

- 运行 `npx vitest run` + `pytest modules/tests/ -v`
- 预期：298 + ~43 = **~341 个测试**
- 更新 CLAUDE.md 添加 M8 组件说明

---

## 8. 依赖关系与执行顺序

```
Phase 1 (Motion 测试)        ─── 独立 ──┐
Phase 2 (语义检索)           ─── 独立 ──┤
Phase 3 (物理按钮)           ─── 独立 ──┤──→ Phase 6 (全量测试)
Phase 4 (会话摘要)           ─── 独立 ──┤
Phase 5 (E2E 测试)           ── 依赖 1-4 ┘
```

Phase 1-4 可完全并行。Phase 5 建议在 1-4 完成后执行，以覆盖新增组件。

---

## 9. 工作量估计

| Phase | 新增/修改文件数 | 新增测试 | 规模 |
|-------|-----------------|----------|------|
| P1: Motion 测试 | 1 新增 | ~15 | S |
| P2: 语义检索 | 2 新增 + 2 修改 | ~8 | M |
| P3: 物理按钮 | 4 新增 + 2 修改 | ~6 | M |
| P4: 会话摘要 | 1 新增 + 1 修改 | ~6 | M |
| P5: E2E 测试 | 1 新增 | ~8 | M |
| P6: 测试 + 文档 | 1 修改 | 0 | S |
| **合计** | ~9 新增 + ~5 修改 | ~43 | — |

---

## 10. 不在 M8 范围内（P3 后续）

以下功能在需求文档中为"建议"或"可选"，不阻塞当前目标：

| 功能 | 理由 |
|------|------|
| **情感引擎** | Legacy 功能，提升体验但非 MUST；可作为 M9 独立迭代 |
| **个性化管理** | 同上，Legacy 有 PersonalityManager 可参考 |
| **离线 ASR (Vosk)** | Legacy 有实现，当前 Cloud ASR 已足够；离线 ASR 质量较差 |
| **多设备同步** | Req.md 明确标注"可后续" |
| **技能市场** | Req.md 明确标注"安全风险高，可后续" |
| **向量嵌入升级** | Phase 2 预留接口，未来可替换为 Embedding API |

---

## 11. 验收清单

### M8 完成标准

- [x] Motion 模块有 ≥15 个 Python 测试，覆盖所有 5 个能力 + stop + manifest
- [x] `searchRelevant()` 可按标签/关键词匹配返回相关记忆，有测试
- [x] `modules/button/` 存在且可在 mock 模式运行，有测试
- [x] 长会话自动摘要压缩，保留最近 N 轮，有测试
- [x] E2E 测试覆盖：正常对话、急停、危险确认、记忆提议、API 降级
- [x] 全量 375 测试通过（272 TS + 103 Python），无回归
- [x] CLAUDE.md 更新
- [x] 部署文档 (docs/DEPLOY.md) + 手工测试指南 (docs/TESTING.md)

### 需求覆盖率目标

M8 完成后，Req.md 所有 **MUST** 级别需求全部覆盖：
- ✅ 语义检索 (Req 4.4.4) — 关键词标签增强实现
- ✅ 物理急停 (Req 6.2) — GPIO 按钮模块
- ✅ 会话摘要 (Req 8) — LLM + 本地兜底

唯一剩余的"建议/可选"项为情感引擎、个性化、离线 ASR 等 P3 功能。
