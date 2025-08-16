#!/bin/bash
# AI桌宠音频和AI问题修复脚本
# 专门解决ALSA、SDL2、Porcupine和Gemini API问题

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查是否在项目根目录
check_project_root() {
    if [[ ! -f "src/robot_voice_web_control.py" ]]; then
        log_error "请在AI桌宠项目根目录运行此脚本"
        exit 1
    fi
}

# 修复ALSA音频配置
fix_alsa_configuration() {
    log_step "修复ALSA音频配置..."
    
    # 备份现有配置
    if [[ -f ~/.asoundrc ]]; then
        cp ~/.asoundrc ~/.asoundrc.backup.$(date +%Y%m%d_%H%M%S)
    fi
    
    # 创建新的ALSA配置
    cat > ~/.asoundrc << 'EOF'
# ALSA configuration for AI Desktop Pet
# 优先使用PulseAudio
pcm.!default {
    type pulse
    fallback "sysdefault"
    hint {
        show on
        description "Default ALSA Output (currently PulseAudio Sound Server)"
    }
}

ctl.!default {
    type pulse
    fallback "sysdefault"
}

# USB音频设备配置
pcm.usb {
    type hw
    card 1
}

ctl.usb {
    type hw
    card 1
}

# 混音器配置
pcm.dmixer {
    type dmix
    ipc_key 1024
    slave {
        pcm "hw:0,0"
        period_time 0
        period_size 1024
        buffer_size 4096
        rate 44100
    }
    bindings {
        0 0
        1 1
    }
}

pcm.dsnooper {
    type dsnoop
    ipc_key 2048
    slave {
        pcm "hw:0,0"
        channels 2
        period_time 0
        period_size 1024
        buffer_size 4096
        rate 44100
    }
    bindings {
        0 0
        1 1
    }
}

pcm.duplex {
    type asym
    playback.pcm "dmixer"
    capture.pcm "dsnooper"
}
EOF
    
    log_info "ALSA配置已更新"
}

# 安装SDL2音频库
install_sdl2_libraries() {
    log_step "安装SDL2音频库..."
    
    # 更新包列表
    sudo apt update
    
    # 安装SDL2相关包
    local sdl2_packages=(
        "libsdl2-2.0-0"
        "libsdl2-dev"
        "libsdl2-mixer-2.0-0"
        "libsdl2-mixer-dev"
        "libsdl2-image-2.0-0"
        "libsdl2-image-dev"
        "libsdl2-ttf-2.0-0"
        "libsdl2-ttf-dev"
    )
    
    log_info "安装SDL2包: ${sdl2_packages[*]}"
    sudo apt install -y "${sdl2_packages[@]}"
    
    # 重新安装pygame
    if [[ -d ".venv" ]]; then
        log_info "重新安装pygame..."
        source .venv/bin/activate
        pip uninstall pygame -y
        pip install pygame --no-cache-dir --force-reinstall
        
        # 测试pygame
        python3 -c "
import pygame
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    print('✓ pygame音频系统初始化成功')
    pygame.mixer.quit()
except Exception as e:
    print(f'✗ pygame音频系统初始化失败: {e}')
"
    else
        log_warn "虚拟环境不存在，跳过pygame重装"
    fi
}

