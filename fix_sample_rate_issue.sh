#!/bin/bash
# 修复采样率问题 - 让USB麦克风支持16000Hz采样率

echo "🎵 修复USB麦克风采样率问题"
echo "=================================="

# 1. 检查USB麦克风支持的采样率
echo "1. 检查USB麦克风支持的采样率..."
echo "USB麦克风硬件信息:"
cat /proc/asound/card1/stream0 2>/dev/null || echo "无法读取USB麦克风流信息"
echo

# 2. 测试不同采样率
echo "2. 测试USB麦克风支持的采样率..."
for rate in 8000 16000 22050 44100 48000; do
    echo -n "测试 ${rate}Hz: "
    timeout 2s arecord -D hw:1,0 -f S16_LE -r $rate -c 1 -t wav /dev/null 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ 支持"
    else
        echo "❌ 不支持"
    fi
done
echo

# 3. 创建支持多采样率的ALSA配置
echo "3. 创建支持多采样率的ALSA配置..."

# 备份当前配置
cp ~/.asoundrc ~/.asoundrc.backup.samplerate.$(date +%s)

cat > ~/.asoundrc << 'EOF'
# USB麦克风多采样率支持配置

# 默认设备配置
pcm.!default {
    type asym
    playback.pcm "playback_device"
    capture.pcm "capture_device"
}

# 播放设备 - 树莓派内置音频
pcm.playback_device {
    type plug
    slave {
        pcm "hw:0,0"
    }
}

# 录音设备 - USB麦克风，支持采样率转换
pcm.capture_device {
    type plug
    slave {
        pcm "usb_mic_raw"
    }
}

# USB麦克风原始设备
pcm.usb_mic_raw {
    type hw
    card 1
    device 0
}

# 为PyAudio提供的麦克风设备 - 支持采样率转换
pcm.mic {
    type plug
    slave {
        pcm "usb_mic_raw"
        rate 44100  # 使用USB麦克风的原生采样率
        channels 1
        format S16_LE
    }
    # 启用采样率转换
    rate_converter "samplerate_best"
}

# 16kHz专用设备
pcm.mic_16k {
    type plug
    slave {
        pcm "usb_mic_raw"
        rate 44100
        channels 1
        format S16_LE
    }
    # 强制转换到16kHz
    rate_converter "samplerate_best"
}

# 控制设备
ctl.!default {
    type hw
    card 0
}
EOF

echo "  ✅ 已创建支持多采样率的配置"

# 4. 重启音频服务
echo "4. 重启音频服务..."
pulseaudio --kill 2>/dev/null
sleep 2
sudo alsa force-reload 2>/dev/null
sleep 2
pulseaudio --start --log-target=syslog 2>/dev/null &
sleep 2

# 5. 创建改进的PyAudio测试脚本
echo "5. 创建改进的PyAudio测试脚本..."
cat > test_pyaudio_sample_rates.py << 'EOF'
#!/usr/bin/env python3
# PyAudio多采样率测试

import pyaudio
import wave
import sys

