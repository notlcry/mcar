#!/bin/bash
# 修复音频设备权限问题

echo "🔧 修复音频设备权限..."

# 检查当前用户和组
echo "当前用户: $(whoami)"
echo "当前组: $(groups)"

# 添加用户到所有音频相关组
echo "添加用户到音频组..."
sudo usermod -a -G audio $USER
sudo usermod -a -G pulse-access $USER
sudo usermod -a -G pulse $USER

# 检查音频设备权限
echo -e "\n检查音频设备权限:"
ls -la /dev/snd/

# 修复音频设备权限
echo -e "\n修复音频设备权限..."
sudo chmod 666 /dev/snd/*

# 检查USB音频设备
echo -e "\n检查USB音频设备:"
lsusb | grep -i audio

# 重启音频服务
echo -e "\n重启音频服务..."
sudo systemctl restart alsa-state || true
pulseaudio --kill 2>/dev/null || true
sleep 2
pulseaudio --start 2>/dev/null || true

# 创建简单的ALSA配置
echo -e "\n创建简单的ALSA配置..."
cat > ~/.asoundrc << 'EOF'
# 简单的ALSA配置 - 解决权限问题

pcm.!default {
    type asym
    playback.pcm "hw:0,0"
    capture.pcm "plughw:1,0"
}

ctl.!default {
    type hw
    card 0
}

pcm.speakers {
    type hw
    card 0
}

pcm.microphone {
    type plug
    slave.pcm "hw:1,0"
}
EOF

echo "✅ ALSA配置已更新"

# 测试录音权限
echo -e "\n🧪 测试录音权限..."

# 测试基本录音
echo "测试基本录音 (3秒):"
timeout 3 arecord -D plughw:1,0 -f cd -t wav /tmp/test_audio.wav 2>/dev/null && echo "✅ 基本录音成功" || echo "❌ 基本录音失败"

# 测试配置的麦克风
echo "测试配置的麦克风 (3秒):"
timeout 3 arecord -D microphone -t wav /tmp/test_mic.wav 2>/dev/null && echo "✅ 配置麦克风成功" || echo "❌ 配置麦克风失败"

# 清理测试文件
rm -f /tmp/test_audio.wav /tmp/test_mic.wav

echo -e "\n⚠️  重要提醒:"
echo "如果权限修复后仍有问题，请："
echo "1. 重新登录或重启系统"
echo "2. 确保USB麦克风连接稳定"
echo "3. 检查是否有其他程序占用麦克风"

echo -e "\n✅ 音频权限修复完成"