#!/usr/bin/env python3
"""
直接测试音频硬件设备
"""

import os
import sys
import subprocess
import tempfile
import wave
import numpy as np

def test_direct_hardware():
    """直接测试音频硬件"""
    print("🔧 直接测试音频硬件")
    print("=" * 40)
    
    # 生成测试音频文件
    print("🎵 生成测试音频文件...")
    
    sample_rate = 44100
    duration = 2.0
    frequency = 440.0
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave_data = np.sin(2 * np.pi * frequency * t) * 0.3
    audio_data = (wave_data * 32767).astype(np.int16)
    
    # 创建临时WAV文件
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    with wave.open(tmp_path, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    print(f"✅ 测试文件创建: {tmp_path}")
    
    # 测试不同的播放方式
    tests = [
        ("直接硬件设备", ["aplay", "-D", "hw:0,0", tmp_path]),
        ("默认设备", ["aplay", tmp_path]),
        ("plughw设备", ["aplay", "-D", "plughw:0,0", tmp_path]),
    ]
    
    success_count = 0
    
    for name, cmd in tests:
        print(f"\n🧪 测试 {name}...")
        print(f"   命令: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"   ✅ {name} 播放成功")
                success_count += 1
            else:
                print(f"   ❌ {name} 播放失败")
                print(f"   错误: {result.stderr.strip()}")
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ {name} 播放超时")
        except Exception as e:
            print(f"   ❌ {name} 测试异常: {e}")
    
    # 清理临时文件
    os.unlink(tmp_path)
    
    return success_count > 0

def check_audio_system():
    """检查音频系统状态"""
    print("\n🔍 检查音频系统状态")
    print("=" * 40)
    
    checks = [
        ("音频设备列表", ["aplay", "-l"]),
        ("音频卡信息", ["cat", "/proc/asound/cards"]),
        ("ALSA版本", ["aplay", "--version"]),
    ]
    
    for name, cmd in checks:
        print(f"\n📋 {name}:")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(result.stdout.strip())
            else:
                print(f"❌ 获取失败: {result.stderr.strip()}")
        except Exception as e:
            print(f"❌ 检查失败: {e}")

def enable_audio_output():
    """尝试启用音频输出"""
    print("\n🔧 尝试启用音频输出")
    print("=" * 40)
    
    # 树莓派特有的音频启用命令
    commands = [
        ("设置音频输出到耳机", ["sudo", "raspi-config", "nonint", "do_audio", "1"]),
        ("加载音频模块", ["sudo", "modprobe", "snd_bcm2835"]),
        ("设置音量", ["amixer", "set", "PCM", "80%"]),
        ("取消静音", ["amixer", "set", "PCM", "unmute"]),
    ]
    
    for name, cmd in commands:
        print(f"\n🔄 {name}...")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"   ✅ {name} 成功")
            else:
                print(f"   ⚠️  {name} 可能失败: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print(f"   ⏰ {name} 超时")
        except FileNotFoundError:
            print(f"   ⚠️  命令不存在: {cmd[0]}")
        except Exception as e:
            print(f"   ❌ {name} 异常: {e}")

def test_simple_speaker_test():
    """简单的扬声器测试"""
    print("\n🔊 简单扬声器测试")
    print("=" * 40)
    
    try:
        # 使用speaker-test命令
        print("🎵 播放测试音频 (5秒)...")
        result = subprocess.run([
            "speaker-test", 
            "-t", "sine", 
            "-f", "440", 
            "-c", "1", 
            "-s", "1",
            "-l", "1"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ speaker-test 播放成功")
            return True
        else:
            print(f"❌ speaker-test 失败: {result.stderr.strip()}")
            return False
            
    except FileNotFoundError:
        print("⚠️  speaker-test 命令不可用")
        return False
    except Exception as e:
        print(f"❌ speaker-test 异常: {e}")
        return False

if __name__ == "__main__":
    print("🔊 音频硬件直接测试")
    print("=" * 50)
    
    # 检查音频系统
    check_audio_system()
    
    # 尝试启用音频输出
    enable_audio_output()
    
    # 测试简单扬声器
    if test_simple_speaker_test():
        print("\n🎉 基础音频功能正常")
    
    # 测试直接硬件播放
    if test_direct_hardware():
        print("\n🎉 硬件音频播放成功！")
        print("💡 现在可以重新测试pygame和其他音频库")
    else:
        print("\n❌ 硬件音频播放失败")
        print("💡 可能需要:")
        print("• 检查音频线是否连接")
        print("• 确认音频输出设置")
        print("• 重启音频服务")