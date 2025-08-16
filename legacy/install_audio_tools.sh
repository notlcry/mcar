#!/bin/bash
"""
安装音频播放工具
"""

echo "🔧 安装音频播放工具"
echo "=" * 50

# 更新包列表
echo "📦 更新包列表..."
sudo apt update

# 安装音频播放工具
echo "🎵 安装音频播放工具..."

# 安装 alsa-utils (包含 aplay)
echo "安装 alsa-utils (aplay)..."
sudo apt install -y alsa-utils

# 安装 mpg123
echo "安装 mpg123..."
sudo apt install -y mpg123

# 安装 ffmpeg (包含 ffplay)
echo "安装 ffmpeg (ffplay)..."
sudo apt install -y ffmpeg

# 安装其他可能需要的音频工具
echo "安装其他音频工具..."
sudo apt install -y sox
sudo apt install -y pulseaudio-utils

echo ""
echo "✅ 音频工具安装完成！"
echo ""
echo "📋 已安装的工具："
echo "- aplay (ALSA音频播放器)"
echo "- mpg123 (MP3播放器)"
echo "- ffplay (FFmpeg音频/视频播放器)"
echo "- sox (音频处理工具)"
echo "- pulseaudio-utils (PulseAudio工具)"
echo ""
echo "🔍 验证安装："

# 检查工具是否安装成功
if command -v aplay &> /dev/null; then
    echo "✅ aplay: $(aplay --version | head -1)"
else
    echo "❌ aplay: 未安装"
fi

if command -v mpg123 &> /dev/null; then
    echo "✅ mpg123: $(mpg123 --version | head -1)"
else
    echo "❌ mpg123: 未安装"
fi

if command -v ffplay &> /dev/null; then
    echo "✅ ffplay: $(ffplay -version | head -1)"
else
    echo "❌ ffplay: 未安装"
fi

echo ""
echo "🎉 安装完成！现在可以重启AI程序测试音频播放功能。"