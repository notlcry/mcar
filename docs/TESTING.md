# mcar 手工测试指南

真机部署后的功能验证测试矩阵。所有 curl 命令假设服务运行在 `localhost:8080`。

> 提示: 所有 JSON 输出可加 `| python3 -m json.tool` 格式化。

---

## T1. 基础启动验证

### T1.1 服务启动

```bash
sudo systemctl start mcar
# 或
cd core && node dist/index.js
```

**预期**: 控制台/日志显示以下关键行：
- `Orchestrator started`
- 6 个模块注册: mock, voice, display, motion, sensor, button
- `Web server listening on 0.0.0.0:8080`

### T1.2 模块注册检查

```bash
curl -s http://localhost:8080/api/modules | python3 -m json.tool
```

**预期**: 返回 6 个模块，包含 `module_id`、`capabilities`、`enabled` 等字段。

### T1.3 系统状态

```bash
curl -s http://localhost:8080/api/status | python3 -m json.tool
```

**预期**: 返回包含 `mode`, `health`, `risk_level`, `recent_actions` 的 JSON。

| 测试项 | 预期结果 | 通过 | 备注 |
|--------|---------|------|------|
| T1.1 服务启动 | 无报错，6 模块注册 | [ ] | |
| T1.2 模块列表 | 6 个模块，均有状态 | [ ] | |
| T1.3 系统状态 | JSON 包含 mode/health | [ ] | |

---

## T2. 文本对话

### T2.1 基本对话

```bash
curl -s -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "你好，你是谁？"}' | python3 -m json.tool
```

**预期**: 返回包含 `response` 字段的 JSON，Agent 有意义的回复。

### T2.2 能力列表查询

```bash
curl -s http://localhost:8080/api/capabilities | python3 -m json.tool
```

**预期**: 列出所有能力（echo, timer, status, forward, backward, turn_left, turn_right, stop, ultrasonic, infrared, recognize, synthesize, show_expression, show_text, clear, button.status 等）。

### T2.3 Agent 调用能力

```bash
curl -s -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "测试一下 echo 功能，发送 hello"}' | python3 -m json.tool
```

**预期**: Agent 应调用 `tool.mock.echo`，回复中包含 echo 结果。

| 测试项 | 预期结果 | 通过 | 备注 |
|--------|---------|------|------|
| T2.1 基本对话 | 有意义的回复 | [ ] | |
| T2.2 能力列表 | 列出所有模块能力 | [ ] | |
| T2.3 Agent 调用 | 成功调用 echo | [ ] | |

---

## T3. Web 控制台 API

### T3.1 REST API

逐个测试核心端点：

```bash
# 状态
curl -s http://localhost:8080/api/status | python3 -m json.tool

# 能力
curl -s http://localhost:8080/api/capabilities | python3 -m json.tool

# 模块列表
curl -s http://localhost:8080/api/modules | python3 -m json.tool

# 健康检查
curl -s http://localhost:8080/api/health | python3 -m json.tool

# 审计日志
curl -s http://localhost:8080/api/audit | python3 -m json.tool

# 指标
curl -s http://localhost:8080/api/metrics | python3 -m json.tool

# 模块进程状态
curl -s http://localhost:8080/api/watchdog | python3 -m json.tool

# 技能列表
curl -s http://localhost:8080/api/skills | python3 -m json.tool

# 会话列表
curl -s http://localhost:8080/api/sessions | python3 -m json.tool

# 规则引擎状态
curl -s http://localhost:8080/api/rules/status | python3 -m json.tool
```

### T3.2 直接调用能力

```bash
# 调用 mock echo
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.mock.echo", "input": {"text": "hello from api"}}' \
  | python3 -m json.tool
```

**预期**: 返回 `{"success": true, "result": {"echo": "hello from api", ...}}`

### T3.3 WebSocket 连接

```bash
# 需要 wscat (npm install -g wscat) 或使用浏览器
wscat -c ws://localhost:8080/ws
```

**预期**: 连接成功，执行操作时收到实时推送事件。

### T3.4 Web UI

在浏览器中打开 `http://<树莓派IP>:8080`，应看到单页控制台。

| 测试项 | 预期结果 | 通过 | 备注 |
|--------|---------|------|------|
| T3.1 REST 端点 | 所有端点返回 JSON | [ ] | |
| T3.2 invoke API | echo 正常返回 | [ ] | |
| T3.3 WebSocket | 连接成功，收到事件 | [ ] | |
| T3.4 Web UI | 页面正常加载 | [ ] | |

---

## T4. 语音交互

