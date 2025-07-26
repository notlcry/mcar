# AI桌宠系统设置指南

## 快速开始

### 1. 安装依赖

```bash
cd src
chmod +x install_ai_dependencies.sh
./install_ai_dependencies.sh
```

### 2. 配置API密钥

编辑环境变量文件：
```bash
nano ~/.ai_pet_env
```

填入你的API密钥：
```bash
# Google Gemini API密钥
export GEMINI_API_KEY="your_gemini_api_key_here"

# Picovoice访问密钥（可选，用于自定义唤醒词）
export PICOVOICE_ACCESS_KEY="your_picovoice_access_key_here"
```

加载环境变量：
```bash
source ~/.ai_pet_env
```

### 3. 测试系统

运行完整测试：
```bash
python3 test_ai_conversation.py
```

### 4. 启动AI桌宠

```bash
python3 robot_voice_web_control.py
```

然后在浏览器中访问：`http://树莓派IP:5000`

## API密钥获取

### Google Gemini API
1. 访问：https://makersuite.google.com/app/apikey
2. 登录Google账号
3. 创建新的API密钥
4. 复制密钥到配置文件

### Picovoice（可选）
1. 访问：https://console.picovoice.ai/
2. 注册账号
3. 获取访问密钥
4. 用于自定义唤醒词训练

## 功能测试

### 测试AI对话
```bash
python3 ai_conversation.py
```

### 测试语音控制
```bash
python3 enhanced_voice_control.py
```

### 测试唤醒词检测
```bash
python3 wake_word_detector.py
```

## 配置文件

系统会自动创建 `ai_pet_config.json` 配置文件，包含：

- AI设置（模型、温度、个性提示）
- 语音设置（TTS语音、唤醒词）
- 个性配置（名字、性格特征）
- 系统设置（历史长度、超时时间）

## 个性化设置

### 修改机器人名字
```python
from config import config_manager
config_manager.update_personality(name="你的机器人名字")
```

### 调整性格特征
```python
config_manager.update_personality(
    friendliness=0.9,    # 友好度 (0-1)
    energy_level=0.8,    # 活跃度 (0-1)
    playfulness=0.7      # 顽皮度 (0-1)
)
```

### 更换TTS语音
```python
config_manager.update_voice_settings(
    tts_voice="zh-CN-YunxiNeural"  # 男声
    # 或 "zh-CN-XiaoxiaoNeural"   # 女声
)
```

## 故障排除

### 常见问题

1. **Gemini API调用失败**
   - 检查API密钥是否正确
   - 确认网络连接正常
   - 检查API配额是否用完

2. **语音识别不工作**
   - 检查麦克风连接
   - 调整麦克风音量
   - 确认PulseAudio服务运行

3. **TTS播放无声音**
   - 检查音频输出设备
   - 安装音频播放工具：`sudo apt install alsa-utils`
   - 测试音频：`speaker-test`

4. **唤醒词检测失败**
   - 如果没有Picovoice密钥，会使用简单检测器
   - 说话清晰，距离麦克风适中
   - 检查环境噪音

### 日志查看

系统日志会显示详细的错误信息，帮助诊断问题：
```bash
python3 robot_voice_web_control.py 2>&1 | tee ai_pet.log
```

### 重置配置

删除配置文件重新开始：
```bash
rm ai_pet_config.json
```

## 高级功能

### 自定义唤醒词

1. 注册Picovoice账号获取访问密钥
2. 在Picovoice控制台训练自定义唤醒词
3. 下载.ppn文件到项目目录
4. 更新配置使用自定义唤醒词

### 扩展个性提示

编辑 `config.py` 中的 `personality_prompt` 来自定义AI的行为风格。

### 添加新的情感动作

在 `enhanced_voice_control.py` 的 `_execute_emotional_action` 方法中添加新的动作模式。

## 系统要求

- 树莓派4B或更高配置
- Python 3.7+
- 至少2GB RAM
- 稳定的网络连接
- USB麦克风
- 音频输出设备（扬声器/耳机）

## 性能优化

- 使用较小的Gemini模型（如gemini-1.5-flash）
- 限制对话历史长度
- 调整音频采样率
- 使用本地Whisper模型减少网络依赖