# AI桌宠系统 API 文档

## 📋 概述

本文档详细描述了AI桌宠系统的所有API接口，包括REST API、WebSocket接口和内部Python API。开发者可以使用这些接口来扩展功能、集成第三方应用或构建自定义客户端。

## 🌐 REST API 接口

### 基础信息

- **基础URL**: `http://your-robot-ip:5000`
- **内容类型**: `application/json`
- **认证**: 无（本地网络使用）

### 系统状态 API

#### GET /status
获取系统整体状态信息

**响应示例**:
```json
{
    "status": "running",
    "timestamp": "2024-01-01T12:00:00Z",
    "uptime": 3600,
    "components": {
        "robot_controller": "active",
        "ai_conversation": "active",
        "voice_control": "active",
        "camera": "active",
        "sensors": {
            "ultrasonic": "active",
            "infrared_left": "active",
            "infrared_right": "active"
        }
    },
    "current_emotion": "happy",
    "conversation_active": true,
    "voice_control_active": true
}
```

#### GET /health
系统健康检查

**响应示例**:
```json
{
    "status": "healthy",
    "checks": {
        "database": "ok",
        "ai_api": "ok",
        "hardware": "ok",
        "memory_usage": "normal"
    }
}
```

### 运动控制 API

#### POST /control
控制机器人运动

**请求参数**:
```json
{
    "action": "forward",     // 动作类型
    "duration": 1.0,         // 持续时间（秒）
    "speed": 50              // 速度 (0-100)
}
```

**支持的动作类型**:
- `forward` - 前进
- `backward` - 后退
- `left` - 左转
- `right` - 右转
- `shift_left` - 左平移
- `shift_right` - 右平移
- `stop` - 停止

**响应示例**:
```json
{
    "success": true,
    "action": "forward",
    "duration": 1.0,
    "timestamp": "2024-01-01T12:00:00Z"
}
```

#### POST /speed
设置运动速度

**请求参数**:
```json
{
    "speed": 75  // 速度值 (0-100)
}
```

#### GET /sensors
获取传感器数据

**响应示例**:
```json
{
    "ultrasonic_distance": 25.6,
    "infrared_left": false,
    "infrared_right": true,
    "timestamp": "2024-01-01T12:00:00Z"
}
```

### AI对话 API

#### POST /ai_conversation
启动或停止AI对话模式

**请求参数**:
```json
{
    "action": "start"  // "start" 或 "stop"
}
```

**响应示例**:
```json
{
    "success": true,
    "conversation_active": true,
    "session_id": "session_1234567890_5678"
}
```

#### POST /ai_chat
发送对话消息

**请求参数**:
```json
{
    "message": "你好，今天天气怎么样？",
    "session_id": "session_1234567890_5678"
}
```

**响应示例**:
```json
{
    "success": true,
    "response": "你好！今天天气很不错呢，阳光明媚的~",
    "emotion_detected": "happy",
    "actions_triggered": ["show_happy_expression", "gentle_movement"],
    "session_id": "session_1234567890_5678",
    "timestamp": "2024-01-01T12:00:00Z"
}
```

#### GET /conversation_history
获取对话历史

**查询参数**:
- `session_id` (可选): 特定会话ID
- `limit` (可选): 返回条数限制，默认50
- `offset` (可选): 偏移量，默认0

**响应示例**:
```json
{
    "conversations": [
        {
            "timestamp": "2024-01-01T12:00:00Z",
            "user_input": "你好",
            "ai_response": "你好！很高兴见到你~",
            "emotion_detected": "happy",
            "session_id": "session_123"
        }
    ],
    "total_count": 25,
    "has_more": false
}
```

#### POST /clear_history
清空对话历史

**请求参数**:
```json
{
    "session_id": "session_123",  // 可选，不提供则清空所有
    "confirm": true
}
```

### 语音控制 API

#### POST /voice_control
启动或停止语音控制

**请求参数**:
```json
{
    "action": "start",  // "start" 或 "stop"
    "mode": "conversation"  // "conversation" 或 "command"
}
```

#### GET /voice_status
获取语音控制状态

**响应示例**:
```json
{
    "voice_control_active": true,
    "listening": false,
    "last_recognized": "向前",
    "recognition_confidence": 0.85,
    "microphone_available": true
}
```

### 情感表达 API

#### GET /ai_emotion
获取当前情感状态

**响应示例**:
```json
{
    "current_emotion": "happy",
    "intensity": 0.8,
    "secondary_emotions": {
        "excited": 0.3,
        "curious": 0.2
    },
    "duration": 15.5,
    "expression_active": true
}
```

#### POST /ai_execute_emotion
手动触发情感表达

**请求参数**:
```json
{
    "emotion": "excited",
    "intensity": 0.9,
    "duration": 5.0
}
```

### 个性管理 API

#### GET /ai_personality
获取个性设置