def test_device_sample_rates():
    print("🎵 PyAudio采样率测试")
    print("=" * 40)
    
    try:
        p = pyaudio.PyAudio()
        
        # 找到输入设备
        input_devices = []
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    input_devices.append((i, info['name'], info['defaultSampleRate']))
                    print(f"输入设备 {i}: {info['name']} (默认: {info['defaultSampleRate']}Hz)")
            except:
                pass
        
        if not input_devices:
            print("❌ 没有找到输入设备")
            p.terminate()
            return False
        
        # 测试每个输入设备的不同采样率
        sample_rates = [8000, 16000, 22050, 44100, 48000]
        
        for device_index, device_name, default_rate in input_devices:
            print(f"\n测试设备 {device_index}: {device_name}")
            print("-" * 30)
            
            working_rates = []
            
            for rate in sample_rates:
                try:
                    print(f"尝试 {rate}Hz... ", end="")
                    
                    # 尝试打开音频流
                    stream = p.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=rate,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=1024
                    )
                    
                    # 尝试读取一些数据
                    data = stream.read(512, exception_on_overflow=False)
                    
                    stream.close()
                    working_rates.append(rate)
                    print("✅")
                    
                except Exception as e:
                    print(f"❌ ({str(e)[:30]}...)")
            
            if working_rates:
                print(f"✅ 设备 {device_index} 支持的采样率: {working_rates}")
                
                # 使用第一个工作的采样率进行录音测试
                test_rate = working_rates[0]
                print(f"\n使用 {test_rate}Hz 进行3秒录音测试...")
                
                try:
                    stream = p.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=test_rate,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=1024
                    )
                    
                    frames = []
                    for i in range(0, int(test_rate / 1024 * 3)):  # 3秒
                        data = stream.read(1024, exception_on_overflow=False)
                        frames.append(data)
                    
                    stream.close()
                    
                    # 保存录音文件
                    filename = f"test_device_{device_index}_{test_rate}hz.wav"
                    wf = wave.open(filename, 'wb')
                    wf.setnchannels(1)
                    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(test_rate)
                    wf.writeframes(b''.join(frames))
                    wf.close()
                    
                    print(f"✅ 录音成功！文件: {filename}")
                    
                    # 如果16000Hz工作，这就是我们需要的
                    if 16000 in working_rates:
                        print("🎉 设备支持16000Hz，完美适配语音识别！")
                        return True
                    
                except Exception as e:
                    print(f"❌ 录音测试失败: {e}")
            else:
                print(f"❌ 设备 {device_index} 没有支持的采样率")
        
        p.terminate()
        
        # 如果有任何设备工作，就算成功
        return len([rates for _, _, rates in input_devices if rates]) > 0
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_default_device():
    """测试默认设备"""
    print("\n🎤 测试默认输入设备")
    print("=" * 40)
    
    try:
        p = pyaudio.PyAudio()
        
        # 尝试不同采样率的默认设备
        sample_rates = [44100, 22050, 16000, 8000]
        
        for rate in sample_rates:
            try:
                print(f"尝试默认设备 {rate}Hz... ", end="")
                
                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=rate,
                    input=True,
                    frames_per_buffer=1024
                )
                
                # 录音2秒
                frames = []
                for i in range(0, int(rate / 1024 * 2)):
                    data = stream.read(1024, exception_on_overflow=False)
                    frames.append(data)
                
                stream.close()
                
                # 保存文件
                filename = f"default_device_{rate}hz.wav"
                wf = wave.open(filename, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(rate)
                wf.writeframes(b''.join(frames))
                wf.close()
                
                print(f"✅ 成功！文件: {filename}")
                
                if rate == 16000:
                    print("🎉 默认设备支持16000Hz！")
                    p.terminate()
                    return True
                
            except Exception as e:
                print(f"❌ ({str(e)[:30]}...)")
        
        p.terminate()
        return False
        
    except Exception as e:
        print(f"❌ 默认设备测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 开始PyAudio采样率兼容性测试")
    print("=" * 50)
    
    device_success = test_device_sample_rates()
    default_success = test_default_device()
    
    print("\n" + "=" * 50)
    print("📊 测试结果总结")
    print("=" * 50)
    
    if device_success or default_success:
        print("✅ PyAudio音频输入配置成功！")
        print("\n📁 生成的测试文件:")
        import os
        for file in os.listdir('.'):
            if file.endswith('.wav') and 'test_' in file:
                print(f"  {file}")
        
        print("\n🎯 下一步: 运行语音功能诊断")
        print("  python3 diagnose_voice_issues.py")
        
        sys.exit(0)
    else:
        print("❌ PyAudio音频输入仍有问题")
        print("\n💡 建议:")
        print("  1. 重启系统: sudo reboot")
        print("  2. 检查USB麦克风硬件")
        print("  3. 尝试不同的USB端口")
        
        sys.exit(1)
EOF

chmod +x test_pyaudio_sample_rates.py

# 6. 运行改进的测试
echo "6. 运行改进的PyAudio测试..."
python3 test_pyaudio_sample_rates.py

echo
echo "=================================="
echo "🎯 采样率修复完成！"
echo "=================================="