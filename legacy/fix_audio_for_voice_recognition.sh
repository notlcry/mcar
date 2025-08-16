#!/bin/bash
# 修复音频配置用于中文语音识别
# 解决音量过小和ALSA错误问题

echo "🔧 修复音频配置用于中文语音识别"
echo "=================================="

# 1. 安装必要软件包
echo "📦 安装必要软件包..."
sudo apt-get update
sudo apt-get install -y flac alsa-utils pulseaudio-utils

# 2. 检测音频设备
echo "🎤 检测音频设备..."
echo "录音设备:"
arecord -l
echo ""
echo "播放设备:"
aplay -l
echo ""

# 3. 创建优化的ALSA配置
echo "🔧 创建优化的ALSA配置..."
cat > ~/.asoundrc << 'EOF'
# 优化的ALSA配置用于语音识别
# 解决Raspberry Pi音频问题

pcm.!default {
    type asym
    playback.pcm "playback"
    capture.pcm "capture"
}

pcm.playback {
    type hw
    card 0
    device 0
}

pcm.capture {
    type dsnoop
    ipc_key 1024
    slave {
        pcm "hw:1,0"
        period_size 1024
        buffer_size 4096
        rate 16000
        format S16_LE
        channels 1
    }
    bindings.0 0
}

ctl.!default {
    type hw
    card 0
}

# 如果上面的配置不工作，使用备选方案
pcm.microphone {
    type dsnoop
    ipc_key 1024
    slave {
        pcm "hw:1,0"
        rate 16000
        format S16_LE
        channels 1
    }
}
EOF

echo "✅ ALSA配置文件已创建: ~/.asoundrc"

# 4. 设置音频权限
echo "🔐 设置音频权限..."
sudo usermod -a -G audio $USER

# 5. 调整麦克风音量
echo "🎚️ 调整麦克风音量..."
echo "正在设置麦克风音量到85%..."

# 尝试不同的麦克风控制名称
for control in "Mic" "Microphone" "Capture" "Digital" "Mic Boost" "Internal Mic Boost"; do
    amixer sset "$control" 85% 2>/dev/null && echo "✅ 已设置 $control 音量"
done

# 设置捕获音量
amixer sset "Capture" 85% 2>/dev/null
amixer sset "Capture" cap 2>/dev/null

# 6. 重启音频服务
echo "🔄 重启音频服务..."
sudo systemctl restart alsa-state 2>/dev/null || true
pulseaudio -k 2>/dev/null || true
sleep 2
pulseaudio --start 2>/dev/null || true

# 7. 测试音频录制
echo "🧪 测试音频录制..."
echo "测试3秒录音..."
if arecord -D hw:1,0 -f S16_LE -r 16000 -c 1 -d 3 test_audio.wav 2>/dev/null; then
    echo "✅ 录音测试成功"
    
    # 分析音频文件
    if command -v sox >/dev/null 2>&1; then
        sox test_audio.wav -n stat 2>&1 | grep -E "(Maximum amplitude|RMS amplitude)"
    fi
    
    echo "播放录音测试..."
    aplay test_audio.wav 2>/dev/null
    rm -f test_audio.wav
else
    echo "❌ 录音测试失败"
fi

# 8. 创建环境变量设置
echo "🌍 设置环境变量..."
cat >> ~/.bashrc << 'EOF'

# 语音识别优化环境变量
export ALSA_CARD=1
export ALSA_DEVICE=0
export ALSA_QUIET=1
export SDL_AUDIODRIVER=alsa
EOF

echo ""
echo "=================================="
echo "🎉 音频配置修复完成！"
echo ""
echo "📋 重要提醒:"
echo "1. 请重新登录或运行 'source ~/.bashrc'"
echo "2. 重启系统以确保所有更改生效"
echo "3. 如果还有问题，运行 'alsamixer' 手动调整音量"
echo ""
echo "🧪 测试命令:"
echo "1. 测试录音: arecord -D hw:1,0 -f S16_LE -r 16000 -c 1 -d 3 test.wav"
echo "2. 播放测试: aplay test.wav"
echo "3. 查看设备: arecord -l"
echo "4. 音量控制: alsamixer"
echo ""
echo "🚀 现在可以运行修复后的语音识别测试:"
echo "   python3 fix_chinese_voice_recognition.py"