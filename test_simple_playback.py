#!/usr/bin/env python3
"""
简化的音频播放测试
"""

import os
import subprocess
import tempfile
import wave
import numpy as np

def test_aplay_basic():
    """测试基础aplay功能"""
    print("🎵 测试基础aplay功能")
    print("=" * 40)
    
    # 创建测试音频文件（在用户目录）
    test_file = os.path.expanduser("~/test_playback.wav")
    
    # 生成测试音频
    sample_rate = 44100
    duration = 2.0
    frequency = 440.0
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave_data = np.sin(2 * np.pi * frequency * t) * 0.3
    audio_data = (wave_data * 32767).astype(np.int16)
    
    # 写入WAV文件
    with wave.open(test_file, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    print(f"✅ 创建测试文件: {test_file}")
    
    # 测试不同的播放方式
    tests = [
        ("默认设备", ["aplay", test_file]),
        ("硬件设备", ["aplay", "-D", "hw:0,0", test_file]),
        ("插件设备", ["aplay", "-D", "plughw:0,0", test_file]),
    ]
    
    success_count = 0
    working_device = None
    
    for name, cmd in tests:
        print(f"\n🧪 测试 {name}...")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"   ✅ {name} 播放成功")
                success_count += 1
                if working_device is None:
                    working_device = cmd[1:3] if len(cmd) > 2 else ["default"]
            else:
                print(f"   ❌ {name} 失败: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print(f"   ⏰ {name} 超时")
        except Exception as e:
            print(f"   ❌ {name} 异常: {e}")
    
    # 清理
    if os.path.exists(test_file):
        os.unlink(test_file)
    
    return success_count > 0, working_device

def test_pygame_with_working_device(working_device):
    """使用可工作的设备测试pygame"""
    print(f"\n🎮 使用可工作设备测试pygame")
    print("=" * 40)
    
    try:
        import pygame
        import os
        
        # 设置SDL音频驱动
        if working_device and len(working_device) > 1:
            # 如果有特定设备，尝试设置环境变量
            os.environ['SDL_AUDIODRIVER'] = 'alsa'
            print(f"🔧 设置音频驱动: ALSA")
        
        # 初始化pygame
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=1, buffer=1024)
        pygame.mixer.init()
        
        print("✅ pygame初始化成功")
        
        # 创建测试音频文件
        test_file = os.path.expanduser("~/pygame_test.wav")
        
        sample_rate = 44100
        duration = 2.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave_data = np.sin(2 * np.pi * frequency * t) * 0.3
        audio_data = (wave_data * 32767).astype(np.int16)
        
        with wave.open(test_file, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        print(f"🎵 播放测试音频...")
        
        # 播放音频
        pygame.mixer.music.load(test_file)
        pygame.mixer.music.play()
        
        # 等待播放完成
        import time
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        pygame.mixer.quit()
        os.unlink(test_file)
        
        print("✅ pygame播放成功")
        return True
        
    except Exception as e:
        print(f"❌ pygame播放失败: {e}")
        return False

def test_pyaudio_playback():
    """测试PyAudio播放"""
    print(f"\n🎤 测试PyAudio播放")
    print("=" * 40)
    
    try:
        import pyaudio
        
        # 生成测试音频
        sample_rate = 44100
        duration = 2.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave_data = np.sin(2 * np.pi * frequency * t) * 0.3
        audio_data = (wave_data * 32767).astype(np.int16)
        
        print("🎵 PyAudio播放测试音频...")
        
        # 创建PyAudio实例
        pa = pyaudio.PyAudio()
        
        # 打开音频流
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            output=True,
            frames_per_buffer=1024
        )
        
        # 播放音频
        chunk_size = 1024
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            if len(chunk) < chunk_size:
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)), 'constant')
            stream.write(chunk.tobytes())
        
        stream.close()
        pa.terminate()
        
        print("✅ PyAudio播放成功")
        return True
        
    except Exception as e:
        print(f"❌ PyAudio播放失败: {e}")
        return False

if __name__ == "__main__":
    print("🔊 简化音频播放测试")
    print("=" * 50)
    
    # 测试基础播放
    aplay_works, working_device = test_aplay_basic()
    
    if aplay_works:
        print(f"\n🎉 基础音频播放正常！")
        print(f"可工作的设备: {working_device}")
        
        # 测试PyAudio
        pyaudio_works = test_pyaudio_playback()
        
        # 测试pygame
        pygame_works = test_pygame_with_working_device(working_device)
        
        print(f"\n📊 测试结果:")
        print(f"• aplay: ✅ 成功")
        print(f"• PyAudio: {'✅ 成功' if pyaudio_works else '❌ 失败'}")
        print(f"• pygame: {'✅ 成功' if pygame_works else '❌ 失败'}")
        
        if pyaudio_works or pygame_works:
            print(f"\n🎉 Python音频库可以工作！")
            print(f"💡 现在可以使用语音合成功能")
        else:
            print(f"\n⚠️  基础播放正常，但Python库有问题")
            print(f"💡 可能需要重新配置Python音频库")
    else:
        print(f"\n❌ 基础音频播放失败")
        print(f"💡 需要检查音频硬件配置")