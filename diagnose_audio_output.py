#!/usr/bin/env python3
"""
诊断音频输出问题
"""

import subprocess
import os

def check_audio_cards():
    """检查音频卡配置"""
    print("🔍 检查音频卡配置")
    print("=" * 40)
    
    try:
        # 检查 /proc/asound/cards
        with open('/proc/asound/cards', 'r') as f:
            cards_info = f.read()
            print("📋 /proc/asound/cards:")
            print(cards_info)
    except Exception as e:
        print(f"❌ 无法读取音频卡信息: {e}")
    
    try:
        # 检查 aplay -l
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
        print("\n📋 aplay -l 输出:")
        print(result.stdout)
        if result.stderr:
            print("错误信息:")
            print(result.stderr)
    except Exception as e:
        print(f"❌ aplay -l 失败: {e}")

def check_alsa_devices():
    """检查ALSA设备文件"""
    print("\n🔍 检查ALSA设备文件")
    print("=" * 40)
    
    snd_dir = "/dev/snd"
    if os.path.exists(snd_dir):
        print(f"📁 {snd_dir} 内容:")
        try:
            files = os.listdir(snd_dir)
            for f in sorted(files):
                full_path = os.path.join(snd_dir, f)
                stat_info = os.stat(full_path)
                print(f"  {f} - 权限: {oct(stat_info.st_mode)[-3:]}")
        except Exception as e:
            print(f"❌ 无法列出设备: {e}")
    else:
        print(f"❌ {snd_dir} 不存在")

def test_direct_device_access():
    """测试直接设备访问"""
    print("\n🧪 测试直接设备访问")
    print("=" * 40)
    
    # 可能的播放设备
    playback_devices = [
        "/dev/snd/pcmC0D0p",  # Card 0, Device 0, Playback
        "/dev/snd/pcmC0D1p",  # Card 0, Device 1, Playback
    ]
    
    for device in playback_devices:
        if os.path.exists(device):
            print(f"📱 测试设备: {device}")
            try:
                # 尝试打开设备进行写入
                with open(device, 'wb') as f:
                    print(f"  ✅ 可以打开写入")
            except PermissionError:
                print(f"  ❌ 权限不足")
            except Exception as e:
                print(f"  ❌ 打开失败: {e}")
        else:
            print(f"❌ 设备不存在: {device}")

def check_raspberry_pi_audio():
    """检查树莓派音频配置"""
    print("\n🍓 检查树莓派音频配置")
    print("=" * 40)
    
    # 检查音频输出设置
    try:
        result = subprocess.run(['raspi-config', 'nonint', 'get_audio'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            audio_setting = result.stdout.strip()
            print(f"🔊 当前音频输出设置: {audio_setting}")
            if audio_setting == "0":
                print("  ⚠️  音频输出设置为自动")
            elif audio_setting == "1":
                print("  🎧 音频输出设置为3.5mm耳机")
            elif audio_setting == "2":
                print("  📺 音频输出设置为HDMI")
        else:
            print("❌ 无法获取音频输出设置")
    except FileNotFoundError:
        print("⚠️  raspi-config 不可用（可能不是树莓派系统）")
    except Exception as e:
        print(f"❌ 检查音频设置失败: {e}")
    
    # 检查音频模块
    print("\n🔍 检查音频模块:")
    try:
        result = subprocess.run(['lsmod'], capture_output=True, text=True)
        audio_modules = []
        for line in result.stdout.split('\n'):
            if any(mod in line.lower() for mod in ['snd', 'audio', 'bcm2835']):
                audio_modules.append(line.strip())
        
        if audio_modules:
            print("📋 已加载的音频模块:")
            for module in audio_modules:
                print(f"  {module}")
        else:
            print("❌ 没有找到音频模块")
    except Exception as e:
        print(f"❌ 检查模块失败: {e}")

def try_enable_audio():
    """尝试启用音频输出"""
    print("\n🔧 尝试启用音频输出")
    print("=" * 40)
    
    commands = [
        # 设置音频输出到3.5mm耳机
        (["sudo", "raspi-config", "nonint", "do_audio", "1"], "设置音频输出到3.5mm"),
        # 加载音频模块
        (["sudo", "modprobe", "snd_bcm2835"], "加载BCM2835音频模块"),
        # 重启ALSA
        (["sudo", "alsactl", "restore"], "恢复ALSA设置"),
    ]
    
    for cmd, desc in commands:
        print(f"🔄 {desc}...")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"  ✅ 成功")
            else:
                print(f"  ⚠️  可能失败: {result.stderr.strip()}")
        except FileNotFoundError:
            print(f"  ⚠️  命令不存在: {cmd[0]}")
        except subprocess.TimeoutExpired:
            print(f"  ⏰ 超时")
        except Exception as e:
            print(f"  ❌ 异常: {e}")

def create_fixed_asoundrc():
    """创建修复的ALSA配置"""
    print("\n📝 创建修复的ALSA配置")
    print("=" * 40)
    
    # 强制使用3.5mm输出的配置
    config = """# 强制使用3.5mm音频输出
pcm.!default {
    type plug
    slave {
        pcm "hw:0,0"
        rate 44100
        channels 2
        format S16_LE
    }
}

ctl.!default {
    type hw
    card 0
}

# 单声道播放（备用）
pcm.mono {
    type plug
    slave {
        pcm "hw:0,0"
        rate 44100
        channels 1
        format S16_LE
    }
}
"""
    
    try:
        with open('.asoundrc', 'w') as f:
            f.write(config)
        print("✅ 创建了新的 .asoundrc 配置")
        
        # 也创建系统级配置
        try:
            with open('/tmp/asound.conf', 'w') as f:
                f.write(config)
            subprocess.run(['sudo', 'cp', '/tmp/asound.conf', '/etc/asound.conf'], 
                         capture_output=True)
            print("✅ 创建了系统级 /etc/asound.conf 配置")
        except:
            print("⚠️  无法创建系统级配置")
            
    except Exception as e:
        print(f"❌ 创建配置失败: {e}")

if __name__ == "__main__":
    print("🔊 音频输出问题诊断")
    print("=" * 50)
    
    # 检查音频卡
    check_audio_cards()
    
    # 检查设备文件
    check_alsa_devices()
    
    # 测试设备访问
    test_direct_device_access()
    
    # 检查树莓派配置
    check_raspberry_pi_audio()
    
    # 尝试启用音频
    try_enable_audio()
    
    # 创建修复配置
    create_fixed_asoundrc()
    
    print("\n" + "=" * 50)
    print("🎯 诊断完成")
    print("💡 建议:")
    print("1. 确保音频线已连接到3.5mm接口")
    print("2. 重启系统: sudo reboot")
    print("3. 重启后测试: aplay ~/test.wav")