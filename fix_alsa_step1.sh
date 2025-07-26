#!/bin/bash
# 第一步：修复ALSA音频配置
# 针对树莓派 + USB麦克风的配置

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 备份现有配置
backup_existing_config() {
    log_step "备份现有ALSA配置..."
    
    if [[ -f ~/.asoundrc ]]; then
        cp ~/.asoundrc ~/.asoundrc.backup.$(date +%Y%m%d_%H%M%S)
        log_info "已备份 ~/.asoundrc"
    fi
    
    if [[ -f /etc/asound.conf ]]; then
        sudo cp /etc/asound.conf /etc/asound.conf.backup.$(date +%Y%m%d_%H%M%S)
        log_info "已备份 /etc/asound.conf"
    fi
}

# 创建针对你的硬件配置的ALSA配置
create_alsa_config() {
    log_step "创建ALSA配置文件..."
    
    # 根据你的设备创建配置
    cat > ~/.asoundrc << 'EOF'
# ALSA配置 - 树莓派 + USB麦克风
# 播放: card 0 (bcm2835 Headphones)
# 录音: card 1 (USB PnP Sound Device)

# 默认播放设备
pcm.!default {
    type asym
    playback.pcm "playback_device"
    capture.pcm "capture_device"
}

# 播放设备配置 (树莓派内置音频)
pcm.playback_device {
    type plug
    slave {
        pcm "hw:0,0"
        rate 44100
        channels 2
        format S16_LE
    }
}

# 录音设备配置 (USB麦克风)
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

# 混音器配置 - 用于多应用程序同时使用音频
pcm.dmixer {
    type dmix
    ipc_key 1024
    slave {
        pcm "hw:0,0"
        period_time 0
        period_size 1024
        buffer_size 4096
        rate 44100
        channels 2
    }
    bindings {
        0 0
        1 1
    }
}

# 录音混音器
pcm.dsnooper {
    type dsnoop
    ipc_key 2048
    slave {
        pcm "hw:1,0"
        channels 1
        period_time 0
        period_size 1024
        buffer_size 4096
        rate 44100
    }
    bindings {
        0 0
    }
}

# 全双工配置
pcm.duplex {
    type asym
    playback.pcm "dmixer"
    capture.pcm "dsnooper"
}

# 专用配置别名
pcm.speakers {
    type plug
    slave.pcm "hw:0,0"
}

pcm.microphone {
    type plug
    slave.pcm "hw:1,0"
}
EOF
    
    log_info "ALSA配置文件已创建"
}

# 测试音频配置
test_audio_config() {
    log_step "测试音频配置..."
    
    # 测试播放设备
    log_info "测试播放设备 (将播放2秒测试音)..."
    echo "如果听到测试音，说明播放设备正常"
    speaker-test -c 2 -t wav -l 1 -D speakers || log_warn "播放测试失败"
    
    # 测试录音设备
    log_info "测试录音设备 (录音3秒)..."
    echo "请对着麦克风说话..."
    arecord -D microphone -d 3 -f cd test_recording.wav || log_warn "录音测试失败"
    
    if [[ -f test_recording.wav ]]; then
        log_info "播放录音测试..."
        aplay -D speakers test_recording.wav || log_warn "播放录音失败"
        rm -f test_recording.wav
    fi
}

# 重启音频服务
restart_audio_services() {
    log_step "重启音频服务..."
    
    # 重新加载ALSA配置
    sudo alsactl restore || log_warn "ALSA配置重载失败"
    
    # 如果有PulseAudio，重启它
    if command -v pulseaudio &> /dev/null; then
        log_info "重启PulseAudio..."
        pulseaudio --kill || true
        sleep 2
        pulseaudio --start || true
    fi
}

# 显示配置信息
show_config_info() {
    log_step "配置完成！"
    
    echo
    echo "======================================"
    echo "🔊 ALSA音频配置已完成"
    echo "======================================"
    echo
    echo "📋 你的音频设备配置："
    echo "• 播放设备: card 0 (bcm2835 Headphones)"
    echo "• 录音设备: card 1 (USB PnP Sound Device)"
    echo
    echo "🎵 可用的PCM设备："
    echo "• default - 默认设备（播放+录音）"
    echo "• speakers - 专用播放设备"
    echo "• microphone - 专用录音设备"
    echo "• dmixer - 混音播放设备"
    echo "• dsnooper - 混音录音设备"
    echo
    echo "🧪 测试命令："
    echo "• 测试播放: speaker-test -D speakers -c 2 -t wav -l 1"
    echo "• 测试录音: arecord -D microphone -d 3 -f cd test.wav"
    echo "• 播放录音: aplay -D speakers test.wav"
    echo
    echo "📁 配置文件位置: ~/.asoundrc"
    echo
    echo "✅ 下一步: 如果音频测试正常，我们可以继续修复SDL2问题"
    echo
}

# 主函数
main() {
    echo "======================================"
    echo "🔧 第一步：修复ALSA音频配置"
    echo "======================================"
    echo
    echo "检测到的音频设备："
    echo "• 播放: card 0 (bcm2835 Headphones)"
    echo "• 录音: card 1 (USB PnP Sound Device)"
    echo
    
    read -p "按Enter键继续配置ALSA，或Ctrl+C取消: "
    
    backup_existing_config
    create_alsa_config
    restart_audio_services
    test_audio_config
    show_config_info
    
    log_info "ALSA配置完成！"
}

# 运行主程序
main "$@"