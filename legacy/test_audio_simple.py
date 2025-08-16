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
