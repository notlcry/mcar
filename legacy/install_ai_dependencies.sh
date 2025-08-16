#!/bin/bash
# AI桌宠依赖安装脚本
# 安装Google Gemini API、Porcupine唤醒词检测、edge-tts等依赖

echo "====== 安装AI桌宠依赖项 ======"

# 更新系统包
echo "更新系统包..."
sudo apt update

# 安装系统依赖
echo "安装系统依赖..."
sudo apt install -y \
    python3-pip \
    python3-dev \
    portaudio19-dev \
    espeak \
    espeak-data \
    libespeak1 \
    libespeak-dev \
    ffmpeg \
    alsa-utils \
    pulseaudio

# 升级pip
echo "升级pip..."
python3 -m pip install --upgrade pip

# 安装Python依赖
echo "安装Python依赖..."
pip3 install \
    google-generativeai \
    pvporcupine \
    pyaudio \
    edge-tts \
    pygame \
    SpeechRecognition \
    pocketsphinx \
    luma.oled \
    pillow

# 安装Whisper.cpp相关依赖（可选，用于本地语音识别）
echo "安装Whisper相关依赖..."
pip3 install \
    openai-whisper \
    torch \
    torchaudio

# 创建环境变量配置文件
echo "创建环境变量配置文件..."
cat > ~/.ai_pet_env << 'EOF'
# AI桌宠环境变量配置
# 请填入你的API密钥

# Google Gemini API密钥
# 获取地址: https://makersuite.google.com/app/apikey
export GEMINI_API_KEY="your_gemini_api_key_here"

# Picovoice访问密钥（用于自定义唤醒词）
# 获取地址: https://console.picovoice.ai/
export PICOVOICE_ACCESS_KEY="your_picovoice_access_key_here"

# 加载环境变量
source ~/.ai_pet_env
EOF

echo ""
echo "====== 安装完成 ======"
echo ""
echo "请完成以下配置步骤："
echo "1. 编辑 ~/.ai_pet_env 文件，填入你的API密钥"
echo "2. 运行 'source ~/.ai_pet_env' 加载环境变量"
echo "3. 或者将以下行添加到 ~/.bashrc 中："
echo "   source ~/.ai_pet_env"
echo ""
echo "API密钥获取地址："
echo "- Gemini API: https://makersuite.google.com/app/apikey"
echo "- Picovoice: https://console.picovoice.ai/"
echo ""
echo "测试安装："
echo "python3 ai_conversation.py"
echo ""