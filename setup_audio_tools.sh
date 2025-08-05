#!/bin/bash
# 安装和配置音频工具

echo "🔧 安装ALSA音频工具..."

# 更新包列表
sudo apt update

# 安装ALSA工具
sudo apt install -y alsa-utils alsa-tools

# 检查是否安装成功
if command -v arecord &> /dev/null; then
    echo "✅ arecord 安装成功"
    arecord --version
else
    echo "❌ arecord 安装失败"
fi

if command -v aplay &> /dev/null; then
    echo "✅ aplay 安装成功"
    aplay --version
else
    echo "❌ aplay 安装失败"
fi

# 列出音频设备
echo ""
echo "📊 可用的音频录制设备:"
arecord -l

echo ""
echo "📊 可用的音频播放设备:"
aplay -l

echo ""
echo "📊 PCM设备列表:"
arecord -L | head -20

echo ""
echo "🎛️ 音频控制器:"
amixer controls | head -10

echo ""
echo "🔊 当前音频设置:"
amixer sget Master 2>/dev/null || echo "无Master音量控制"
amixer sget Capture 2>/dev/null || echo "无Capture音量控制"

echo ""
echo "✅ 音频工具安装和检测完成"