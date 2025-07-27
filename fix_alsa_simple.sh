#!/bin/bash
# 创建简化的ALSA配置来解决音频问题

# 备份当前配置
cp ~/.asoundrc ~/.asoundrc.backup.$(date +%Y%m%d_%H%M%S)

# 创建简化的ALSA配置
cat > ~/.asoundrc << 'EOF'
# 简化的ALSA配置 - 解决树莓派音频问题
# 播放: card 0 (bcm2835 Headphones)  
# 录音: card 1 (USB PnP Sound Device)

# 默认设备 - 直接指向硬件
pcm.!default {
    type asym
    playback.pcm "hw:0,0"
    capture.pcm "hw:1,0"
}

ctl.!default {
    type hw
    card 0
}

# 专用设备别名
pcm.speakers {
    type hw
    card 0
    device 0
}

pcm.microphone {
    type hw
    card 1
    device 0
}
EOF

echo "✅ 简化的ALSA配置已创建"

# 重启音频服务
echo "🔄 重启音频服务..."
sudo alsactl restore
pulseaudio --kill 2>/dev/null || true
sleep 2
pulseaudio --start 2>/dev/null || true

echo "🧪 测试音频设备..."
echo "播放设备测试:"
speaker-test -D speakers -c 2 -t wav -l 1 2>/dev/null || echo "播放测试失败"

echo "录音设备测试:"
timeout 3 arecord -D microphone -f cd -t wav /dev/null 2>/dev/null && echo "✅ 录音设备正常" || echo "❌ 录音设备异常"

echo "✅ ALSA配置修复完成"