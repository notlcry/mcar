#!/bin/bash
# 修复USB麦克风配置 - 专门解决PyAudio无法识别USB麦克风的问题

echo "🎤 修复USB麦克风配置"
echo "=================================="

# 1. 确认USB麦克风存在
echo "1. 确认USB麦克风设备..."
echo "ALSA录音设备:"
arecord -l
echo
echo "USB音频设备:"
lsusb | grep -i audio
echo

# 2. 备份现有配置
echo "2. 备份现有ALSA配置..."
if [ -f ~/.asoundrc ]; then
    cp ~/.asoundrc ~/.asoundrc.backup.$(date +%s)
    echo "  已备份 ~/.asoundrc"
fi

if [ -f /etc/asound.conf ]; then
    sudo cp /etc/asound.conf /etc/asound.conf.backup.$(date +%s)
    echo "  已备份 /etc/asound.conf"
fi

# 3. 创建专门的USB麦克风配置
echo "3. 创建USB麦克风ALSA配置..."

cat > ~/.asoundrc << 'EOF'
# USB麦克风专用ALSA配置
# 解决PyAudio无法识别USB麦克风的问题

# 默认设备配置
pcm.!default {
    type asym
    playback.pcm "playback_device"
    capture.pcm "capture_device"
}

# 播放设备 - 使用树莓派内置音频
pcm.playback_device {
    type plug
    slave {
        pcm "hw:0,0"  # bcm2835 Headphones
    }
}

# 录音设备 - 使用USB麦克风
pcm.capture_device {
    type plug
    slave {
        pcm "hw:1,0"  # USB PnP Sound Device
        rate 16000
        channels 1
    }
}

# 控制设备
ctl.!default {
    type hw
    card 0
}

# 为PyAudio提供明确的设备定义
pcm.usb_mic {
    type plug
    slave {
        pcm "hw:1,0"
        rate 16000
        channels 1
        format S16_LE
    }
}

# 创建一个可被PyAudio识别的输入设备
pcm.mic {
    type dsnoop
    ipc_key 1234
    slave {
        pcm "hw:1,0"
        rate 16000
        channels 1
        format S16_LE
        buffer_size 8192
        period_size 1024
    }
}
EOF

echo "  ✅ 已创建 ~/.asoundrc"

# 4. 重启音频服务
echo "4. 重启音频服务..."
sudo systemctl stop alsa-state 2>/dev/null
pulseaudio --kill 2>/dev/null
sleep 2

# 重新加载ALSA
sudo alsa force-reload 2>/dev/null
sleep 2

# 启动PulseAudio
pulseaudio --start --log-target=syslog 2>/dev/null &
sleep 2

sudo systemctl start alsa-state 2>/dev/null

# 5. 测试USB麦克风
echo "5. 测试USB麦克风直接访问..."
echo "测试录音5秒钟..."
timeout 5s arecord -D hw:1,0 -f cd -t wav test_usb_mic.wav 2>/dev/null
if [ -f test_usb_mic.wav ]; then
    echo "✅ USB麦克风直接录音成功"
    ls -la test_usb_mic.wav
else
    echo "❌ USB麦克风直接录音失败"
fi

# 6. 创建PyAudio测试脚本
echo "6. 创建PyAudio测试脚本..."
cat > test_pyaudio_usb_mic.py << 'EOF'
#!/usr/bin/env python3
# PyAudio USB麦克风测试

import pyaudio
import wave
import sys

def test_pyaudio_with_usb_mic():
    print("🎤 PyAudio USB麦克风测试")
    print("=" * 40)
    
    try:
        p = pyaudio.PyAudio()
        
        print(f"PyAudio设备总数: {p.get_device_count()}")
        print()
        
        # 列出所有设备
        input_devices = []
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                print(f"设备 {i}: {info['name']}")
                print(f"  输入通道: {info['maxInputChannels']}")
                print(f"  输出通道: {info['maxOutputChannels']}")
                print(f"  采样率: {info['defaultSampleRate']}")
                print()
                
                if info['maxInputChannels'] > 0:
                    input_devices.append((i, info['name']))
                    
            except Exception as e:
                print(f"设备 {i}: 信息获取失败 - {e}")
        
        if not input_devices:
            print("❌ 仍然没有找到输入设备")
            
            # 尝试强制使用特定设备
            print("\n尝试强制使用USB麦克风...")
            try:
                # 直接尝试打开hw:1,0设备
                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    input_device_index=None,  # 使用默认
                    frames_per_buffer=1024
                )
                
                print("✅ 成功打开默认输入设备")
                
                # 录音测试
                print("开始5秒录音测试...")
                frames = []
                for i in range(0, int(16000 / 1024 * 5)):
                    data = stream.read(1024, exception_on_overflow=False)
                    frames.append(data)
                
                stream.stop_stream()
                stream.close()
                
                # 保存录音
                wf = wave.open("pyaudio_test.wav", 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(16000)
                wf.writeframes(b''.join(frames))
                wf.close()
                
                print("✅ PyAudio录音测试成功！文件: pyaudio_test.wav")
                return True
                
            except Exception as e:
                print(f"❌ 强制使用默认设备失败: {e}")
        else:
            print(f"✅ 找到 {len(input_devices)} 个输入设备")
            for device_index, device_name in input_devices:
                print(f"  设备 {device_index}: {device_name}")
            
            # 测试第一个输入设备
            device_index = input_devices[0][0]
            print(f"\n测试设备 {device_index}...")
            
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
                
                # 录音测试
                frames = []
                for i in range(0, int(16000 / 1024 * 3)):  # 3秒
                    data = stream.read(1024, exception_on_overflow=False)
                    frames.append(data)
                
                stream.stop_stream()
                stream.close()
                
                # 保存录音
                wf = wave.open("pyaudio_device_test.wav", 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(16000)
                wf.writeframes(b''.join(frames))
                wf.close()
                
                print("✅ 设备录音测试成功！文件: pyaudio_device_test.wav")
                return True
                
            except Exception as e:
                print(f"❌ 设备测试失败: {e}")
        
        p.terminate()
        return False
        
    except Exception as e:
        print(f"❌ PyAudio测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_pyaudio_with_usb_mic()
    if success:
        print("\n🎉 PyAudio USB麦克风配置成功！")
    else:
        print("\n❌ PyAudio USB麦克风配置仍有问题")
    sys.exit(0 if success else 1)
EOF

chmod +x test_pyaudio_usb_mic.py

# 7. 运行PyAudio测试
echo "7. 运行PyAudio测试..."
python3 test_pyaudio_usb_mic.py

echo
echo "=================================="
echo "🎯 USB麦克风修复完成！"
echo "=================================="
echo
echo "📋 测试结果文件:"
if [ -f test_usb_mic.wav ]; then
    echo "  ✅ ALSA直接录音: test_usb_mic.wav"
fi
if [ -f pyaudio_test.wav ]; then
    echo "  ✅ PyAudio录音: pyaudio_test.wav"
fi
if [ -f pyaudio_device_test.wav ]; then
    echo "  ✅ PyAudio设备录音: pyaudio_device_test.wav"
fi

echo
echo "📋 下一步操作:"
echo "1. 如果PyAudio测试成功，重新运行语音诊断:"
echo "   python3 diagnose_voice_issues.py"
echo
echo "2. 如果仍有问题，重启系统:"
echo "   sudo reboot"
echo
echo "3. 重启后再次测试:"
echo "   python3 test_pyaudio_usb_mic.py"
echo "   python3 diagnose_voice_issues.py"
echo
echo "4. 最后启动AI桌宠:"
echo "   ./start_ai_pet_quiet.sh"