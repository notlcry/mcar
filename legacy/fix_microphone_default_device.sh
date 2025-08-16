#!/bin/bash
# 修复麦克风默认设备问题

echo "🎤 修复麦克风默认设备问题"
echo "=================================="

# 1. 检查当前音频设备状态
echo "1. 检查当前音频设备状态..."
echo "录音设备:"
arecord -l 2>/dev/null || echo "  ❌ arecord不可用"
echo

# 2. 检查当前ALSA配置
echo "2. 检查当前ALSA配置..."
if [ -f ~/.asoundrc ]; then
    echo "当前 ~/.asoundrc 内容:"
    cat ~/.asoundrc
else
    echo "❌ ~/.asoundrc 不存在"
fi
echo

# 3. 创建新的ALSA配置，明确指定默认输入设备
echo "3. 创建新的ALSA配置..."

# 备份现有配置
if [ -f ~/.asoundrc ]; then
    cp ~/.asoundrc ~/.asoundrc.backup.$(date +%s)
    echo "  已备份现有配置"
fi

# 创建新配置，强制指定默认输入设备
cat > ~/.asoundrc << 'EOF'
# ALSA配置 - 修复默认输入设备问题

# 默认PCM设备
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

# 录音设备 - USB麦克风，强制指定为默认
pcm.capture_device {
    type plug
    slave {
        pcm "hw:1,0"
        rate 44100
        channels 1
        format S16_LE
    }
}

# 控制设备
ctl.!default {
    type hw
    card 0
}

# 为PyAudio提供明确的输入设备
pcm.mic {
    type plug
    slave {
        pcm "hw:1,0"
        rate 44100
        channels 1
        format S16_LE
    }
}

# 确保有一个可用的默认输入设备
pcm.dsnoop_dmixed {
    type dsnoop
    ipc_key 1234
    slave {
        pcm "hw:1,0"
        rate 44100
        channels 1
        format S16_LE
        buffer_size 8192
        period_size 1024
    }
}
EOF

echo "  ✅ 新的ALSA配置已创建"

# 4. 重启音频服务
echo "4. 重启音频服务..."
sudo systemctl stop alsa-state 2>/dev/null
pulseaudio --kill 2>/dev/null
sleep 2

sudo alsa force-reload 2>/dev/null
sleep 2

pulseaudio --start --log-target=syslog 2>/dev/null &
sleep 2

sudo systemctl start alsa-state 2>/dev/null

# 5. 测试PyAudio设备检测
echo "5. 测试PyAudio设备检测..."
python3 << 'EOF'
import pyaudio
import sys

try:
    p = pyaudio.PyAudio()
    
    print(f"PyAudio设备总数: {p.get_device_count()}")
    
    # 查找输入设备
    input_devices = []
    for i in range(p.get_device_count()):
        try:
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                input_devices.append((i, info['name'], info['maxInputChannels']))
                print(f"输入设备 {i}: {info['name']} (通道: {info['maxInputChannels']})")
        except:
            pass
    
    if input_devices:
        print(f"✅ 找到 {len(input_devices)} 个输入设备")
        
        # 尝试获取默认输入设备
        try:
            default_input = p.get_default_input_device_info()
            print(f"✅ 默认输入设备: {default_input['name']} (设备 {default_input['index']})")
        except Exception as e:
            print(f"❌ 无法获取默认输入设备: {e}")
            
            # 尝试使用第一个输入设备作为默认
            if input_devices:
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
                    print(f"✅ 可以使用设备 {device_index} 作为输入")
                    stream.close()
                except Exception as e2:
                    print(f"❌ 设备 {device_index} 也无法使用: {e2}")
    else:
        print("❌ 没有找到输入设备")
        sys.exit(1)
    
    p.terminate()
    print("✅ PyAudio测试完成")
    
except Exception as e:
    print(f"❌ PyAudio测试失败: {e}")
    sys.exit(1)
EOF

# 6. 创建麦克风测试脚本
echo "6. 创建麦克风测试脚本..."
cat > test_microphone_fix.py << 'EOF'
#!/usr/bin/env python3
# 测试麦克风修复结果

import speech_recognition as sr
import pyaudio

def test_microphone():
    print("🎤 测试麦克风修复结果")
    print("=" * 40)
    
    try:
        # 测试SpeechRecognition
        recognizer = sr.Recognizer()
        
        print("1. 测试SpeechRecognition麦克风访问...")
        with sr.Microphone() as source:
            print("✅ 麦克风访问成功")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print(f"✅ 环境噪音调整完成，阈值: {recognizer.energy_threshold}")
        
        print("\n2. 测试PyAudio直接访问...")
        p = pyaudio.PyAudio()
        
        # 查找输入设备
        input_devices = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                input_devices.append(i)
        
        if input_devices:
            device_index = input_devices[0]
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024
            )
            
            # 读取一些数据
            data = stream.read(1024, exception_on_overflow=False)
            stream.close()
            
            print(f"✅ PyAudio直接访问成功，读取了 {len(data)} 字节")
        
        p.terminate()
        
        print("\n🎉 麦克风修复成功！")
        return True
        
    except Exception as e:
        print(f"❌ 麦克风测试失败: {e}")
        return False

if __name__ == "__main__":
    test_microphone()
EOF

chmod +x test_microphone_fix.py

echo
echo "=================================="
echo "🎯 麦克风修复完成！"
echo "=================================="
echo
echo "📋 下一步操作:"
echo "1. 测试麦克风修复结果:"
echo "   python3 test_microphone_fix.py"
echo
echo "2. 如果测试成功，重启AI桌宠系统:"
echo "   停止当前系统 (Ctrl+C)"
echo "   ./start_ai_pet_quiet.sh"
echo
echo "3. 在Web界面启用AI对话模式"
echo
echo "4. 观察是否出现Vosk初始化日志"
echo
echo "💡 如果仍有问题，可能需要:"
echo "• 重启树莓派: sudo reboot"
echo "• 检查USB麦克风连接"
echo "• 尝试不同的USB端口"