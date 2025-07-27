#!/usr/bin/env python3
"""
测试和修复音频权限
"""

import os
import subprocess
import stat

def check_audio_device_permissions():
    """检查音频设备权限"""
    print("🔍 检查音频设备权限")
    print("=" * 40)
    
    # 检查关键音频设备
    devices = [
        "/dev/snd",
        "/dev/snd/controlC0",
        "/dev/snd/pcmC0D0p",  # 播放设备
        "/dev/snd/pcmC1D0c",  # 录音设备
    ]
    
    for device in devices:
        if os.path.exists(device):
            stat_info = os.stat(device)
            mode = stat.filemode(stat_info.st_mode)
            uid = stat_info.st_uid
            gid = stat_info.st_gid
            
            print(f"📱 {device}:")
            print(f"   权限: {mode}")
            print(f"   UID: {uid}, GID: {gid}")
            
            # 检查当前用户是否有访问权限
            if os.access(device, os.R_OK | os.W_OK):
                print(f"   ✅ 当前用户有读写权限")
            else:
                print(f"   ❌ 当前用户无读写权限")
        else:
            print(f"❌ {device} 不存在")

def test_direct_device_access():
    """直接测试设备访问"""
    print("\n🧪 直接测试设备访问")
    print("=" * 40)
    
    # 测试播放设备
    playback_device = "/dev/snd/pcmC0D0p"
    if os.path.exists(playback_device):
        print(f"🔊 测试播放设备: {playback_device}")
        try:
            # 尝试打开设备
            with open(playback_device, 'wb') as f:
                print("✅ 播放设备可以打开")
                # 写入一些测试数据
                test_data = b'\x00' * 1024
                f.write(test_data)
                print("✅ 播放设备可以写入")
        except PermissionError:
            print("❌ 播放设备权限不足")
        except Exception as e:
            print(f"❌ 播放设备访问失败: {e}")
    else:
        print(f"❌ 播放设备不存在: {playback_device}")

def fix_permissions_immediate():
    """立即修复权限（临时方案）"""
    print("\n🔧 立即修复权限")
    print("=" * 40)
    
    commands = [
        # 修复设备权限
        ["sudo", "chmod", "666", "/dev/snd/*"],
        # 添加用户到audio组
        ["sudo", "usermod", "-a", "-G", "audio", os.getenv("USER", "barry")],
        # 重新加载udev规则
        ["sudo", "udevadm", "control", "--reload-rules"],
        ["sudo", "udevadm", "trigger"],
    ]
    
    for cmd in commands:
        print(f"🔄 执行: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("   ✅ 成功")
            else:
                print(f"   ⚠️  可能失败: {result.stderr.strip()}")
        except Exception as e:
            print(f"   ❌ 执行失败: {e}")

def test_with_sudo():
    """使用sudo测试音频播放"""
    print("\n🔧 使用sudo测试音频播放")
    print("=" * 40)
    
    # 创建测试音频文件
    import tempfile
    import wave
    import numpy as np
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    # 生成测试音频
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
    
    print(f"🎵 测试文件: {tmp_path}")
    
    # 使用sudo测试播放
    test_commands = [
        ["sudo", "aplay", tmp_path],
        ["sudo", "aplay", "-D", "hw:0,0", tmp_path],
        ["sudo", "aplay", "-D", "plughw:0,0", tmp_path],
    ]
    
    success = False
    for cmd in test_commands:
        print(f"🧪 测试: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("   ✅ sudo播放成功！")
                success = True
                break
            else:
                print(f"   ❌ 失败: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print("   ⏰ 超时")
        except Exception as e:
            print(f"   ❌ 异常: {e}")
    
    # 清理
    os.unlink(tmp_path)
    
    if success:
        print("\n🎉 sudo可以播放音频，确认是权限问题！")
        return True
    else:
        print("\n❌ 即使sudo也无法播放，可能是硬件问题")
        return False

def create_audio_test_script():
    """创建音频测试脚本"""
    print("\n📝 创建音频测试脚本")
    print("=" * 40)
    
    script_content = '''#!/bin/bash
# 音频权限快速修复脚本

echo "🔧 快速修复音频权限..."

# 修复设备权限
sudo chmod 666 /dev/snd/* 2>/dev/null

# 添加用户到audio组
sudo usermod -a -G audio $USER

# 应用新的组权限（不需要重新登录）
exec sg audio -c "$0 test"

if [ "$1" = "test" ]; then
    echo "🧪 测试音频播放..."
    
    # 创建测试音频
    python3 -c "
import wave, numpy as np
t = np.linspace(0, 1, 44100, False)
data = (np.sin(2*np.pi*440*t) * 0.3 * 32767).astype(np.int16)
with wave.open('/tmp/test_audio.wav', 'w') as f:
    f.setnchannels(1)
    f.setsampwidth(2) 
    f.setframerate(44100)
    f.writeframes(data.tobytes())
"
    
    # 测试播放
    if aplay /tmp/test_audio.wav 2>/dev/null; then
        echo "✅ 音频播放成功！"
        rm -f /tmp/test_audio.wav
        exit 0
    else
        echo "❌ 音频播放仍然失败"
        rm -f /tmp/test_audio.wav
        exit 1
    fi
fi
'''
    
    with open('quick_audio_fix.sh', 'w') as f:
        f.write(script_content)
    
    os.chmod('quick_audio_fix.sh', 0o755)
    print("✅ 创建了 quick_audio_fix.sh")
    print("💡 运行: ./quick_audio_fix.sh")

if __name__ == "__main__":
    print("🔧 音频权限诊断和修复")
    print("=" * 50)
    
    # 检查权限
    check_audio_device_permissions()
    
    # 测试设备访问
    test_direct_device_access()
    
    # 使用sudo测试
    if test_with_sudo():
        print("\n🎯 确认是权限问题！")
        
        # 立即修复权限
        fix_permissions_immediate()
        
        # 创建快速修复脚本
        create_audio_test_script()
        
        print("\n💡 解决方案:")
        print("1. 运行: ./quick_audio_fix.sh")
        print("2. 或者重新登录系统")
        print("3. 然后测试: python3 test_audio_output_fixed.py")
    else:
        print("\n❌ 不仅仅是权限问题，可能需要检查硬件配置")