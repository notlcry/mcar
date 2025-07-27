#!/bin/bash
# 修复音频输入设备问题 - 专门解决麦克风无法识别的问题

echo "🔧 修复音频输入设备问题"
echo "=================================="

# 1. 检查当前音频设备状态
echo "1. 检查当前音频设备状态..."
echo "播放设备:"
aplay -l 2>/dev/null || echo "  ❌ aplay命令不可用"
echo
echo "录音设备:"
arecord -l 2>/dev/null || echo "  ❌ arecord命令不可用"
echo

# 2. 安装必要的音频工具
echo "2. 安装音频工具..."
sudo apt-get update -qq
sudo apt-get install -y alsa-utils pulseaudio pulseaudio-utils

# 3. 检查USB音频设备
echo "3. 检查USB音频设备..."
lsusb | grep -i audio
echo

# 4. 重新扫描音频设备
echo "4. 重新扫描音频设备..."
sudo alsa force-reload 2>/dev/null || echo "  alsa force-reload不可用"

# 5. 创建ALSA配置文件
echo "5. 创建ALSA配置文件..."

# 备份现有配置
if [ -f ~/.asoundrc ]; then
    cp ~/.asoundrc ~/.asoundrc.backup.$(date +%s)
    echo "  已备份现有 ~/.asoundrc"
fi

# 创建新的ALSA配置
cat > ~/.asoundrc << 'EOF'
# ALSA配置文件 - 解决树莓派音频问题

# 默认PCM设备
pcm.!default {
    type asym
    playback.pcm "playback"
    capture.pcm "capture"
}

# 播放设备配置
pcm.playback {
    type plug
    slave {
        pcm "hw:0,0"
    }
}

# 录音设备配置 - 尝试多个可能的设备
pcm.capture {
    type plug
    slave {
        pcm "hw:1,0"  # 通常USB麦克风是hw:1,0
    }
}

# 如果hw:1,0不工作，尝试hw:0,0
pcm.capture_fallback {
    type plug
    slave {
        pcm "hw:0,0"
    }
}

# 控制设备
ctl.!default {
    type hw
    card 0
}
EOF

echo "  ✅ 已创建 ~/.asoundrc"

# 6. 重启音频服务
echo "6. 重启音频服务..."
pulseaudio --kill 2>/dev/null
sleep 2
pulseaudio --start --log-target=syslog 2>/dev/null &
sleep 2

# 7. 重新加载ALSA
sudo /etc/init.d/alsa-utils restart 2>/dev/null || echo "  alsa-utils服务重启失败"

# 8. 检查修复后的状态
echo "7. 检查修复后的状态..."
echo "播放设备:"
aplay -l
echo
echo "录音设备:"
arecord -l
echo

# 9. 测试麦克风
echo "8. 测试麦克风访问..."
python3 << 'EOF'
import sys
try:
    import pyaudio
    p = pyaudio.PyAudio()
    
    print(f"PyAudio设备数量: {p.get_device_count()}")
    
    # 查找输入设备
    input_devices = []
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            input_devices.append((i, info['name'], info['maxInputChannels']))
            print(f"输入设备 {i}: {info['name']} (通道: {info['maxInputChannels']})")
    
    if input_devices:
        print("✅ 找到输入设备")
        
        # 尝试使用第一个输入设备
        device_index = input_devices[0][0]
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024
            )
            print(f"✅ 成功打开输入设备 {device_index}")
            stream.close()
        except Exception as e:
            print(f"❌ 无法打开输入设备: {e}")
    else:
        print("❌ 没有找到输入设备")
    
    p.terminate()
    
except ImportError:
    print("❌ PyAudio未安装")
    sys.exit(1)
except Exception as e:
    print(f"❌ 测试失败: {e}")
    sys.exit(1)
EOF

# 10. 创建测试脚本
echo "9. 创建音频测试脚本..."
cat > test_microphone.py << 'EOF'
#!/usr/bin/env python3
# 麦克风测试脚本

import pyaudio
import wave
import sys

def test_microphone():
    try:
        p = pyaudio.PyAudio()
        
        # 查找输入设备
        input_devices = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                input_devices.append((i, info['name']))
                print(f"设备 {i}: {info['name']}")
        
        if not input_devices:
            print("❌ 没有找到输入设备")
            return False
        
        # 使用第一个输入设备录音测试
        device_index = input_devices[0][0]
        print(f"\n使用设备 {device_index} 进行5秒录音测试...")
        
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=1024
        )
        
        frames = []
        for i in range(0, int(16000 / 1024 * 5)):  # 5秒
            data = stream.read(1024)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # 保存录音文件
        wf = wave.open("test_recording.wav", 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(16000)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        print("✅ 录音测试完成，文件保存为 test_recording.wav")
        print("可以播放这个文件来检查录音质量")
        return True
        
    except Exception as e:
        print(f"❌ 录音测试失败: {e}")
        return False

if __name__ == "__main__":
    test_microphone()
EOF

chmod +x test_microphone.py

echo
echo "=================================="
echo "🎯 修复完成！"
echo "=================================="
echo
echo "📋 下一步操作:"
echo "1. 重启系统以确保所有更改生效:"
echo "   sudo reboot"
echo
echo "2. 重启后测试麦克风:"
echo "   python3 test_microphone.py"
echo
echo "3. 如果麦克风正常，重新运行语音诊断:"
echo "   python3 diagnose_voice_issues.py"
echo
echo "4. 最后启动AI桌宠系统:"
echo "   ./start_ai_pet_quiet.sh"
echo
echo "💡 如果问题仍然存在:"
echo "• 检查USB麦克风是否正确连接"
echo "• 尝试不同的USB端口"
echo "• 检查麦克风是否在其他设备上正常工作"