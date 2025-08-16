#!/usr/bin/env python3
"""
测试修复后的音频输出
"""

import os
import sys
import time
import numpy as np

def test_pygame_audio_fixed():
    """测试修复后的pygame音频"""
    print("🎮 测试修复后的pygame音频")
    print("=" * 40)
    
    try:
        import pygame
        import tempfile
        import wave
        
        # 初始化pygame mixer
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
        pygame.mixer.init()
        
        print("✅ pygame mixer初始化成功")
        
        # 创建测试音频
        sample_rate = 44100
        duration = 2.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave_data = np.sin(2 * np.pi * frequency * t) * 0.3
        
        # 转换为立体声
        stereo_data = np.column_stack((wave_data, wave_data))
        audio_data = (stereo_data * 32767).astype(np.int16)
        
        # 创建临时WAV文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        with wave.open(tmp_path, 'w') as wav_file:
            wav_file.setnchannels(2)  # 立体声
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        print(f"🎵 播放测试音频 (440Hz, 2秒, 立体声)...")
        
        # 播放音频
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        
        # 等待播放完成
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        pygame.mixer.quit()
        os.unlink(tmp_path)
        
        print("✅ pygame音频播放成功")
        return True
        
    except Exception as e:
        print(f"❌ pygame音频播放失败: {e}")
        return False

def test_edge_tts_playback():
    """测试edge-tts语音合成播放"""
    print("\n🗣️  测试edge-tts语音合成")
    print("=" * 40)
    
    try:
        import edge_tts
        import asyncio
        import pygame
        import tempfile
        
        async def generate_speech():
            text = "你好，我是AI桌宠，语音输出测试成功！"
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
            
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            await communicate.save(tmp_path)
            return tmp_path
        
        print("🔄 生成语音...")
        audio_file = asyncio.run(generate_speech())
        
        print("🎵 播放语音...")
        
        # 初始化pygame
        pygame.mixer.init()
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
        
        # 等待播放完成
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        pygame.mixer.quit()
        os.unlink(audio_file)
        
        print("✅ edge-tts语音合成播放成功")
        return True
        
    except ImportError:
        print("❌ edge-tts未安装，跳过测试")
        print("💡 安装命令: pip install edge-tts")
        return False
    except Exception as e:
        print(f"❌ edge-tts测试失败: {e}")
        return False

def test_pyttsx3_playback():
    """测试pyttsx3语音合成"""
    print("\n🗣️  测试pyttsx3语音合成")
    print("=" * 40)
    
    try:
        import pyttsx3
        
        engine = pyttsx3.init()
        
        # 设置语音参数
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.8)
        
        # 尝试设置中文语音
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                engine.setProperty('voice', voice.id)
                break
        
        text = "你好，我是AI桌宠，pyttsx3语音测试成功！"
        print(f"🎵 播放语音: {text}")
        
        engine.say(text)
        engine.runAndWait()
        
        print("✅ pyttsx3语音合成成功")
        return True
        
    except ImportError:
        print("❌ pyttsx3未安装，跳过测试")
        print("💡 安装命令: pip install pyttsx3")
        return False
    except Exception as e:
        print(f"❌ pyttsx3测试失败: {e}")
        return False

def test_system_audio():
    """测试系统音频命令"""
    print("\n🔊 测试系统音频命令")
    print("=" * 40)
    
    try:
        import subprocess
        
        # 测试aplay
        try:
            # 生成测试音频文件
            import tempfile
            import wave
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # 生成简单的测试音频
            sample_rate = 44100
            duration = 1.0
            frequency = 440.0
            
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            wave_data = np.sin(2 * np.pi * frequency * t) * 0.3
            audio_data = (wave_data * 32767).astype(np.int16)
            
            with wave.open(tmp_path, 'w') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.tobytes())
            
            print("🎵 使用aplay播放测试音频...")
            result = subprocess.run(['aplay', tmp_path], capture_output=True, text=True)
            
            os.unlink(tmp_path)
            
            if result.returncode == 0:
                print("✅ aplay播放成功")
                return True
            else:
                print(f"❌ aplay播放失败: {result.stderr}")
                return False
                
        except FileNotFoundError:
            print("❌ aplay命令不可用")
            return False
            
    except Exception as e:
        print(f"❌ 系统音频测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🔊 修复后的音频输出测试")
    print("=" * 50)
    
    results = []
    
    # 测试pygame
    results.append(("pygame", test_pygame_audio_fixed()))
    
    # 测试edge-tts
    results.append(("edge-tts", test_edge_tts_playback()))
    
    # 测试pyttsx3
    results.append(("pyttsx3", test_pyttsx3_playback()))
    
    # 测试系统音频
    results.append(("aplay", test_system_audio()))
    
    print("\n" + "=" * 50)
    print("📊 测试结果总结:")
    
    success_count = 0
    for name, success in results:
        if success:
            print(f"✅ {name}: 成功")
            success_count += 1
        else:
            print(f"❌ {name}: 失败")
    
    print(f"\n📈 成功率: {success_count}/{len(results)}")
    
    if success_count > 0:
        print("🎉 音频输出修复成功！")
        print("💡 现在可以使用语音合成功能了")
    else:
        print("❌ 音频输出仍有问题，需要进一步调试")