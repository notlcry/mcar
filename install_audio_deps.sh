#!/bin/bash
# 安装音频依赖包

echo "🔧 安装音频处理依赖包..."

# 安装系统级音频工具
echo "📦 安装ALSA工具..."
sudo apt update
sudo apt install -y alsa-utils alsa-tools

# 安装Python音频库
echo "📦 安装Python音频库..."
pip3 install sounddevice

# 检查安装结果
echo ""
echo "✅ 检查安装结果:"

if command -v arecord &> /dev/null; then
    echo "✅ arecord 已安装"
else
    echo "❌ arecord 未安装"
fi

if python3 -c "import sounddevice" 2>/dev/null; then
    echo "✅ sounddevice 已安装"
    python3 -c "import sounddevice as sd; print(f'sounddevice版本: {sd.__version__}')"
else
    echo "❌ sounddevice 未安装"
fi

if python3 -c "import pyaudio" 2>/dev/null; then
    echo "✅ pyaudio 已安装"
else
    echo "⚠️ pyaudio 未安装 (可选)"
fi

echo ""
echo "🎛️ 音频设备信息:"
if command -v arecord &> /dev/null; then
    echo "录音设备:"
    arecord -l
fi

echo ""
echo "✅ 音频依赖安装完成"