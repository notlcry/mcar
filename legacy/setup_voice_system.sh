#!/bin/bash
# AI桌宠语音系统统一配置脚本
# 这个脚本会被集成到主安装流程中

echo "🎤 AI桌宠语音系统配置"
echo "=================================="

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then
    echo "❌ 请不要以root用户运行此脚本"
    exit 1
fi

# 1. 安装必要的系统包
echo "1. 安装音频系统依赖..."
sudo apt-get update -qq
sudo apt-get install -y \
    alsa-utils \
    pulseaudio \
    pulseaudio-utils \
    libsdl2-mixer-2.0-0 \
    libsdl2-mixer-dev \
    python3-pyaudio \
    portaudio19-dev

# 2. 安装Python语音识别库
echo "2. 安装Python语音识别库..."
pip3 install --upgrade \
    SpeechRecognition \
    pyaudio \
    vosk \
    pvporcupine \
    pygame \
    edge-tts

# 3. 下载Vosk中文模型（如果不存在）
echo "3. 配置Vosk中文模型..."
if [ ! -d "models/vosk-model-small-cn-0.22" ]; then
    echo "  下载Vosk小型中文模型..."
    mkdir -p models
    cd models
    
    if command -v wget >/dev/null 2>&1; then
        wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip
    elif command -v curl >/dev/null 2>&1; then
        curl -L -O https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip
    else
        echo "  ❌ 需要wget或curl来下载模型"
        cd ..
        exit 1
    fi
    
    if [ -f "vosk-model-small-cn-0.22.zip" ]; then
        unzip -q vosk-model-small-cn-0.22.zip
        rm vosk-model-small-cn-0.22.zip
        echo "  ✅ Vosk中文模型下载完成"
    else
        echo "  ❌ 模型下载失败"
        cd ..
        exit 1
    fi
    
    cd ..
else
    echo "  ✅ Vosk中文模型已存在"
fi

# 4. 配置ALSA音频系统
echo "4. 配置ALSA音频系统..."

# 备份现有配置
if [ -f ~/.asoundrc ]; then
    cp ~/.asoundrc ~/.asoundrc.backup.$(date +%s)
    echo "  已备份现有ALSA配置"
fi

# 创建可靠的ALSA配置
cat > ~/.asoundrc << 'EOF'
# AI桌宠ALSA配置
# 自动检测USB麦克风并配置为默认输入设备

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

# 录音设备 - USB麦克风
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

# 为语音识别优化的设备
pcm.voice_input {
    type plug
    slave {
        pcm "hw:1,0"
        rate 16000
        channels 1
        format S16_LE
    }
}
EOF

echo "  ✅ ALSA配置已创建"

# 5. 配置用户权限
echo "5. 配置用户权限..."
sudo usermod -a -G audio,gpio,i2c,spi,dialout $USER
echo "  ✅ 用户权限已配置"

# 6. 创建systemd服务（可选）
echo "6. 创建系统服务..."
sudo tee /etc/systemd/system/ai-desktop-pet.service > /dev/null << EOF
[Unit]
Description=AI Desktop Pet Voice System
After=network.target sound.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/.venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$(pwd)/start_ai_pet_quiet.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "  ✅ 系统服务已创建"

# 7. 重启音频服务
echo "7. 重启音频服务..."
sudo systemctl stop alsa-state 2>/dev/null
pulseaudio --kill 2>/dev/null
sleep 2
sudo alsa force-reload 2>/dev/null
sleep 2
pulseaudio --start --log-target=syslog 2>/dev/null &
sleep 2
sudo systemctl start alsa-state 2>/dev/null

# 8. 测试配置
echo "8. 测试语音系统配置..."
python3 << 'EOF'
import sys
import os
sys.path.insert(0, 'src')

def test_voice_system():
    try:
        # 测试基础语音识别
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        print("✅ 基础语音识别正常")
        
        # 测试Vosk
        from vosk_recognizer import VoskRecognizer
        vosk_rec = VoskRecognizer()
        
        if vosk_rec.is_available:
            print("✅ Vosk中文识别正常")
        else:
            print("⚠️  Vosk中文识别不可用")
        
        # 测试Porcupine（如果有API密钥）
        if os.getenv('PICOVOICE_ACCESS_KEY'):
            import pvporcupine
            porcupine = pvporcupine.create(
                access_key=os.getenv('PICOVOICE_ACCESS_KEY'),
                keywords=['picovoice']
            )
            porcupine.delete()
            print("✅ Porcupine唤醒词正常")
        else:
            print("⚠️  Porcupine需要API密钥")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

# 加载环境变量
try:
    with open('.ai_pet_env', 'r') as f:
        for line in f:
            if line.startswith('export ') and '=' in line:
                line = line.replace('export ', '').strip()
                key, value = line.split('=', 1)
                value = value.strip('"')
                os.environ[key] = value
except:
    pass

if test_voice_system():
    print("🎉 语音系统配置成功！")
else:
    print("❌ 语音系统配置失败")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo
    echo "=================================="
    echo "🎉 AI桌宠语音系统配置完成！"
    echo "=================================="
    echo
    echo "📋 配置总结:"
    echo "✅ 音频系统依赖已安装"
    echo "✅ Python语音识别库已安装"
    echo "✅ Vosk中文模型已配置"
    echo "✅ ALSA音频系统已配置"
    echo "✅ 用户权限已设置"
    echo "✅ 系统服务已创建"
    echo
    echo "🚀 启动方式:"
    echo "• 手动启动: ./start_ai_pet_quiet.sh"
    echo "• 服务启动: sudo systemctl start ai-desktop-pet"
    echo "• 开机自启: sudo systemctl enable ai-desktop-pet"
    echo
    echo "🌐 Web界面: http://你的树莓派IP:5000"
    echo
    echo "💡 注意: 建议重启系统以确保所有配置生效"
    echo "   sudo reboot"
else
    echo
    echo "❌ 配置过程中出现错误"
    echo "请检查错误信息并重新运行"
fi