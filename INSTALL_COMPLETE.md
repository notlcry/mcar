# AI桌宠完整安装指南

## 🎯 一键安装（推荐）

```bash
# 完整安装AI桌宠系统（包含语音功能）
chmod +x install_complete_system.sh
./install_complete_system.sh
```

## 📋 安装内容

这个完整安装包含：

### ✅ 系统依赖
- Python 3.9+
- 音频系统（ALSA + PulseAudio）
- 摄像头支持
- GPIO权限配置

### ✅ Python库
- 基础库：Flask, OpenCV, pygame
- 语音识别：SpeechRecognition, pyaudio, vosk
- AI对话：google-generativeai
- 唤醒词检测：pvporcupine
- 语音合成：edge-tts

### ✅ 语音模型
- Vosk中文语音识别模型（离线）
- Porcupine唤醒词模型

### ✅ 系统配置
- ALSA音频配置（自动检测USB麦克风）
- 用户权限配置
- systemd服务配置

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone <your-repo-url>
cd ai-desktop-pet
```

### 2. 运行完整安装
```bash
chmod +x install_complete_system.sh
./install_complete_system.sh
```

### 3. 配置API密钥
```bash
# 编辑环境变量文件
nano .ai_pet_env

# 添加以下内容：
export GEMINI_API_KEY="your_gemini_api_key"
export PICOVOICE_ACCESS_KEY="your_picovoice_key"  # 可选
```

### 4. 启动系统
```bash
./start_ai_pet_quiet.sh
```

### 5. 访问Web界面
打开浏览器访问：`http://你的树莓派IP:5000`

## 🔧 故障排除

### 如果遇到问题

1. **音频问题**：
   ```bash
   # 重新配置音频系统
   ./setup_voice_system.sh
   ```

2. **权限问题**：
   ```bash
   # 重新登录或重启系统
   sudo reboot
   ```

3. **模型下载失败**：
   ```bash
   # 手动下载Vosk模型
   ./download_vosk_model.sh
   ```

4. **完全重置**：
   ```bash
   # 清理并重新安装
   ./cleanup_system.sh
   ./install_complete_system.sh
   ```

## 📊 系统要求

- **硬件**：树莓派4B（推荐4GB+内存）
- **系统**：Raspberry Pi OS Lite/Desktop
- **存储**：至少8GB SD卡（推荐16GB+）
- **外设**：USB麦克风、摄像头、扬声器

## 🎤 语音功能

### 支持的语音识别引擎
1. **Vosk**（主要）：中文离线识别
2. **Google**（备选）：中文在线识别
3. **PocketSphinx**（最后备选）：英文离线识别

### 唤醒词
- **内置**：`picovoice`
- **自定义**：配置PICOVOICE_ACCESS_KEY后可使用自定义唤醒词

## 🌐 Web界面功能

- ✅ 实时视频流
- ✅ 机器人运动控制
- ✅ AI文字对话
- ✅ 语音识别和对话
- ✅ 自动避障开关
- ✅ 速度调节

## 🔄 系统服务

### 手动启动
```bash
./start_ai_pet_quiet.sh
```

### 系统服务
```bash
# 启动服务
sudo systemctl start ai-desktop-pet

# 开机自启
sudo systemctl enable ai-desktop-pet

# 查看状态
sudo systemctl status ai-desktop-pet

# 查看日志
sudo journalctl -u ai-desktop-pet -f
```

## 📝 配置文件

### 主要配置文件
- `.ai_pet_env`：环境变量和API密钥
- `~/.asoundrc`：ALSA音频配置
- `ai_pet_config.json`：系统配置（自动生成）

### 模型文件
- `models/vosk-model-small-cn-0.22/`：Vosk中文模型
- `src/wake_words/`：自定义唤醒词文件

## 🆘 获取帮助

### 日志文件
- 系统日志：`sudo journalctl -u ai-desktop-pet`
- 应用日志：`src/data/logs/ai_pet.log`

### 诊断工具
```bash
# 系统健康检查
python3 verify_system.py

# 语音系统诊断
python3 diagnose_voice_issues.py

# 音频设备检测
python3 detect_audio_devices.py
```

### 常见问题
参考：`TROUBLESHOOTING_GUIDE.md`

---

**最后更新**：2025年7月27日  
**版本**：2.0  
**适用系统**：树莓派4B + Raspberry Pi OS