**响应示例**:
```json
{
    "name": "快快",
    "user_name": "小明",
    "traits": {
        "friendliness": 0.8,
        "energy_level": 0.7,
        "curiosity": 0.6,
        "playfulness": 0.9
    },
    "movement_style": "bouncy",
    "voice_settings": {
        "voice": "zh-CN-XiaoxiaoNeural",
        "rate": "+0%",
        "volume": "+0%"
    }
}
```

#### POST /ai_personality
更新个性设置

**请求参数**:
```json
{
    "name": "新名字",
    "traits": {
        "friendliness": 0.9
    },
    "voice_settings": {
        "voice": "zh-CN-YunxiNeural"
    }
}
```

### 会话管理 API

#### POST /session/create
创建新会话

**响应示例**:
```json
{
    "session_id": "session_1234567890_5678",
    "created_at": "2024-01-01T12:00:00Z"
}
```

#### GET /session/{session_id}
获取会话信息

**响应示例**:
```json
{
    "session_id": "session_123",
    "start_time": "2024-01-01T12:00:00Z",
    "last_activity": "2024-01-01T12:30:00Z",
    "conversation_count": 15,
    "current_emotion": "happy",
    "active": true
}
```

#### GET /sessions
列出所有活跃会话

**响应示例**:
```json
{
    "sessions": [
        {
            "session_id": "session_123",
            "start_time": "2024-01-01T12:00:00Z",
            "last_activity": "2024-01-01T12:30:00Z",
            "active": true
        }
    ],
    "total_count": 1
}
```

### 记忆系统 API

#### GET /memory/preferences
获取用户偏好

**查询参数**:
- `type` (可选): 偏好类型筛选

**响应示例**:
```json
{
    "preferences": [
        {
            "type": "user_info",
            "key": "name",
            "value": "小明",
            "confidence": 1.0,
            "last_updated": "2024-01-01T12:00:00Z"
        }
    ]
}
```

#### POST /memory/preferences
更新用户偏好

**请求参数**:
```json
{
    "type": "personality",
    "key": "favorite_activity",
    "value": "listening_to_music",
    "confidence": 0.8
}
```

#### GET /memory/search
搜索对话记录

**查询参数**:
- `query`: 搜索关键词
- `limit`: 结果数量限制

**响应示例**:
```json
{
    "results": [
        {
            "timestamp": "2024-01-01T12:00:00Z",
            "user_input": "我喜欢听音乐",
            "ai_response": "音乐真是太棒了！",
            "relevance_score": 0.95
        }
    ],
    "total_matches": 3
}
```

## 🔌 WebSocket 接口

### 连接信息

- **WebSocket URL**: `ws://your-robot-ip:5000/ws`
- **协议**: WebSocket

### 实时数据流

#### 传感器数据流
```json
{
    "type": "sensor_data",
    "data": {
        "ultrasonic_distance": 25.6,
        "infrared_left": false,
        "infrared_right": true
    },
    "timestamp": "2024-01-01T12:00:00Z"
}
```

#### 情感状态更新
```json
{
    "type": "emotion_update",
    "data": {
        "emotion": "excited",
        "intensity": 0.8,
        "expression": "big_eyes_animation"
    },
    "timestamp": "2024-01-01T12:00:00Z"
}
```

#### 语音识别结果
```json
{
    "type": "voice_recognition",
    "data": {
        "text": "向前",
        "confidence": 0.85,
        "action": "forward"
    },
    "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🐍 Python API

### 核心类接口

#### AIConversationManager

```python
from ai_conversation import AIConversationManager

# 初始化
ai_manager = AIConversationManager()

# 启动对话模式
ai_manager.start_conversation_mode()

# 处理用户输入
response = ai_manager.process_user_input("你好")

# 获取对话上下文
context = ai_manager.get_conversation_context()

# 停止对话模式
ai_manager.stop_conversation_mode()
```

#### EmotionEngine

```python
from emotion_engine import EmotionEngine

# 初始化
emotion_engine = EmotionEngine()

# 分析文本情感
emotion = emotion_engine.analyze_response_emotion("我很开心！")

# 获取当前情感状态
current_state = emotion_engine.get_current_emotional_state()

# 更新情感状态
emotion_engine.update_emotion("happy", intensity=0.8)
```

#### PersonalityManager

```python
from personality_manager import PersonalityManager

# 初始化
personality = PersonalityManager(robot_controller)

# 执行情感驱动运动
personality.execute_emotional_movement("happy", intensity=0.8)

# 获取个性化回复风格
style = personality.get_personality_response_style()

# 更新个性特征
personality.update_personality_traits(friendliness=0.9)
```

#### MemoryManager

```python
from memory_manager import MemoryManager

# 初始化
memory = MemoryManager()

# 存储对话
memory.store_conversation(
    session_id="session_123",
    user_input="你好",
    ai_response="你好！",
    emotion="happy"
)

# 获取对话历史
history = memory.get_conversation_history("session_123")

# 搜索对话
results = memory.search_conversations("音乐")

# 存储用户偏好
memory.store_user_preference("user_info", "name", "小明")
```

### 配置管理

```python
from config import config_manager

