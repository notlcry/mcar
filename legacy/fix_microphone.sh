#!/bin/bash
# 修复USB麦克风问题

echo "🎤 检查音频设备状态..."

echo "播放设备:"
aplay -l

echo -e "\n录音设备:"
arecord -l

echo -e "\n检查USB设备:"
lsusb | grep -i audio || echo "未找到USB音频设备"

echo -e "\n检查音频权限:"
groups | grep -E "(audio|pulse)" && echo "✅ 用户在音频组中" || echo "❌ 用户不在音频组中"

echo -e "\n测试不同的录音设备配置..."

# 测试直接使用card 1
echo "测试 hw:1,0:"
timeout 2 arecord -D hw:1,0 -f cd -t wav /dev/null 2>/dev/null && echo "✅ hw:1,0 正常" || echo "❌ hw:1,0 异常"

# 测试使用plughw
echo "测试 plughw:1,0:"
timeout 2 arecord -D plughw:1,0 -f cd -t wav /dev/null 2>/dev/null && echo "✅ plughw:1,0 正常" || echo "❌ plughw:1,0 异常"

# 测试不同的采样率
echo "测试不同采样率:"
for rate in 16000 22050 44100 48000; do
    timeout 2 arecord -D hw:1,0 -r $rate -f S16_LE -c 1 -t wav /dev/null 2>/dev/null && echo "✅ $rate Hz 正常" || echo "❌ $rate Hz 异常"
done

echo -e "\n创建修复的ALSA配置..."

# 创建更兼容的配置
cat > ~/.asoundrc << 'EOF'
# 修复的ALSA配置 - 兼容USB麦克风

# 默认设备
pcm.!default {
    type asym
    playback.pcm "hw:0,0"
    capture.pcm "plughw:1,0"
}

ctl.!default {
    type hw
    card 0
}

# 专用设备
pcm.speakers {
    type hw
    card 0
    device 0
}

pcm.microphone {
    type plug
    slave {
        pcm "hw:1,0"
        rate 16000
        channels 1
        format S16_LE
    }
}

# USB麦克风专用配置
pcm.usb_mic {
    type plug
    slave {
        pcm "hw:1,0"
        rate 16000
        channels 1
        format S16_LE
    }
}
EOF

echo "✅ 新的ALSA配置已创建"

# 重启音频服务
echo "🔄 重启音频服务..."
sudo alsactl restore 2>/dev/null || true
pulseaudio --kill 2>/dev/null || true
sleep 2
pulseaudio --start 2>/dev/null || true

echo -e "\n🧪 测试修复后的录音设备..."
timeout 3 arecord -D microphone -t wav /dev/null 2>/dev/null && echo "✅ 麦克风修复成功" || echo "❌ 麦克风仍有问题"

timeout 3 arecord -D usb_mic -t wav /dev/null 2>/dev/null && echo "✅ USB麦克风配置正常" || echo "❌ USB麦克风配置异常"

echo "✅ 麦克风修复完成"