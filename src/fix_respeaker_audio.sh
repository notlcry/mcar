#!/bin/bash
# ReSpeaker 2-Mics Pi HAT 音频系统修复脚本

echo "🔧 修复ReSpeaker音频配置..."

# 1. 停止音频服务
echo "⏹️ 停止音频服务..."
sudo systemctl stop alsa-state
sudo killall pulseaudio 2>/dev/null || true

# 2. 重新加载ALSA配置
echo "🔄 重新加载ALSA配置..."
sudo alsactl init

# 3. 检查ReSpeaker驱动
echo "🔍 检查音频设备..."
aplay -l | grep -i "seeed\|respeaker\|usb"
arecord -l | grep -i "seeed\|respeaker\|usb"

# 4. 设置默认音频设备
echo "🎛️ 配置默认音频设备..."

# 创建.asoundrc配置文件
cat > ~/.asoundrc << 'EOF'
# ReSpeaker 2-Mics配置
pcm.!default {
    type asym
    playback.pcm "playback"
    capture.pcm "capture"
}

pcm.playback {
    type plug
    slave.pcm "dmix"
}

pcm.capture {
    type plug
    slave {
        pcm "hw:1,0"
        rate 48000
        channels 2
        format S16_LE
    }
}

pcm.dmix {
    type dmix
    ipc_key 1024
    slave {
        pcm "hw:0,0"
        rate 44100
        channels 2
        format S16_LE
    }
}

ctl.!default {
    type hw
    card 1
}
EOF

# 5. 设置音频权限
echo "🔐 设置音频权限..."
sudo usermod -a -G audio $USER

# 6. 重启音频服务
echo "🔄 重启音频服务..."
sudo systemctl restart alsa-state
pulseaudio --start --log-target=syslog 2>/dev/null || true

# 7. 测试音频录制
echo "🎤 测试音频录制..."
timeout 3s arecord -D hw:1,0 -f S16_LE -r 48000 -c 2 test_audio.wav 2>/dev/null && echo "✅ 录制测试成功" || echo "❌ 录制测试失败"
rm -f test_audio.wav

# 8. 显示最终状态
echo "📊 最终音频设备状态："
echo "播放设备："
aplay -l 2>/dev/null | grep -E "card|device" | head -5
echo "录制设备："
arecord -l 2>/dev/null | grep -E "card|device" | head -5

echo "✅ ReSpeaker音频配置修复完成！"
echo "💡 建议重启系统以确保所有更改生效"