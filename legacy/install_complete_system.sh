#!/bin/bash
# AI桌宠完整系统安装脚本
# 集成所有必要的配置和修复

set -e  # 遇到错误立即退出

echo "🤖 AI桌宠完整系统安装"
echo "=================================="
echo "这个脚本将安装所有必要的依赖和配置"
echo "预计需要15-30分钟，请耐心等待..."
echo

# 检查系统
if [ ! -f /etc/rpi-issue ]; then
    echo "⚠️  警告：此脚本专为树莓派设计"
    read -p "是否继续？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 检查网络连接
echo "🌐 检查网络连接..."
if ! ping -c 1 google.com &> /dev/null; then
    echo "❌ 网络连接失败，请检查网络设置"
    exit 1
fi
echo "✅ 网络连接正常"

# 1. 更新系统
echo
echo "📦 更新系统包..."
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# 2. 安装系统依赖
echo
echo "🔧 安装系统依赖..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    cmake \
    pkg-config \
    libjpeg-dev \
    libtiff5-dev \
    libjasper-dev \
    libpng-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libfontconfig1-dev \
    libcairo2-dev \
    libgdk-pixbuf2.0-dev \
    libpango1.0-dev \
    libgtk2.0-dev \
    libgtk-3-dev \
    libatlas-base-dev \
    gfortran \
    libhdf5-dev \
    libhdf5-serial-dev \
    libhdf5-103 \
    python3-pyqt5 \
    python3-h5py \
    alsa-utils \
    pulseaudio \
    pulseaudio-utils \
    libsdl2-mixer-2.0-0 \
    libsdl2-mixer-dev \
    portaudio19-dev \
    espeak \
    espeak-data \
    libespeak1 \
    libespeak-dev \
    festival \
    festvox-kallpc16k \
    git \
    wget \
    curl \
    unzip

echo "✅ 系统依赖安装完成"

# 3. 创建虚拟环境
echo
echo "🐍 创建Python虚拟环境..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✅ 虚拟环境创建完成"
else
    echo "✅ 虚拟环境已存在"
fi

# 激活虚拟环境
source .venv/bin/activate

# 4. 升级pip
echo
echo "📦 升级pip..."
pip install --upgrade pip

# 5. 安装Python依赖
echo
echo "🐍 安装Python依赖..."

# 基础依赖
pip install \
    numpy \
    opencv-python-headless \
    flask \
    requests \
    pygame \
    RPi.GPIO \
    smbus \
    picamera \
    pyaudio \
    SpeechRecognition \
    vosk \
    pvporcupine \
    google-generativeai \
    edge-tts \
    jieba \
    sqlite3 \
    threading \
    queue \
    logging \
    json \
    time \
    datetime \
    os \
    sys \
    subprocess \
    tempfile \
    wave \
    struct

echo "✅ Python依赖安装完成"

# 6. 配置语音系统
echo
echo "🎤 配置语音系统..."
./setup_voice_system.sh

# 7. 创建环境变量文件
echo
echo "⚙️  创建配置文件..."
if [ ! -f ".ai_pet_env" ]; then
    cat > .ai_pet_env << 'EOF'
# AI桌宠环境变量配置文件
# 请填入你的实际API密钥

# Google Gemini API密钥（必需）
# 获取地址: https://makersuite.google.com/app/apikey
export GEMINI_API_KEY="your_gemini_api_key_here"

# Picovoice访问密钥（可选，用于自定义唤醒词）
# 获取地址: https://console.picovoice.ai/
export PICOVOICE_ACCESS_KEY="your_picovoice_key_here"

# 项目路径
export AI_PET_HOME="$(pwd)"

# Python虚拟环境
export VIRTUAL_ENV="$(pwd)/.venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"

# 日志级别
export LOG_LEVEL="INFO"

# TTS语音设置
export TTS_VOICE="zh-CN-XiaoxiaoNeural"
export TTS_RATE="+0%"
export TTS_VOLUME="+0%"
EOF
    echo "✅ 环境变量文件已创建"
else
    echo "✅ 环境变量文件已存在"
fi

# 8. 设置权限
echo
echo "🔐 设置用户权限..."
sudo usermod -a -G audio,gpio,i2c,spi,dialout,video $USER
echo "✅ 用户权限设置完成"

# 9. 创建数据目录
echo
echo "📁 创建数据目录..."
mkdir -p src/data/{logs,temp,memory,sessions}
mkdir -p models
echo "✅ 数据目录创建完成"

# 10. 创建启动脚本
echo
echo "🚀 创建启动脚本..."
if [ ! -f "start_ai_pet_quiet.sh" ]; then
    cat > start_ai_pet_quiet.sh << 'EOF'
#!/bin/bash
# AI桌宠静默启动脚本

# 设置环境变量
export ALSA_QUIET=1
export SDL_AUDIODRIVER=alsa

# 重定向ALSA错误到/dev/null
exec 2> >(grep -v "ALSA lib" >&2)

echo "🤖 启动AI桌宠系统..."

# 激活虚拟环境
source .venv/bin/activate

# 加载环境变量
source .ai_pet_env

# 启动主程序
cd src
python3 robot_voice_web_control.py 2>&1 | grep -v "ALSA lib"
EOF
    chmod +x start_ai_pet_quiet.sh
    echo "✅ 启动脚本创建完成"
else
    echo "✅ 启动脚本已存在"
fi

# 11. 创建systemd服务
echo
echo "🔄 创建系统服务..."
sudo tee /etc/systemd/system/ai-desktop-pet.service > /dev/null << EOF
[Unit]
Description=AI Desktop Pet Voice System
After=network.target sound.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/.venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$(pwd)/start_ai_pet_quiet.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
echo "✅ 系统服务创建完成"

# 12. 最终测试
echo
echo "🧪 系统测试..."
source .venv/bin/activate
python3 verify_system.py

if [ $? -eq 0 ]; then
    echo
    echo "=================================="
    echo "🎉 AI桌宠系统安装完成！"
    echo "=================================="
    echo
    echo "📋 安装总结:"
    echo "✅ 系统依赖已安装"
    echo "✅ Python虚拟环境已创建"
    echo "✅ 语音系统已配置"
    echo "✅ 用户权限已设置"
    echo "✅ 系统服务已创建"
    echo "✅ 核心功能测试通过"
    echo
    echo "⚙️  下一步配置:"
    echo "1. 编辑API密钥："
    echo "   nano .ai_pet_env"
    echo "   # 设置 GEMINI_API_KEY"
    echo
    echo "2. 重启系统（推荐）："
    echo "   sudo reboot"
    echo
    echo "3. 启动AI桌宠："
    echo "   ./start_ai_pet_quiet.sh"
    echo "   # 或使用系统服务："
    echo "   sudo systemctl start ai-desktop-pet"
    echo
    echo "🌐 Web界面: http://你的树莓派IP:5000"
    echo
    echo "📚 更多信息请查看: INSTALL_COMPLETE.md"
else
    echo
    echo "❌ 安装过程中出现问题"
    echo "请查看错误信息并参考故障排除指南"
    echo "📚 故障排除: TROUBLESHOOTING_GUIDE.md"
fi