#!/bin/bash
# 简化的ALSA修复 - 确保能工作

echo "🔧 简化ALSA配置修复"
echo "=================================="

# 1. 停止所有音频服务
echo "1. 停止音频服务..."
pulseaudio --kill 2>/dev/null
sudo systemctl stop alsa-state 2>/dev/null

# 2. 清理现有配置
echo "2. 清理现有配置..."
if [ -f ~/.asoundrc ]; then
    mv ~/.asoundrc ~/.asoundrc.broken.$(date +%s)
    echo "  已备份问题配置"
fi

# 3. 创建最简单可用的配置
echo "3. 创建简单配置..."
cat > ~/.asoundrc << 'EOF'
# 简单的ALSA配置 - 直接指定USB麦克风

pcm.!default {
    type plug
    slave.pcm "hw:1,0"
}

ctl.!default {
    type hw
    card 1
}
EOF

echo "  ✅ 简单配置已创建"

# 4. 重启音频服务
echo "4. 重启音频服务..."
sudo alsa force-reload 2>/dev/null
sleep 2

# 不启动PulseAudio，直接使用ALSA
echo "  使用纯ALSA模式（不启动PulseAudio）"

# 5. 测试配置
echo "5. 测试新配置..."
python3 << 'EOF'
import speech_recognition as sr
import sys

try:
    print("测试SpeechRecognition...")
    recognizer = sr.Recognizer()
    
    # 尝试创建麦克风
    microphone = sr.Microphone()
    print("✅ 麦克风创建成功")
    
    # 尝试调整噪音（短时间）
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
    print("✅ 环境噪音调整成功")
    print("🎉 ALSA配置修复成功！")
    
except Exception as e:
    print(f"❌ 仍有问题: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo
    echo "=================================="
    echo "🎉 ALSA修复成功！"
    echo "=================================="
    echo
    echo "📋 下一步:"
    echo "1. 重启AI桌宠系统:"
    echo "   停止当前系统 (Ctrl+C)"
    echo "   ./start_ai_pet_quiet.sh"
    echo
    echo "2. 在Web界面启用语音控制"
    echo
    echo "3. 应该能看到Vosk初始化日志"
else
    echo
    echo "❌ 修复失败，可能需要重启系统"
    echo "建议运行: sudo reboot"
fi