# AI桌宠树莓派部署指南

## 🚨 重要提醒：虚拟环境不能跨平台使用

**不要**直接复制开发机器上的`.venv`文件夹到树莓派！

### 为什么不能直接使用？

1. **架构差异**：Mac/PC (x86_64) vs 树莓派 (ARM)
2. **系统差异**：macOS/Windows vs Linux (Raspberry Pi OS)
3. **编译包差异**：很多Python包包含平台特定的二进制文件
4. **硬件包差异**：RPi.GPIO等包只能在树莓派上运行

## 📋 正确的部署流程

### 方法1：自动化安装（推荐）

```bash
# 1. 克隆项目到树莓派
git clone <your-repo-url> ai-desktop-pet
cd ai-desktop-pet

# 2. 运行自动安装脚本
chmod +x install_ai_desktop_pet.sh
./install_ai_desktop_pet.sh

# 3. 配置API密钥
chmod +x setup_api_keys.sh
./setup_api_keys.sh

# 4. 启动系统
cd src
python3 robot_voice_web_control.py
```

### 方法2：手动安装

```bash
# 1. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 2. 升级pip
pip install --upgrade pip

# 3. 安装依赖（使用树莓派专用版本）
pip install -r requirements_raspberry_pi.txt

# 4. 配置环境变量
cp .ai_pet_env.example .ai_pet_env
nano .ai_pet_env  # 填入API密钥

# 5. 测试安装
python3 test_config.py
```

## 🔧 树莓派特殊配置

### 系统依赖安装

```bash
# 音频系统
sudo apt install alsa-utils pulseaudio portaudio19-dev

# I2C和GPIO
sudo apt install i2c-tools python3-smbus

# 摄像头支持
sudo raspi-config  # 启用摄像头接口

# 编译工具
sudo apt install build-essential cmake
```

### 硬件接口启用

```bash
# 编辑配置文件
sudo nano /boot/config.txt

# 添加以下行：
dtparam=i2c_arm=on
dtparam=spi=on
start_x=1
gpu_mem=128
```

### 权限配置

```bash
# 添加用户到必要的组
sudo usermod -a -G audio,video,i2c,gpio,spi $USER

# 重新登录以应用权限变更
```

## 📦 依赖包说明

### 核心依赖（必需）
- `flask` - Web服务框架
- `RPi.GPIO` - 树莓派GPIO控制
- `opencv-python-headless` - 图像处理（无GUI版本）
- `google-generativeai` - AI对话服务

### 音频依赖
- `pyaudio` - 音频输入输出
- `SpeechRecognition` - 语音识别
- `edge-tts` - 语音合成
- `pygame` - 音频播放

### 硬件依赖
- `adafruit-circuitpython-ssd1306` - OLED显示
- `picamera` - 树莓派摄像头

### 可选依赖（资源消耗大）
- `torch` - 机器学习框架
- `openai-whisper` - 高质量语音识别

## ⚡ 性能优化建议

### 对于树莓派4B (4GB RAM)
```bash
# 使用轻量级依赖
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 限制并发进程
export OMP_NUM_THREADS=2
```

### 对于树莓派4B (8GB RAM)
```bash
# 可以使用完整功能
pip install -r requirements_raspberry_pi.txt
```

### 对于树莓派3B+或更低配置
```bash
# 建议禁用Whisper和Torch
# 在requirements_raspberry_pi.txt中注释掉相关行
```

## 🔍 安装验证

### 1. 基础功能测试
```bash
python3 test_config.py
```

### 2. 硬件测试
```bash
# 测试GPIO
python3 -c "import RPi.GPIO as GPIO; print('GPIO OK')"

# 测试I2C
i2cdetect -y 1

# 测试摄像头
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera Failed')"

# 测试音频
arecord -d 3 test.wav && aplay test.wav
```

### 3. AI功能测试
```bash
# 测试AI对话（需要API密钥）
python3 -c "
from src.config import config_manager
ai_config = config_manager.get_ai_config()
print('API Key configured:' if ai_config.gemini_api_key else 'API Key missing')
"
```

## 🚀 启动选项

### 开发模式
```bash
cd src
python3 robot_voice_web_control.py --debug
```

### 生产模式（系统服务）
```bash
# 设置系统服务
./setup_systemd_service.sh

# 启动服务
sudo systemctl start ai-desktop-pet@pi.service

# 查看状态
sudo systemctl status ai-desktop-pet@pi.service
```

## 🔧 常见问题

### 1. 虚拟环境创建失败
```bash
# 安装venv模块
sudo apt install python3-venv

# 清理后重新创建
rm -rf .venv
python3 -m venv .venv
```

### 2. PyAudio安装失败
```bash
# 安装系统依赖
sudo apt install portaudio19-dev python3-pyaudio

# 或使用系统包
pip install --global-option="build_ext" pyaudio
```

### 3. Torch安装时间过长
```bash
# 使用预编译版本
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 或暂时跳过
# 在requirements中注释掉torch相关行
```

### 4. 权限问题
```bash
# 检查用户组
groups $USER

# 重新添加权限
sudo usermod -a -G audio,video,i2c,gpio $USER

# 重新登录
```

## 📊 资源监控

### 安装后检查资源使用
```bash
# 内存使用
free -h

# 磁盘使用
df -h

# CPU温度
vcgencmd measure_temp

# 进程监控
htop
```

## 🎯 部署检查清单

- [ ] 项目代码已传输到树莓派
- [ ] 虚拟环境已重新创建（不是复制的）
- [ ] 系统依赖已安装
- [ ] Python依赖已安装
- [ ] 硬件接口已启用（I2C、摄像头等）
- [ ] 用户权限已配置
- [ ] API密钥已配置
- [ ] 基础功能测试通过
- [ ] 硬件测试通过
- [ ] Web界面可访问

完成以上步骤后，你的AI桌宠就可以在树莓派上正常运行了！🤖✨