# 修复Porcupine语言配置
fix_porcupine_language() {
    log_step "修复Porcupine语言配置..."
    
    # 创建唤醒词目录
    mkdir -p src/wake_words
    cd src/wake_words
    
    # 下载中文模型文件
    log_info "下载Porcupine中文模型..."
    if [[ ! -f "porcupine_params_zh.pv" ]]; then
        wget -O porcupine_params_zh.pv \
            "https://github.com/Picovoice/porcupine/raw/master/lib/common/porcupine_params_zh.pv" || \
        curl -L -o porcupine_params_zh.pv \
            "https://github.com/Picovoice/porcupine/raw/master/lib/common/porcupine_params_zh.pv"
    fi
    
    # 检查是否有中文唤醒词文件
    if ls *.ppn 1> /dev/null 2>&1; then
        log_info "发现唤醒词文件:"
        ls -la *.ppn
    else
        log_warn "未发现自定义唤醒词文件，将使用内置英文唤醒词"
    fi
    
    cd ../..
    
    # 更新配置文件以使用正确的模型
    if [[ -f "src/config.py" ]]; then
        log_info "更新Porcupine配置..."
        
        # 备份配置文件
        cp src/config.py src/config.py.backup.$(date +%Y%m%d_%H%M%S)
        
        # 更新配置
        python3 << 'EOF'
import re

# 读取配置文件
with open('src/config.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 更新Porcupine模型路径
content = re.sub(
    r'PORCUPINE_MODEL_PATH\s*=\s*["\'][^"\']*["\']',
    'PORCUPINE_MODEL_PATH = "wake_words/porcupine_params_zh.pv"',
    content
)

# 确保使用中文模型
if 'PORCUPINE_MODEL_PATH' not in content:
    content += '\n# Porcupine中文模型配置\nPORCUPINE_MODEL_PATH = "wake_words/porcupine_params_zh.pv"\n'

# 写回文件
with open('src/config.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("配置文件已更新")
EOF
    fi
}

# 配置音频权限和服务
configure_audio_permissions() {
    log_step "配置音频权限和服务..."
    
    # 添加用户到音频组
    sudo usermod -a -G audio $USER
    sudo usermod -a -G pulse-access $USER
    
    # 重启音频服务
    log_info "重启音频服务..."
    sudo systemctl restart alsa-state || true
    
    # 重启PulseAudio
    pulseaudio --kill || true
    sleep 2
    pulseaudio --start || true
    
    # 设置默认音频设备
    if command -v pactl &> /dev/null; then
        log_info "配置PulseAudio默认设备..."
        pactl set-default-sink @DEFAULT_SINK@ || true
        pactl set-default-source @DEFAULT_SOURCE@ || true
    fi
}

# 修复Gemini API配置
fix_gemini_api_configuration() {
    log_step "修复Gemini API配置..."
    
    # 检查环境变量文件
    if [[ ! -f ~/.ai_pet_env ]]; then
        log_info "创建环境变量配置文件..."
        cat > ~/.ai_pet_env << 'EOF'
# AI桌宠环境变量配置
# 请填入你的API密钥

# Google Gemini API密钥
# 获取地址: https://makersuite.google.com/app/apikey
export GEMINI_API_KEY="your_gemini_api_key_here"

# Picovoice访问密钥（用于自定义唤醒词）
# 获取地址: https://console.picovoice.ai/
export PICOVOICE_ACCESS_KEY="your_picovoice_access_key_here"

# 项目路径
export AI_PET_HOME="$(pwd)"

# Python虚拟环境
export VIRTUAL_ENV="$AI_PET_HOME/.venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"

# 音频配置
export PULSE_RUNTIME_PATH="/run/user/$(id -u)/pulse"
export SDL_AUDIODRIVER="pulse"
EOF
    fi
    
    # 添加到bashrc
    if ! grep -q "source ~/.ai_pet_env" ~/.bashrc; then
        echo "source ~/.ai_pet_env" >> ~/.bashrc
        log_info "环境变量已添加到.bashrc"
    fi
    
    # 加载环境变量
    source ~/.ai_pet_env
    
    # 检查API密钥
    if [[ "$GEMINI_API_KEY" == "your_gemini_api_key_here" ]]; then
        log_warn "请编辑 ~/.ai_pet_env 文件，填入你的Gemini API密钥"
        log_warn "获取地址: https://makersuite.google.com/app/apikey"
    else
        log_info "Gemini API密钥已配置"
    fi
}

# 测试修复结果
test_fixes() {
    log_step "测试修复结果..."
    
    if [[ -d ".venv" ]]; then
        source .venv/bin/activate
        
        # 测试音频系统
        log_info "测试音频系统..."
        python3 -c "
import sys
try:
    import pygame
    pygame.mixer.init()
    print('✓ pygame音频系统正常')
    pygame.mixer.quit()
except Exception as e:
    print(f'✗ pygame音频系统异常: {e}')

try:
    import pyaudio
    p = pyaudio.PyAudio()
    device_count = p.get_device_count()
    print(f'✓ PyAudio检测到 {device_count} 个音频设备')
    p.terminate()
except Exception as e:
    print(f'✗ PyAudio异常: {e}')
"
        
        # 测试Porcupine
        log_info "测试Porcupine配置..."
        python3 -c "
import os
try:
    import pvporcupine
    # 尝试使用中文模型
    model_path = 'src/wake_words/porcupine_params_zh.pv'
    if os.path.exists(model_path):
        print('✓ Porcupine中文模型文件存在')
    else:
        print('✗ Porcupine中文模型文件不存在')
    
    # 测试内置英文唤醒词
    porcupine = pvporcupine.create(keywords=['picovoice'])
    print('✓ Porcupine初始化成功（使用内置英文唤醒词）')
    porcupine.delete()
except Exception as e:
    print(f'✗ Porcupine初始化失败: {e}')
"
        
        # 测试Gemini API
        log_info "测试Gemini API..."
        python3 -c "
import os
try:
    import google.generativeai as genai
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key and api_key != 'your_gemini_api_key_here':
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        print('✓ Gemini API配置正常')
    else:
        print('✗ Gemini API密钥未配置')
except Exception as e:
    print(f'✗ Gemini API异常: {e}')
"
    else
        log_warn "虚拟环境不存在，跳过Python模块测试"
    fi
    
    # 测试音频设备
    log_info "测试音频设备..."
    echo "可用的播放设备:"
    aplay -l | head -10 || echo "无法列出播放设备"
    echo "可用的录音设备:"
    arecord -l | head -10 || echo "无法列出录音设备"
}

# 创建快速修复脚本
create_quick_fix_script() {
    log_step "创建快速修复脚本..."
    
    cat > quick_audio_fix.sh << 'EOF'
#!/bin/bash
# 快速音频修复脚本

echo "重启音频服务..."
pulseaudio --kill
sleep 2
pulseaudio --start

echo "重新加载ALSA配置..."
sudo alsactl restore

echo "测试音频..."
speaker-test -t wav -c 2 -l 1

echo "音频修复完成"
EOF
    
    chmod +x quick_audio_fix.sh
    log_info "快速修复脚本已创建: quick_audio_fix.sh"
}

# 显示修复后的使用说明
show_post_fix_instructions() {
    log_step "修复完成！"
    
    echo
    echo "======================================"
    echo "🔧 音频和AI问题修复完成"
    echo "======================================"
    echo
    echo "📋 接下来的步骤："
    echo
    echo "1. 重新加载环境变量："
    echo "   source ~/.ai_pet_env"
    echo
    echo "2. 配置Gemini API密钥："
    echo "   nano ~/.ai_pet_env"
    echo "   # 填入你的API密钥"
    echo
    echo "3. 重启系统（推荐）："
    echo "   sudo reboot"
    echo
    echo "4. 或者重新登录用户："
    echo "   # 注销并重新登录"
    echo
    echo "5. 测试系统："
    echo "   cd src && python3 robot_voice_web_control.py"
    echo
    echo "🔧 如果仍有音频问题："
    echo "   ./quick_audio_fix.sh"
    echo
    echo "📚 查看详细故障排除："
    echo "   cat TROUBLESHOOTING_GUIDE.md"
    echo
    echo "⚠️  重要提醒："
    echo "   • 确保USB麦克风已连接"
    echo "   • 重启后音频配置才会完全生效"
    echo "   • 如果使用自定义唤醒词，确保是中文版本"
    echo
}

# 主修复流程
main() {
    echo "======================================"
    echo "🔧 AI桌宠音频和AI问题修复程序"
    echo "======================================"
    echo
    
    check_project_root
    
    echo "即将修复以下问题："
    echo "• ALSA音频配置错误"
    echo "• SDL2音频库缺失"
    echo "• Porcupine语言不匹配"
    echo "• Gemini API配置问题"
    echo
    
    read -p "按Enter键继续，或Ctrl+C取消: "
    
    fix_alsa_configuration
    install_sdl2_libraries
    fix_porcupine_language
    configure_audio_permissions
    fix_gemini_api_configuration
    test_fixes
    create_quick_fix_script
    show_post_fix_instructions
    
    log_info "修复程序执行完成！"
}

# 错误处理
trap 'log_error "修复过程中发生错误，请检查上面的错误信息"; exit 1' ERR

# 运行主程序
main "$@"