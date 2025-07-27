#!/usr/bin/env python3
"""
测试音频输出设备
"""

import os
import sys
import pyaudio
import numpy as np
import time

def test_audio_output_devices():
    """测试音频输出设备"""
    print("🔊 检查音频输出设备")
    print("=" * 40)
    
    try:
        pa = pyaudio.PyAudio()
        
        print(f"PyAudio版本: {pyaudio.__version__}")
        print(f"设备总数: {pa.get_device_count()}")
        
        output_devices = []
        
        for i in range(pa.get_device_count()):
            try:
                info = pa.get_device_info_by_index(i)
                if info['maxOutputChannels'] > 0:
                    output_devices.append({
                        'index': i,
                        'name': info['name'],
                        'sample_rate': int(info['defaultSampleRate']),
                        'channels': info['maxOutputChannels']
                    })
                    print(f"  输出设备 {i}: {info['name']}")
                    print(f"    采样率: {info['defaultSampleRate']} Hz")
                    print(f"    通道数: {info['maxOutputChannels']}")
                    
                    # 测试设备是否可用
                    try:
                        test_stream = pa.open(
                            format=pyaudio.paInt16,
                            channels=1,
                            rate=int(info['defaultSampleRate']),
                            output=True,
                            output_device_index=i,
                            frames_per_buffer=1024
                        )
                        test_stream.close()
                        print(f"    ✅ 设备可用")
                    except Exception as e:
                        print(f"    ❌ 设备不可用: {e}")
            except Exception as e:
                print(f"  设备 {i}: 无法获取信息 - {e}")
        
        pa.terminate()
        
        if output_devices:
            print(f"\n✅ 找到 {len(output_devices)} 个输出设备")
            return output_devices
        else:
            print("\n❌ 没有找到输出设备")
            return []
            
    except Exception as e:
        print(f"❌ 音频设备检查失败: {e}")
        return []

def test_simple_audio_playback():
    """测试简单音频播放"""
    print("\n🎵 测试简单音频播放")
    print("=" * 40)
    
    # 找到可用的输出设备
    devices = test_audio_output_devices()
    if not devices:
        print("❌ 没有可用的输出设备")
        return False
    
    # 选择第一个可用设备
    device = devices[0]
    print(f"\n🔊 使用设备: {device['name']}")
    
    try:
        pa = pyaudio.PyAudio()
        
        # 生成测试音频 (440Hz正弦波，1秒)
        sample_rate = device['sample_rate']
        duration = 1.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = np.sin(2 * np.pi * frequency * t) * 0.3
        audio_data = (wave * 32767).astype(np.int16)
        
        print(f"🎵 播放测试音频 (440Hz, 1秒)...")
        
        # 创建音频流
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            output=True,
            output_device_index=device['index'],
            frames_per_buffer=1024
        )
        
        # 播放音频
        chunk_size = 1024
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            if len(chunk) < chunk_size:
                # 填充最后一个块
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)), 'constant')
            stream.write(chunk.tobytes())
        
        stream.close()
        pa.terminate()
        
        print("✅ 音频播放成功")
        return True
        
    except Exception as e:
        print(f"❌ 音频播放失败: {e}")
        return False

def test_pygame_audio():
    """测试pygame音频播放"""
    print("\n🎮 测试pygame音频播放")
    print("=" * 40)
    
    try:
        import pygame
        
        # 初始化pygame mixer
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        
        print("✅ pygame mixer初始化成功")
        
        # 生成测试音频文件
        import tempfile
        import wave
        
        # 创建临时WAV文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        # 生成440Hz正弦波
        sample_rate = 22050
        duration = 1.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave_data = np.sin(2 * np.pi * frequency * t) * 0.3
        audio_data = (wave_data * 32767).astype(np.int16)
        
        # 写入WAV文件
        with wave.open(tmp_path, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        print(f"🎵 播放测试音频...")
        
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
        
    except ImportError:
        print("❌ pygame未安装")
        return False
    except Exception as e:
        print(f"❌ pygame音频播放失败: {e}")
        return False

def check_alsa_configuration():
    """检查ALSA配置"""
    print("\n🔧 检查ALSA配置")
    print("=" * 40)
    
    # 检查.asoundrc文件
    if os.path.exists('.asoundrc'):
        print("✅ 找到.asoundrc配置文件")
        try:
            with open('.asoundrc', 'r') as f:
                content = f.read()
                print("📄 当前配置:")
                print(content)
        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
    else:
        print("⚠️  未找到.asoundrc配置文件")
    
    # 检查系统音频设备
    try:
        import subprocess
        
        print("\n🔍 系统音频设备:")
        
        # 检查ALSA设备
        try:
            result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                print("📱 ALSA播放设备:")
                print(result.stdout)
            else:
                print("❌ 无法获取ALSA设备列表")
        except FileNotFoundError:
            print("⚠️  aplay命令不可用")
        
        # 检查PulseAudio
        try:
            result = subprocess.run(['pulseaudio', '--check'], capture_output=True)
            if result.returncode == 0:
                print("✅ PulseAudio正在运行")
            else:
                print("❌ PulseAudio未运行")
        except FileNotFoundError:
            print("⚠️  PulseAudio不可用")
            
    except Exception as e:
        print(f"❌ 系统检查失败: {e}")

if __name__ == "__main__":
    print("🔊 音频输出设备诊断")
    print("=" * 50)
    
    # 检查ALSA配置
    check_alsa_configuration()
    
    # 测试PyAudio播放
    if test_simple_audio_playback():
        print("\n🎉 PyAudio播放正常")
    else:
        print("\n❌ PyAudio播放有问题")
    
    # 测试pygame播放
    if test_pygame_audio():
        print("\n🎉 pygame播放正常")
    else:
        print("\n❌ pygame播放有问题")
    
    print("\n" + "=" * 50)
    print("📊 诊断完成")
    print("💡 如果所有测试都失败，需要修复ALSA配置")