> 需要: USB 麦克风 + 扬声器 + PICOVOICE_ACCESS_KEY（可选，无则跳过唤醒词）

### T4.1 TTS 合成

```bash
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.voice.synthesize", "input": {"text": "你好，我是小车"}}' \
  | python3 -m json.tool
```

**预期**: 扬声器播放 "你好，我是小车"。

### T4.2 ASR 识别

```bash
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.voice.recognize", "input": {"timeout_s": 5}}' \
  | python3 -m json.tool
```

**预期**: 对着麦克风说话，返回识别的文本。

### T4.3 唤醒词循环（如配置了 Porcupine）

```bash
# 启动唤醒词监听
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.voice.listen_start", "input": {}}' \
  | python3 -m json.tool
```

**预期**: 系统进入监听状态，说出唤醒词后触发 ASR→Agent→TTS 循环。

### T4.4 停止唤醒词

```bash
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.voice.listen_stop", "input": {}}' \
  | python3 -m json.tool
```

| 测试项 | 预期结果 | 通过 | 备注 |
|--------|---------|------|------|
| T4.1 TTS | 扬声器播放语音 | [ ] | |
| T4.2 ASR | 返回识别文本 | [ ] | |
| T4.3 唤醒词 | 唤醒后自动交互 | [ ] | 需 Porcupine key |
| T4.4 停止监听 | 成功停止 | [ ] | |

---

## T5. 急停系统

### T5.1 Web 急停

```bash
# 先启动一个运动
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.motion.forward", "input": {"speed": 30, "duration_ms": 5000}}' &

# 立即急停
curl -s -X POST http://localhost:8080/api/stop | python3 -m json.tool
```

**预期**: 运动立即停止，返回成功。

### T5.2 物理按钮急停

1. 启动一个长时间运动命令
2. 按下急停按钮（GPIO17）
3. 观察运动是否立即停止

**预期**: 按下按钮后运动立即停止，日志显示 `emergency_stop` 事件。

### T5.3 冷却期验证

急停后立即尝试运动：

```bash
# 急停
curl -s -X POST http://localhost:8080/api/stop

# 立即尝试前进（应被拒绝）
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.motion.forward", "input": {"speed": 30, "duration_ms": 1000}}' \
  | python3 -m json.tool
```

**预期**: 冷却期内返回 `E_POLICY_*` 错误，操作被拒绝。

### T5.4 冷却后恢复

等待冷却期（默认 2 秒）后再尝试：

```bash
sleep 6
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.motion.forward", "input": {"speed": 30, "duration_ms": 1000}}' \
  | python3 -m json.tool
```

**预期**: 冷却期后操作成功执行。

| 测试项 | 预期结果 | 通过 | 备注 |
|--------|---------|------|------|
| T5.1 Web 急停 | 运动立即停止 | [ ] | |
| T5.2 物理按钮 | 按钮触发急停 | [ ] | 需接线 |
| T5.3 冷却期 | 操作被拒绝 | [ ] | |
| T5.4 冷却恢复 | 操作恢复正常 | [ ] | |

---

## T6. 安全策略

### T6.1 模式切换

```bash
# 查看当前模式
curl -s http://localhost:8080/api/status | python3 -c "import sys,json;print(json.load(sys.stdin)['mode'])"

# 切换到 kid 模式
curl -s -X POST http://localhost:8080/api/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "kid"}' | python3 -m json.tool

# 切换到 safety 模式
curl -s -X POST http://localhost:8080/api/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "safety"}' | python3 -m json.tool

# 恢复 normal 模式
curl -s -X POST http://localhost:8080/api/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "normal"}' | python3 -m json.tool
```

### T6.2 速度限制（kid 模式）

```bash
# 切换到 kid 模式
curl -s -X POST http://localhost:8080/api/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "kid"}'

# 尝试高速运动
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.motion.forward", "input": {"speed": 100, "duration_ms": 1000}}' \
  | python3 -m json.tool
```

**预期**: kid 模式下速度被限制到安全上限。

### T6.3 危险操作确认流

通过 chat 接口要求 Agent 执行潜在危险操作，观察是否进入 CONFIRMING 状态。

```bash
curl -s -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "全速前进5秒"}' | python3 -m json.tool
```

**预期**: 如果操作被判定为危险级别，系统进入 CONFIRMING 状态，等待确认。

| 测试项 | 预期结果 | 通过 | 备注 |
|--------|---------|------|------|
| T6.1 模式切换 | 3 种模式都能切换 | [ ] | |
| T6.2 速度限制 | kid 模式限速 | [ ] | |
| T6.3 确认流 | 危险操作需确认 | [ ] | |

