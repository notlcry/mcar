#!/bin/bash
# 语音控制依赖安装脚本
# 适用于树莓派/Ubuntu系统

echo "====== 机器人语音控制依赖安装 ======"
echo "正在安装语音识别所需的系统依赖..."

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
    python3-pyaudio

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

# 安装 Python 依赖
echo "安装 Python 语音识别库..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

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

echo ""
echo "====== 安装完成 ======"
echo "注意事项："
echo "1. 请确保USB麦克风已正确连接"
echo "2. 如果遇到权限问题，请重新登录或重启系统"
echo "3. 可以运行 'python3 voice_control.py' 来单独测试语音控制"
echo "4. 运行 'python3 robot_voice_web_control.py' 启动完整的语音控制系统"
echo ""
echo "常见问题解决："
echo "- 如果麦克风无法识别，尝试: sudo modprobe snd-usb-audio"
echo "- 如果pyaudio安装失败，尝试: sudo apt-get install python3-pyaudio"
echo "- 如果语音识别不准确，在安静环境中使用并靠近麦克风" 