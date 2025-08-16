#!/bin/bash
# 彻底修复ALSA音频配置问题

echo "🔧 开始修复ALSA音频配置..."

# 1. 备份现有配置
echo "📦 备份现有配置..."
if [ -f ~/.asoundrc ]; then
    cp ~/.asoundrc ~/.asoundrc.backup.$(date +%Y%m%d_%H%M%S)
fi

# 2. 创建最简单有效的ALSA配置
echo "⚙️ 创建新的ALSA配置..."
cat > ~/.asoundrc << 'EOF'
# 简化的ALSA配置 - 避免复杂的环绕声配置
defaults.pcm.card 0
defaults.pcm.device 0
defaults.ctl.card 0

# 默认播放设备
pcm.!default {
    type hw
    card 0
    device 0
}

# 默认控制设备
ctl.!default {
    type hw
    card 0
}

# 麦克风设备（如果有USB麦克风）
pcm.microphone {
    type hw
    card 1
    device 0
}

# 禁用所有复杂的插件和环绕声配置
pcm.surround21 {
    type hw
    card 0
    device 0
}

pcm.surround40 {
    type hw
    card 0
    device 0
}

pcm.surround41 {
    type hw
    card 0
    device 0
}

pcm.surround50 {
    type hw
    card 0
    device 0
}

pcm.surround51 {
    type hw
    card 0
    device 0
}

pcm.surround71 {
    type hw
    card 0
    device 0
}

pcm.iec958 {
    type hw
    card 0
    device 0
}

pcm.spdif {
    type hw
    card 0
    device 0
}
EOF

# 3. 设置环境变量来抑制ALSA错误
echo "🔇 设置ALSA错误抑制..."
cat >> ~/.bashrc << 'EOF'

# ALSA错误抑制
export ALSA_QUIET=1
export ALSA_PCM_CARD=0
export ALSA_PCM_DEVICE=0
export SDL_AUDIODRIVER=alsa
export PULSE_RUNTIME_PATH=/tmp/pulse-runtime
EOF

# 4. 创建系统级ALSA配置
echo "🌐 创建系统级配置..."
sudo mkdir -p /etc/alsa/conf.d
sudo tee /etc/alsa/conf.d/99-disable-surround.conf > /dev/null << 'EOF'
# 禁用环绕声和复杂音频配置
pcm.!surround21 {
    type hw
    card 0
    device 0
}
pcm.!surround40 {
    type hw
    card 0
    device 0
}
pcm.!surround41 {
    type hw
    card 0
    device 0
}
pcm.!surround50 {
    type hw
    card 0
    device 0
}
pcm.!surround51 {
    type hw
    card 0
    device 0
}
pcm.!surround71 {
    type hw
    card 0
    device 0
}
EOF

# 5. 重新加载ALSA配置
echo "🔄 重新加载ALSA配置..."
sudo alsa force-reload 2>/dev/null || true

# 6. 创建Python音频测试脚本
echo "🐍 创建Python音频测试..."
cat > test_audio_simple.py << 'EOF'
#!/usr/bin/env python3
import os
import sys

# 设置环境变量抑制ALSA错误
os.environ['ALSA_QUIET'] = '1'
os.environ['SDL_AUDIODRIVER'] = 'alsa'

def test_pygame_audio():
    """测试pygame音频系统"""
    try:
        import pygame
        # 使用最简单的音频配置
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=1024)
        pygame.mixer.init()
        print("✅ pygame音频系统初始化成功")
        pygame.mixer.quit()
        return True
    except Exception as e:
        print(f"❌ pygame音频系统失败: {e}")
        return False

def test_pyaudio():
    """测试pyaudio"""
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        print("✅ pyaudio初始化成功")
        print(f"   音频设备数量: {p.get_device_count()}")
        p.terminate()
        return True
    except Exception as e:
        print(f"❌ pyaudio失败: {e}")
        return False

if __name__ == "__main__":
    print("🔊 测试音频系统...")
    pygame_ok = test_pygame_audio()
    pyaudio_ok = test_pyaudio()
    
    if pygame_ok and pyaudio_ok:
        print("\n🎉 音频系统测试通过！")
        sys.exit(0)
    else:
        print("\n⚠️ 音频系统有问题，但可能不影响基本功能")
        sys.exit(1)
EOF

chmod +x test_audio_simple.py

# 7. 创建启动脚本，抑制ALSA错误
echo "🚀 创建无错误启动脚本..."
cat > start_ai_pet_quiet.sh << 'EOF'
#!/bin/bash
# 启动AI桌宠系统，抑制ALSA错误

# 设置环境变量
export ALSA_QUIET=1
export SDL_AUDIODRIVER=alsa
export ALSA_PCM_CARD=0
export ALSA_PCM_DEVICE=0

# 重定向ALSA错误到/dev/null
exec 2> >(grep -v "ALSA lib" >&2)

echo "🤖 启动AI桌宠系统..."
cd src
python3 robot_voice_web_control.py 2>&1 | grep -v "ALSA lib"
EOF

chmod +x start_ai_pet_quiet.sh

echo ""
echo "✅ ALSA配置修复完成！"
echo ""
echo "🧪 测试音频系统:"
echo "   python3 test_audio_simple.py"
echo ""
echo "🚀 启动AI桌宠（无ALSA错误）:"
echo "   ./start_ai_pet_quiet.sh"
echo ""
echo "📝 如果仍有问题，请重启系统后再试"