# 获取配置
ai_config = config_manager.get_ai_settings()
voice_config = config_manager.get_voice_settings()

# 更新配置
config_manager.update_personality(name="新名字")
config_manager.update_voice_settings(voice="zh-CN-YunxiNeural")

# 保存配置
config_manager.save_config()
```

## 🔧 错误处理

### 标准错误响应

所有API在出错时返回统一格式：

```json
{
    "success": false,
    "error": {
        "code": "INVALID_PARAMETER",
        "message": "参数 'action' 是必需的",
        "details": {
            "parameter": "action",
            "expected_type": "string"
        }
    },
    "timestamp": "2024-01-01T12:00:00Z"
}
```

### 错误代码

| 错误代码 | 描述 | HTTP状态码 |
|---------|------|-----------|
| `INVALID_PARAMETER` | 参数无效或缺失 | 400 |
| `HARDWARE_ERROR` | 硬件操作失败 | 500 |
| `AI_API_ERROR` | AI服务调用失败 | 502 |
| `SESSION_NOT_FOUND` | 会话不存在 | 404 |
| `VOICE_UNAVAILABLE` | 语音服务不可用 | 503 |
| `MEMORY_ERROR` | 记忆系统错误 | 500 |

## 📊 限制和配额

### API调用限制

- **对话API**: 每分钟最多60次请求
- **运动控制**: 每秒最多10次请求
- **传感器数据**: 每秒最多20次请求

### 数据限制

- **对话消息长度**: 最大1000字符
- **会话历史**: 每个会话最多保存1000条对话
- **用户偏好**: 每种类型最多100个偏好项

## 🔐 安全考虑

### 输入验证

所有API输入都经过严格验证：
- 参数类型检查
- 长度限制
- 特殊字符过滤
- SQL注入防护

### 访问控制

- 仅限本地网络访问
- 无需认证（适用于家庭环境）
- 可配置IP白名单

### 数据保护

- 所有数据本地存储
- 不上传到云端
- 支持数据导出和删除

## 📈 性能优化

### 缓存策略

- 对话历史内存缓存
- 用户偏好缓存
- 配置文件缓存

### 异步处理

- AI API调用异步化
- 语音合成后台处理
- 传感器数据异步更新

## 🧪 测试工具

### API测试脚本

```bash
# 测试基础功能
curl -X GET http://localhost:5000/status

# 测试运动控制
curl -X POST http://localhost:5000/control \
  -H "Content-Type: application/json" \
  -d '{"action": "forward", "duration": 1.0}'

# 测试AI对话
curl -X POST http://localhost:5000/ai_chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
```

### Python测试示例

```python
import requests
import json

# 基础API测试
def test_api():
    base_url = "http://localhost:5000"
    
    # 测试状态接口
    response = requests.get(f"{base_url}/status")
    print("Status:", response.json())
    
    # 测试运动控制
    control_data = {
        "action": "forward",
        "duration": 1.0,
        "speed": 50
    }
    response = requests.post(f"{base_url}/control", json=control_data)
    print("Control:", response.json())
    
    # 测试AI对话
    chat_data = {"message": "你好"}
    response = requests.post(f"{base_url}/ai_chat", json=chat_data)
    print("Chat:", response.json())

if __name__ == "__main__":
    test_api()
```

## 📚 SDK 和客户端库

### JavaScript/Node.js

```javascript
// AI桌宠客户端库
class AIPetClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }
    
    async getStatus() {
        const response = await fetch(`${this.baseUrl}/status`);
        return response.json();
    }
    
    async sendMessage(message) {
        const response = await fetch(`${this.baseUrl}/ai_chat`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message})
        });
        return response.json();
    }
    
    async controlMovement(action, duration = 1.0) {
        const response = await fetch(`${this.baseUrl}/control`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({action, duration})
        });
        return response.json();
    }
}

// 使用示例
const client = new AIPetClient('http://192.168.1.100:5000');
client.sendMessage('你好').then(response => {
    console.log('AI回复:', response.response);
});
```

### Python客户端

```python
import requests
import json

class AIPetClient:
    def __init__(self, base_url):
        self.base_url = base_url
    
    def get_status(self):
        response = requests.get(f"{self.base_url}/status")
        return response.json()
    
    def send_message(self, message):
        data = {"message": message}
        response = requests.post(f"{self.base_url}/ai_chat", json=data)
        return response.json()
    
    def control_movement(self, action, duration=1.0):
        data = {"action": action, "duration": duration}
        response = requests.post(f"{self.base_url}/control", json=data)
        return response.json()

# 使用示例
client = AIPetClient('http://192.168.1.100:5000')
result = client.send_message('你好')
print('AI回复:', result['response'])
```

## 📝 更新日志

### v1.0.0 (2024-01-01)
- 初始API版本发布
- 支持基础运动控制
- 支持AI对话功能
- 支持语音控制
- 支持情感表达
- 支持记忆系统

---

*本文档持续更新中，如有问题请查看故障排除指南或提交Issue。*