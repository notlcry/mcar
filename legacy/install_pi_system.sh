#!/bin/bash
# AI桌宠树莓派系统级安装脚本
# 不使用虚拟环境，直接安装到系统Python

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

echo "🚀 AI桌宠树莓派系统级安装"
echo "=========================="
echo "• 不使用虚拟环境"
echo "• 直接安装到系统Python"
echo "• 使用系统预装OpenCV"
echo "• 适合树莓派4B"
echo

# 检查是否为树莓派
if [[ -f "/proc/device-tree/model" ]] && grep -q "Raspberry Pi" /proc/device-tree/model; then
    PI_MODEL=$(cat /proc/device-tree/model)
    log_info "检测到设备: $PI_MODEL"
else
    log_warn "未检测到树莓派，继续安装..."
fi

# 更新系统
log_step "更新系统包..."
sudo apt update
sudo apt upgrade -y

# 安装系统依赖
log_step "安装系统依赖..."
sudo apt install -y \
    python3-pip \
    python3-dev \
    python3-opencv \
    python3-numpy \
    python3-pil \
    python3-rpi.gpio \
    python3-smbus \
    i2c-tools \
    alsa-utils \
    pulseaudio \
    pulseaudio-utils \
    portaudio19-dev \
    python3-pyaudio \
    espeak \
    espeak-data \
    libespeak-dev \
    ffmpeg \
    sox \
    build-essential \
    cmake \
    pkg-config

log_info "系统依赖安装完成"

# 升级pip
log_step "升级pip..."
python3 -m pip install --upgrade pip

# 安装Python依赖（跳过系统已有的包）
log_step "安装Python依赖..."

# 创建临时requirements文件，排除系统已有包
cat > temp_requirements.txt << 'EOF'
# Web框架
flask>=2.0.1,<3.0.0
jinja2>=3.0.0,<4.0.0
werkzeug>=2.0.0,<3.0.0
markupsafe>=2.0.0,<3.0.0
itsdangerous>=2.0.0,<3.0.0
click>=8.0.0,<9.0.0

# 树莓派硬件（如果系统没有）
picamera>=1.13

# 音频处理
SpeechRecognition>=3.8.1
pocketsphinx>=0.1.15
pygame>=2.1.0

# AI和语音服务（使用兼容版本）
google-generativeai==0.3.2
grpcio==1.44.0
grpcio-status==1.44.0
pvporcupine>=3.0.0
edge-tts>=6.1.0
jieba>=0.42.1

# OLED显示
adafruit-circuitpython-ssd1306>=2.12.0
adafruit-blinka>=8.0.0

# 系统工具
requests>=2.25.0
aiofiles>=0.8.0
EOF

# 安装Python包
pip3 install -r temp_requirements.txt

# 清理临时文件
rm temp_requirements.txt

# 配置硬件接口
log_step "配置硬件接口..."

# 启用I2C
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    log_info "启用I2C接口..."
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
fi

# 启用摄像头
if ! grep -q "^start_x=1" /boot/config.txt; then
    log_info "启用摄像头接口..."
    echo "start_x=1" | sudo tee -a /boot/config.txt
    echo "gpu_mem=128" | sudo tee -a /boot/config.txt
fi

# 配置用户权限
log_step "配置用户权限..."
sudo usermod -a -G audio,video,i2c,gpio,spi,dialout $USER

# 创建环境变量配置
log_step "创建配置文件..."
if [[ ! -f ".ai_pet_env" ]]; then
    cp .ai_pet_env.example .ai_pet_env
    log_info "已创建 .ai_pet_env 配置文件"
fi

# 创建数据目录
mkdir -p src/data/ai_memory
mkdir -p src/data/logs
mkdir -p src/data/temp

# 测试安装
log_step "测试安装..."

python3 -c "
import sys
sys.path.append('src')

print('=== 系统组件测试 ===')

try:
    import cv2
    print(f'✅ OpenCV: {cv2.__version__}')
except Exception as e:
    print(f'❌ OpenCV: {e}')

try:
    import numpy as np
    print(f'✅ NumPy: {np.__version__}')
except Exception as e:
    print(f'❌ NumPy: {e}')

try:
    import RPi.GPIO as GPIO
    print('✅ RPi.GPIO: 可用')
except Exception as e:
    print(f'❌ RPi.GPIO: {e}')

try:
    import flask
    print(f'✅ Flask: {flask.__version__}')
except Exception as e:
    print(f'❌ Flask: {e}')

try:
    import google.generativeai as genai
    print('✅ Google Generative AI: 可用')
except Exception as e:
    print(f'❌ Google Generative AI: {e}')

try:
    import speech_recognition as sr
    print('✅ SpeechRecognition: 可用')
except Exception as e:
    print(f'❌ SpeechRecognition: {e}')

try:
    import edge_tts
    print('✅ Edge-TTS: 可用')
except Exception as e:
    print(f'❌ Edge-TTS: {e}')

try:
    import pygame
    print('✅ Pygame: 可用')
except Exception as e:
    print(f'❌ Pygame: {e}')

try:
    from config import ConfigManager
    config = ConfigManager('src/ai_pet_config.json')
    print('✅ 配置系统: 正常')
except Exception as e:
    print(f'❌ 配置系统: {e}')

print('\\n=== 硬件接口测试 ===')

# 测试I2C
import subprocess
try:
    result = subprocess.run(['i2cdetect', '-y', '1'], capture_output=True, text=True)
    if result.returncode == 0:
        print('✅ I2C接口: 可用')
    else:
        print('❌ I2C接口: 不可用')
except:
    print('❌ I2C接口: 测试失败')

# 测试音频设备
try:
    result = subprocess.run(['arecord', '-l'], capture_output=True, text=True)
    if 'card' in result.stdout:
        print('✅ 音频录制设备: 可用')
    else:
        print('❌ 音频录制设备: 未找到')
except:
    print('❌ 音频录制设备: 测试失败')
"

echo
echo "=============================="
echo "🎉 安装完成！"
echo "=============================="
echo
echo "安装方式："
echo "• ✅ 系统级安装（无虚拟环境）"
echo "• ✅ 使用系统OpenCV"
echo "• ✅ 所有依赖已安装"
echo
echo "接下来的步骤："
echo
echo "1. 配置API密钥:"
echo "   ./setup_api_keys.sh"
echo
echo "2. 配置自定义唤醒词（可选）:"
echo "   ./setup_custom_wake_word.sh"
echo
echo "3. 启动系统:"
echo "   cd src"
echo "   python3 robot_voice_web_control.py"
echo
echo "4. 访问Web界面:"
echo "   http://$(hostname -I | awk '{print $1}'):5000"
echo
echo "⚠️  重要提醒："
echo "• 如果修改了用户组权限，请重新登录或重启"
echo "• 如果启用了新的硬件接口，建议重启树莓派"
echo "• 首次使用建议在安静环境中测试语音功能"
echo
echo "🔧 故障排除:"
echo "• 查看安装日志上方的测试结果"
echo "• 如有问题，参考 TROUBLESHOOTING_GUIDE.md"
echo "• 测试硬件: python3 src/test_hardware.py"
echo