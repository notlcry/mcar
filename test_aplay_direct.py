#!/usr/bin/env python3
"""
直接测试aplay调用
"""

import subprocess
import tempfile
import wave
import numpy as np
import os

def test_aplay_direct():
    """直接测试aplay调用"""
    print("🧪 直接测试aplay调用")
    print("=" * 30)
    
    # 创建测试音频文件
    test_file = "/tmp/test_aplay.wav"
    
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
    
    print(f"✅ 创建测试文件: {test_file}")
    
    # 测试不同的调用方式
    tests = [
        ("完整路径", ['/usr/bin/aplay', '-D', 'hw:0,0', test_file]),
        ("相对路径", ['aplay', '-D', 'hw:0,0', test_file]),
        ("shell=True", 'aplay -D hw:0,0 ' + test_file),
    ]
    
    for name, cmd in tests:
        print(f"\n🧪 测试 {name}:")
        print(f"   命令: {cmd}")
        
        try:
            if isinstance(cmd, str):
                # shell=True方式
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            else:
                # 列表方式
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                print(f"   ✅ {name} 成功")
                break
            else:
                print(f"   ❌ {name} 失败: {result.stderr.strip()}")
                
        except FileNotFoundError as e:
            print(f"   ❌ {name} 文件未找到: {e}")
        except subprocess.TimeoutExpired:
            print(f"   ⏰ {name} 超时")
        except Exception as e:
            print(f"   ❌ {name} 异常: {e}")
    
    # 清理
    if os.path.exists(test_file):
        os.unlink(test_file)

def test_environment():
    """测试环境变量"""
    print("\n🔍 检查环境变量")
    print("=" * 30)
    
    print(f"PATH: {os.environ.get('PATH', 'Not set')}")
    print(f"USER: {os.environ.get('USER', 'Not set')}")
    print(f"HOME: {os.environ.get('HOME', 'Not set')}")
    
    # 测试which命令
    try:
        result = subprocess.run(['which', 'aplay'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"which aplay: {result.stdout.strip()}")
        else:
            print("which aplay: 未找到")
    except:
        print("which命令不可用")

if __name__ == "__main__":
    print("🔧 aplay直接调用测试")
    print("=" * 40)
    
    test_environment()
    test_aplay_direct()