#!/usr/bin/env python3
"""
音频设备检测脚本 - 详细检测所有可用的音频设备
"""

import subprocess
import os

def check_system_audio_devices():
    """检查系统级音频设备"""
    print("🔍 系统级音频设备检测")
    print("-" * 40)
    
    # 检查ALSA设备
    print("1. ALSA设备列表:")
    try:
        # 播放设备
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            print("播放设备:")
            print(result.stdout)
        else:
            print("❌ 无法获取播放设备列表")
        
        # 录音设备
        result = subprocess.run(['arecord', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            print("录音设备:")
            print(result.stdout)
        else:
            print("❌ 无法获取录音设备列表")
            
    except FileNotFoundError:
        print("❌ ALSA工具未安装")
    
    # 检查USB设备
    print("\n2. USB音频设备:")
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        if result.returncode == 0:
            usb_audio = [line for line in result.stdout.split('\n') if 'audio' in line.lower()]
            if usb_audio:
                for device in usb_audio:
                    print(f"  {device}")
            else:
                print("  ❌ 未找到USB音频设备")
        else:
            print("  ❌ 无法获取USB设备列表")
    except FileNotFoundError:
        print("  ❌ lsusb命令不可用")
    
    # 检查/proc/asound/
    print("\n3. /proc/asound/ 设备:")
    try:
        if os.path.exists('/proc/asound/cards'):
            with open('/proc/asound/cards', 'r') as f:
                content = f.read()
                if content.strip():
                    print(content)
                else:
                    print("  ❌ 没有音频卡")
        else:
            print("  ❌ /proc/asound/cards 不存在")
    except Exception as e:
        print(f"  ❌ 读取失败: {e}")

def check_pyaudio_devices():
    """检查PyAudio可见的设备"""
    print("\n🎤 PyAudio设备检测")
    print("-" * 40)
    
    try:
        import pyaudio
        
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()
        
        print(f"设备总数: {device_count}")
        print()
        
        input_devices = []
        output_devices = []
        
        for i in range(device_count):
            try:
                info = p.get_device_info_by_index(i)
                
                print(f"设备 {i}:")
                print(f"  名称: {info['name']}")
                print(f"  输入通道: {info['maxInputChannels']}")
                print(f"  输出通道: {info['maxOutputChannels']}")
                print(f"  默认采样率: {info['defaultSampleRate']}")
                print(f"  主机API: {info['hostApi']}")
                print()
                
                if info['maxInputChannels'] > 0:
                    input_devices.append((i, info['name']))
                if info['maxOutputChannels'] > 0:
                    output_devices.append((i, info['name']))
                    
            except Exception as e:
                print(f"  ❌ 设备 {i} 信息获取失败: {e}")
        
        print(f"✅ 找到 {len(input_devices)} 个输入设备")
        print(f"✅ 找到 {len(output_devices)} 个输出设备")
        
        # 尝试获取默认设备
        try:
            default_input = p.get_default_input_device_info()
            print(f"\n默认输入设备: {default_input['name']} (设备 {default_input['index']})")
        except Exception as e:
            print(f"\n❌ 无法获取默认输入设备: {e}")
        
        try:
            default_output = p.get_default_output_device_info()
            print(f"默认输出设备: {default_output['name']} (设备 {default_output['index']})")
        except Exception as e:
            print(f"❌ 无法获取默认输出设备: {e}")
        
        p.terminate()
        return input_devices, output_devices
        
    except ImportError:
        print("❌ PyAudio未安装")
        return [], []
    except Exception as e:
        print(f"❌ PyAudio检测失败: {e}")
        return [], []

def test_specific_device(device_index):
    """测试特定设备"""
    print(f"\n🧪 测试设备 {device_index}")
    print("-" * 40)
    
    try:
        import pyaudio
        
        p = pyaudio.PyAudio()
        
        # 获取设备信息
        info = p.get_device_info_by_index(device_index)
        print(f"设备名称: {info['name']}")
        print(f"输入通道: {info['maxInputChannels']}")
        
        if info['maxInputChannels'] == 0:
            print("❌ 该设备不支持输入")
            p.terminate()
            return False
        
        # 尝试打开音频流
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024
            )
            
            print("✅ 音频流打开成功")
            
            # 尝试读取一些数据
            try:
                data = stream.read(1024, exception_on_overflow=False)
                print(f"✅ 成功读取 {len(data)} 字节音频数据")
                success = True
            except Exception as e:
                print(f"❌ 读取音频数据失败: {e}")
                success = False
            
            stream.close()
            
        except Exception as e:
            print(f"❌ 无法打开音频流: {e}")
            success = False
        
        p.terminate()
        return success
        
    except Exception as e:
        print(f"❌ 设备测试失败: {e}")
        return False

def create_working_asoundrc(working_device_index):
    """为工作的设备创建.asoundrc配置"""
    print(f"\n📝 为设备 {working_device_index} 创建ALSA配置")
    print("-" * 40)
    
    # 备份现有配置
    if os.path.exists(os.path.expanduser('~/.asoundrc')):
        backup_name = f"~/.asoundrc.backup.{int(__import__('time').time())}"
        os.rename(os.path.expanduser('~/.asoundrc'), os.path.expanduser(backup_name))
        print(f"已备份现有配置到: {backup_name}")
    
    # 创建新配置
    config_content = f"""# ALSA配置 - 为设备 {working_device_index} 优化

pcm.!default {{
    type asym
    playback.pcm "playback"
    capture.pcm "capture"
}}

pcm.playback {{
    type plug
    slave {{
        pcm "hw:0,0"
    }}
}}

pcm.capture {{
    type plug
    slave {{
        pcm "hw:{working_device_index},0"
    }}
}}

ctl.!default {{
    type hw
    card 0
}}
"""
    
    with open(os.path.expanduser('~/.asoundrc'), 'w') as f:
        f.write(config_content)
    
    print("✅ 新的ALSA配置已创建")
    print("建议重启系统以使配置生效")

def main():
    print("=" * 50)
    print("🔍 详细音频设备检测")
    print("=" * 50)
    
    # 系统级检测
    check_system_audio_devices()
    
    # PyAudio检测
    input_devices, output_devices = check_pyaudio_devices()
    
    if not input_devices:
        print("\n❌ 没有找到任何输入设备")
        print("\n💡 建议:")
        print("1. 检查USB麦克风是否正确连接")
        print("2. 运行: sudo apt-get install alsa-utils pulseaudio")
        print("3. 重启系统")
        return False
    
    print(f"\n🧪 测试所有输入设备")
    print("=" * 50)
    
    working_devices = []
    
    for device_index, device_name in input_devices:
        print(f"\n测试设备 {device_index}: {device_name}")
        if test_specific_device(device_index):
            working_devices.append((device_index, device_name))
            print(f"✅ 设备 {device_index} 工作正常")
        else:
            print(f"❌ 设备 {device_index} 无法正常工作")
    
    print("\n" + "=" * 50)
    print("📊 检测结果总结")
    print("=" * 50)
    
    if working_devices:
        print(f"✅ 找到 {len(working_devices)} 个可工作的输入设备:")
        for device_index, device_name in working_devices:
            print(f"  设备 {device_index}: {device_name}")
        
        # 为第一个工作的设备创建配置
        best_device = working_devices[0][0]
        print(f"\n💡 建议使用设备 {best_device}")
        
        response = input("\n是否为该设备创建ALSA配置? (y/n): ")
        if response.lower() == 'y':
            create_working_asoundrc(best_device)
        
        return True
    else:
        print("❌ 没有找到可工作的输入设备")
        print("\n💡 故障排除建议:")
        print("1. 检查硬件连接")
        print("2. 尝试不同的USB端口")
        print("3. 检查设备权限: sudo usermod -a -G audio $USER")
        print("4. 重启系统")
        return False

if __name__ == "__main__":
    main()