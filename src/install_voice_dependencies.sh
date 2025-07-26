#!/bin/bash
# 增强语音控制依赖安装脚本
# 适用于树莓派/Ubuntu系统 - 支持AI对话、Whisper、edge-tts等

echo "====== 增强语音控制系统依赖安装 ======"
echo "正在安装AI语音对话所需的系统依赖..."

# 更新包管理器
echo "更新软件包列表..."
sudo apt-get update

# 安装音频相关依赖
echo "安装音频系统依赖..."
sudo apt-get install -y \
    alsa-utils \
    pulseaudio \
    pulseaudio-utils \
    libasound2-dev \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    python3-pyaudio \
    mpg123 \
    ffmpeg \
    sox \
    libsox-fmt-all

# 安装语音识别依赖
echo "安装语音识别依赖..."
sudo apt-get install -y \
    espeak \
    espeak-data \
    libespeak1 \
    libespeak-dev \
    festival \
    festvox-kallpc16k

# 安装 PocketSphinx 依赖
echo "安装 PocketSphinx 依赖..."
sudo apt-get install -y \
    swig \
    libpulse-dev \
    libasound2-dev \
    libsamplerate0-dev \
    python3-dev \
    pkg-config

# 安装 Whisper 系统依赖
echo "安装 Whisper 系统依赖..."
sudo apt-get install -y \
    build-essential \
    cmake \
    git \
    libfftw3-dev \
    libopenblas-dev

# 安装 Python 依赖
echo "安装 Python 语音识别库..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

# 安装额外的AI语音依赖
echo "安装AI语音对话依赖..."
pip3 install --upgrade \
    edge-tts>=6.1.0 \
    openai-whisper>=20231117 \
    pvporcupine>=3.0.0 \
    pygame>=2.1.0 \
    google-generativeai>=0.3.0 \
    asyncio \
    aiofiles

# 配置音频权限
echo "配置音频权限..."
sudo usermod -a -G audio $USER

# 检测USB麦克风
echo "检测音频设备..."
echo "=== 音频录音设备 ==="
arecord -l
echo ""
echo "=== 音频播放设备 ==="
aplay -l
echo ""

# 测试麦克风
echo "测试麦克风（如果有的话）..."
if command -v arecord >/dev/null 2>&1; then
    echo "可以使用以下命令测试麦克风："
    echo "arecord -d 3 test.wav && aplay test.wav"
fi

# 下载Whisper模型（可选）
echo ""
echo "是否下载Whisper语音识别模型？(y/n)"
read -r download_whisper
if [ "$download_whisper" = "y" ] || [ "$download_whisper" = "Y" ]; then
    echo "下载Whisper基础模型..."
    python3 -c "import whisper; whisper.load_model('tiny'); whisper.load_model('base')"
    echo "Whisper模型下载完成"
fi

# 运行系统设置脚本
echo ""
echo "运行增强语音系统设置..."
python3 setup_enhanced_voice.py

echo ""
echo "====== 安装完成 ======"
echo "增强语音控制系统已安装完成！"
echo ""
echo "功能特性："
echo "✓ AI对话支持（Google Gemini）"
echo "✓ 唤醒词检测（'喵喵小车'）"
echo "✓ Whisper本地语音识别"
echo "✓ Edge-TTS语音合成"
echo "✓ 情感表达和个性化动作"
echo "✓ 语音识别确认反馈"
echo ""
echo "测试命令："
echo "1. 基本功能测试: python3 test_enhanced_voice_system.py"
echo "2. 语音演示: python3 enhanced_voice_control.py demo"
echo "3. 完整系统测试: python3 enhanced_voice_control.py"
echo ""
echo "启动命令："
echo "- 启动完整系统: python3 robot_voice_web_control.py"
echo ""
echo "配置文件："
echo "- 语音配置: voice_control_config.json"
echo "- AI配置: ai_pet_config.json"
echo ""
echo "注意事项："
echo "1. 请确保USB麦克风已正确连接"
echo "2. 需要配置Google Gemini API密钥"
echo "3. 如果遇到权限问题，请重新登录或重启系统"
echo "4. 首次使用建议在安静环境中测试"
echo ""
echo "常见问题解决："
echo "- 麦克风无法识别: sudo modprobe snd-usb-audio"
echo "- PyAudio安装失败: sudo apt-get install python3-pyaudio"
echo "- Whisper模型下载失败: 检查网络连接"
echo "- Edge-TTS无法使用: 检查网络连接"
echo "- 语音识别不准确: 在安静环境中使用并靠近麦克风" 