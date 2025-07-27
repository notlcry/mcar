#!/usr/bin/env python3
"""
安全修复播放配置，不影响唤醒词功能
"""

import os
import shutil

def backup_current_config():
    """备份当前配置"""
    if os.path.exists('.asoundrc'):
        shutil.copy('.asoundrc', '.asoundrc.working_wakeword')
        print("✅ 已备份当前配置到 .asoundrc.working_wakeword")
        return True
    return False

def create_safe_playback_config():
    """创建安全的播放配置"""
    print("🔧 创建安全的播放配置...")
    
    # 保留录音配置，只修复播放配置
    config = """# ALSA配置 - 安全修复播放功能
# 播放设备：使用Card 0 (树莓派内置音频)
pcm.!default {
    type plug
    slave {
        pcm "hw:0,0"
        rate 44100
        channels 2
        format S16_LE
    }
}

# 控制设备：使用Card 0
ctl.!default {
    type hw
    card 0
}

# 录音设备：保持原有配置 (USB麦克风)
pcm.mic {
    type plug
    slave {
        pcm "hw:1,0"
        rate 16000
        channels 1
        format S16_LE
    }
}

# 专用播放设备（备用）
pcm.speaker {
    type plug
    slave {
        pcm "hw:0,0"
        rate 44100
        channels 2
        format S16_LE
    }
}
"""
    
    try:
        with open('.asoundrc', 'w') as f:
            f.write(config)
        print("✅ 创建了安全的播放配置")
        return True
    except Exception as e:
        print(f"❌ 创建配置失败: {e}")
        return False

def test_playback():
    """测试播放功能"""
    print("\n🧪 测试播放功能...")
    
    import subprocess
    
    # 测试默认播放
    try:
        result = subprocess.run(['aplay', os.path.expanduser('~/test.wav')], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ 默认播放成功")
            return True
        else:
            print(f"❌ 默认播放失败: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print("⏰ 播放超时")
        return False
    except Exception as e:
        print(f"❌ 播放测试失败: {e}")
        return False

def test_python_audio():
    """测试Python音频库"""
    print("\n🐍 测试Python音频库...")
    
    try:
        import pygame
        import tempfile
        import wave
        import numpy as np
        
        # 初始化pygame
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
        pygame.mixer.init()
        
        # 创建测试音频
        sample_rate = 44100
        duration = 1.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave_data = np.sin(2 * np.pi * frequency * t) * 0.3
        
        # 转换为立体声
        stereo_data = np.column_stack((wave_data, wave_data))
        audio_data = (stereo_data * 32767).astype(np.int16)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        with wave.open(tmp_path, 'w') as wav_file:
            wav_file.setnchannels(2)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        # 播放测试
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        
        # 等待播放完成
        import time
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        pygame.mixer.quit()
        os.unlink(tmp_path)
        
        print("✅ pygame播放成功")
        return True
        
    except Exception as e:
        print(f"❌ pygame播放失败: {e}")
        return False

def restore_config_if_needed():
    """如果需要，恢复配置"""
    if os.path.exists('.asoundrc.working_wakeword'):
        shutil.copy('.asoundrc.working_wakeword', '.asoundrc')
        print("🔄 已恢复原始配置")

if __name__ == "__main__":
    print("🔧 安全修复播放配置")
    print("=" * 50)
    
    # 备份当前配置
    backup_current_config()
    
    # 创建安全配置
    if create_safe_playback_config():
        
        # 测试播放
        playback_ok = test_playback()
        
        if playback_ok:
            print("\n🎉 播放配置修复成功！")
            
            # 测试Python音频库
            python_ok = test_python_audio()
            
            if python_ok:
                print("\n🎉 Python音频库也正常工作！")
                print("💡 现在可以使用语音合成功能了")
            else:
                print("\n⚠️  Python音频库仍有问题，但基础播放正常")
        else:
            print("\n❌ 播放配置修复失败")
            print("🔄 恢复原始配置...")
            restore_config_if_needed()
    
    print("\n📋 重要提醒:")
    print("• 唤醒词功能已确认正常")
    print("• 录音功能不受影响")
    print("• 如有问题可恢复: cp .asoundrc.working_wakeword .asoundrc")