#!/bin/bash
# 彻底清理并重新配置ALSA

echo "🧹 清理ALSA配置..."

# 1. 删除损坏的配置文件
rm -f ~/.asoundrc
rm -f ~/.asoundrc.backup.*

# 2. 检查音频设备
echo "🔍 检查可用音频设备..."
aplay -l

# 3. 创建最简单的ALSA配置
echo "⚙️ 创建干净的ALSA配置..."
cat > ~/.asoundrc << 'EOF'
# 最简单的ALSA配置
defaults.pcm.card 0
defaults.pcm.device 0
defaults.ctl.card 0

pcm.!default {
    type hw
    card 0
    device 0
}

ctl.!default {
    type hw
    card 0
}
EOF

# 4. 测试ALSA配置
echo "🧪 测试ALSA配置..."
aplay -D default /usr/share/sounds/alsa/Noise.wav 2>/dev/null || echo "音频测试完成（可能没有声音文件）"

# 5. 创建简化的Python测试
cat > test_audio_minimal.py << 'EOF'
#!/usr/bin/env python3
import os
import sys

# 完全抑制ALSA错误
os.environ['ALSA_QUIET'] = '1'
os.environ['SDL_AUDIODRIVER'] = 'pulse'  # 尝试使用PulseAudio

def test_pygame_minimal():
    try:
        import pygame
        # 最小配置
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=2048)
        pygame.mixer.init()
        print("✅ pygame音频初始化成功")
        pygame.mixer.quit()
        return True
    except Exception as e:
        print(f"❌ pygame失败: {e}")
        # 尝试不同的驱动
        try:
            os.environ['SDL_AUDIODRIVER'] = 'alsa'
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=4096)
            pygame.mixer.init()
            print("✅ pygame音频初始化成功（ALSA驱动）")
            pygame.mixer.quit()
            return True
        except Exception as e2:
            print(f"❌ pygame ALSA也失败: {e2}")
            return False

if __name__ == "__main__":
    print("🔊 最小音频测试...")
    if test_pygame_minimal():
        print("🎉 音频系统可用！")
        sys.exit(0)
    else:
        print("⚠️ 音频系统不可用，但系统可能仍能工作")
        sys.exit(1)
EOF

chmod +x test_audio_minimal.py

echo ""
echo "✅ ALSA配置已清理并重新创建"
echo ""
echo "🧪 运行测试:"
echo "   python3 test_audio_minimal.py"
echo ""
echo "📝 如果仍有问题，可以尝试重启系统"