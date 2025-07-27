#!/bin/bash
# 安装TTS依赖 - 幂等脚本

echo "📦 安装TTS语音合成依赖..."

# 检查ffmpeg
if command -v ffmpeg &> /dev/null; then
    echo "✅ ffmpeg已安装"
else
    echo "🔄 安装ffmpeg..."
    sudo apt update
    sudo apt install -y ffmpeg
    
    if command -v ffmpeg &> /dev/null; then
        echo "✅ ffmpeg安装成功"
    else
        echo "❌ ffmpeg安装失败"
        exit 1
    fi
fi

# 检查edge-tts
if python3 -c "import edge_tts" 2>/dev/null; then
    echo "✅ edge-tts已安装"
else
    echo "🔄 安装edge-tts..."
    pip install edge-tts
    
    if python3 -c "import edge_tts" 2>/dev/null; then
        echo "✅ edge-tts安装成功"
    else
        echo "❌ edge-tts安装失败"
        exit 1
    fi
fi

echo "🎉 TTS依赖安装完成！"