---

## T7. 记忆系统

### T7.1 创建记忆（通过对话）

```bash
curl -s -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "请记住我喜欢蓝色"}' | python3 -m json.tool
```

**预期**: Agent 提议记忆写入，确认后写入成功。

### T7.2 查询记忆

```bash
curl -s http://localhost:8080/api/memories | python3 -m json.tool
```

**预期**: 返回记忆列表，包含刚创建的记忆。

### T7.3 关键词搜索

```bash
curl -s "http://localhost:8080/api/memories/search?q=蓝色" | python3 -m json.tool
```

**预期**: 搜索到包含"蓝色"的记忆。

### T7.4 删除记忆

```bash
# 先获取记忆 ID
MEMORY_ID=$(curl -s http://localhost:8080/api/memories | python3 -c "import sys,json;ms=json.load(sys.stdin);print(ms[0]['id'] if ms else '')")

# 删除
curl -s -X DELETE "http://localhost:8080/api/memories/$MEMORY_ID" | python3 -m json.tool
```

### T7.5 导出记忆

```bash
curl -s http://localhost:8080/api/memories/export > memories_backup.json
cat memories_backup.json | python3 -m json.tool
```

### T7.6 导入记忆

```bash
curl -s -X POST http://localhost:8080/api/memories/import \
  -H "Content-Type: application/json" \
  -d @memories_backup.json | python3 -m json.tool
```

### T7.7 按类型清除

```bash
curl -s -X POST http://localhost:8080/api/memories/clear \
  -H "Content-Type: application/json" \
  -d '{"type": "preference"}' | python3 -m json.tool
```

| 测试项 | 预期结果 | 通过 | 备注 |
|--------|---------|------|------|
| T7.1 创建记忆 | Agent 提议并写入 | [ ] | |
| T7.2 查询记忆 | 返回记忆列表 | [ ] | |
| T7.3 搜索 | 关键词搜索命中 | [ ] | |
| T7.4 删除 | 指定记忆被删除 | [ ] | |
| T7.5 导出 | JSON 文件生成 | [ ] | |
| T7.6 导入 | 记忆恢复成功 | [ ] | |
| T7.7 按类型清除 | 指定类型全部删除 | [ ] | |

---

## T8. 硬件模块

> 以下测试需要实际硬件连接。Mock 模式下也会返回模拟数据。

### T8.1 运动模块

```bash
# 前进
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.motion.forward", "input": {"speed": 30, "duration_ms": 2000}}' \
  | python3 -m json.tool

# 后退
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.motion.backward", "input": {"speed": 30, "duration_ms": 2000}}' \
  | python3 -m json.tool

# 左转
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.motion.turn_left", "input": {"speed": 30, "duration_ms": 1000}}' \
  | python3 -m json.tool

# 右转
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.motion.turn_right", "input": {"speed": 30, "duration_ms": 1000}}' \
  | python3 -m json.tool

# 停止
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.motion.stop", "input": {}}' \
  | python3 -m json.tool
```

### T8.2 传感器模块

```bash
# 超声波距离
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.sensor.ultrasonic", "input": {}}' \
  | python3 -m json.tool

# 红外障碍物
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.sensor.infrared", "input": {}}' \
  | python3 -m json.tool
```

**预期**: 超声波返回 `distance_cm`，红外返回 `left_obstacle`/`right_obstacle` 障碍物状态。

### T8.3 显示模块

```bash
# 显示表情
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.display.show_expression", "input": {"expression": "happy"}}' \
  | python3 -m json.tool

# 显示文字
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.display.show_text", "input": {"text": "Hello mcar!"}}' \
  | python3 -m json.tool

# 清除显示
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.display.clear", "input": {}}' \
  | python3 -m json.tool
```

**预期**: OLED 分别显示表情图案、文字、清屏。

可选表情: `happy`, `sad`, `thinking`, `confused`, `excited`, `sleeping`, `listening`, `speaking`, `neutral`

### T8.4 按钮模块

```bash
# 查询按钮状态
curl -s -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability_id": "tool.button.status", "input": {}}' \
  | python3 -m json.tool
```

**预期**: 返回按钮当前状态（是否按下、GPIO 检测可用性）。

| 测试项 | 预期结果 | 通过 | 备注 |
|--------|---------|------|------|
| T8.1a 前进 | 电机正转 | [ ] | |
| T8.1b 后退 | 电机反转 | [ ] | |
| T8.1c 左转 | 左转 | [ ] | |
| T8.1d 右转 | 右转 | [ ] | |
| T8.1e 停止 | 电机停止 | [ ] | |
| T8.2a 超声波 | 返回距离 cm | [ ] | |
| T8.2b 红外 | 返回 left_obstacle/right_obstacle | [ ] | |
| T8.3a 表情 | OLED 显示表情 | [ ] | |
| T8.3b 文字 | OLED 显示文字 | [ ] | |
| T8.3c 清屏 | OLED 清空 | [ ] | |
| T8.4 按钮状态 | 返回按钮状态 | [ ] | |

---

## T9. 技能系统

### T9.1 列出技能

```bash
curl -s http://localhost:8080/api/skills | python3 -m json.tool
```

**预期**: 返回内置技能列表（self_check, night_mode, patrol）。

### T9.2 执行 self_check

```bash
curl -s -X POST http://localhost:8080/api/skills/self_check/execute | python3 -m json.tool
```

**预期**: 执行自检流程，返回各模块健康状态汇总。

### T9.3 执行 night_mode

```bash
curl -s -X POST http://localhost:8080/api/skills/night_mode/execute | python3 -m json.tool
```

**预期**: 切换到夜间模式，降低显示亮度、限制运动速度。

| 测试项 | 预期结果 | 通过 | 备注 |
|--------|---------|------|------|
| T9.1 列出技能 | 3 个内置技能 | [ ] | |
| T9.2 self_check | 自检完成，返回状态 | [ ] | |
| T9.3 night_mode | 夜间模式生效 | [ ] | |

---

## T10. 监控运维

### T10.1 健康检查

```bash
curl -s http://localhost:8080/api/health | python3 -m json.tool
```

**预期**: 返回各模块健康状态，总体 `status` 为 `healthy` 或 `degraded`。

### T10.2 模块进程状态

```bash
curl -s http://localhost:8080/api/watchdog | python3 -m json.tool
```

**预期**: 返回各模块进程的 PID、重启次数、状态。

### T10.3 性能指标

```bash
curl -s http://localhost:8080/api/metrics | python3 -m json.tool
```

**预期**: 返回各操作的延迟百分位指标（p50/p95/p99）。需要先执行一些操作产生数据。

### T10.4 审计日志

```bash
# 最近 100 条
curl -s http://localhost:8080/api/audit | python3 -m json.tool

# 导出全部
curl -s http://localhost:8080/api/audit/export > audit_export.json
```

**预期**: 返回审计日志列表，包含之前执行的操作记录。

### T10.5 会话回放

```bash
# 列出会话
curl -s http://localhost:8080/api/sessions | python3 -m json.tool

# 回放指定会话 (替换 SESSION_ID)
SESSION_ID=$(curl -s http://localhost:8080/api/sessions | python3 -c "import sys,json;ss=json.load(sys.stdin);print(ss[0]['id'] if ss else '')")
curl -s "http://localhost:8080/api/sessions/$SESSION_ID/replay" | python3 -m json.tool
```

### T10.6 规则引擎

```bash
# 规则状态
curl -s http://localhost:8080/api/rules/status | python3 -m json.tool

# 手动触发规则评估
curl -s -X POST http://localhost:8080/api/rules/evaluate | python3 -m json.tool
```

| 测试项 | 预期结果 | 通过 | 备注 |
|--------|---------|------|------|
| T10.1 健康检查 | 返回模块健康状态 | [ ] | |
| T10.2 Watchdog | 返回进程状态 | [ ] | |
| T10.3 指标 | 返回延迟百分位 | [ ] | |
| T10.4 审计日志 | 返回操作记录 | [ ] | |
| T10.5 会话回放 | 回放事件流 | [ ] | |
| T10.6 规则引擎 | 规则状态/评估 | [ ] | |

---

## 测试总结表

| 类别 | 测试数 | 通过 | 失败 | 跳过 |
|------|-------|------|------|------|
| T1 基础启动 | 3 | | | |
| T2 文本对话 | 3 | | | |
| T3 Web 控制台 | 4 | | | |
| T4 语音交互 | 4 | | | |
| T5 急停系统 | 4 | | | |
| T6 安全策略 | 3 | | | |
| T7 记忆系统 | 7 | | | |
| T8 硬件模块 | 11 | | | |
| T9 技能系统 | 3 | | | |
| T10 监控运维 | 6 | | | |
| **合计** | **48** | | | |

**测试日期**: ____________
**测试人员**: ____________
**树莓派型号**: ____________
**系统版本**: ____________
**备注**: ____________
