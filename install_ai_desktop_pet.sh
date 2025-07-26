#!/bin/bash
# AI桌宠完整安装脚本
# 适用于树莓派4B和Ubuntu系统
# 版本: 1.0
# 作者: AI桌宠开发团队

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
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

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要以root用户运行此脚本"
        exit 1
    fi
}

# 检查系统兼容性
check_system() {
    log_step "检查系统兼容性..."
    
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        log_info "检测到系统: $NAME $VERSION"
        
        case $ID in
            "raspbian"|"debian"|"ubuntu")
                log_info "系统兼容，继续安装..."
                ;;
            *)
                log_warn "未测试的系统，可能存在兼容性问题"
                read -p "是否继续安装? (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    exit 1
                fi
                ;;
        esac
    else
        log_error "无法检测系统类型"
        exit 1
    fi
}

# 检查Python版本
check_python() {
    log_step "检查Python版本..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        log_info "Python版本: $PYTHON_VERSION"
        
        if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 7) else 1)'; then
            log_info "Python版本满足要求 (>= 3.7)"
        else
            log_error "Python版本过低，需要3.7或更高版本"
            exit 1
        fi
    else
        log_error "未找到Python3，请先安装Python3"
        exit 1
    fi
}

# 更新系统包
update_system() {
    log_step "更新系统包..."
    sudo apt update
    sudo apt upgrade -y
}

# 安装系统依赖
install_system_dependencies() {
    log_step "安装系统依赖..."
    
    local packages=(
        # 基础开发工具
        "build-essential"
        "cmake"
        "git"
        "pkg-config"
        "python3-dev"
        "python3-pip"
        "python3-venv"
        
        # 音频系统
        "alsa-utils"
        "pulseaudio"
        "pulseaudio-utils"
        "libasound2-dev"
        "libportaudio2"
        "libportaudiocpp0"
        "portaudio19-dev"
        "python3-pyaudio"
        "mpg123"
        "ffmpeg"
        "sox"
        "libsox-fmt-all"
        
        # 语音识别依赖
        "espeak"
        "espeak-data"
        "libespeak1"
        "libespeak-dev"
        "festival"
        "festvox-kallpc16k"
        "swig"
        "libpulse-dev"
        "libsamplerate0-dev"
        
        # 图像处理
        "libopencv-dev"
        "python3-opencv"
        
        # I2C和GPIO
        "i2c-tools"
        "python3-smbus"
        "python3-rpi.gpio"
        
        # OLED显示
        "python3-pil"
        "libfreetype6-dev"
        "libjpeg-dev"
        "libopenjp2-7"
        "libtiff5"
        
        # 网络工具
        "curl"
        "wget"
        
        # 系统服务
        "systemd"
    )
    
    log_info "安装 ${#packages[@]} 个系统包..."
    sudo apt install -y "${packages[@]}"
}

# 创建虚拟环境
create_virtual_env() {
    log_step "创建Python虚拟环境..."
    
    if [[ -d ".venv" ]]; then
        log_warn "虚拟环境已存在，是否重新创建? (y/N)"
        read -p "" -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf .venv
        else
            log_info "使用现有虚拟环境"
            return
        fi
    fi
    
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip setuptools wheel
}

# 安装Python依赖
install_python_dependencies() {
    log_step "安装Python依赖..."
    
    # 确保虚拟环境激活
    if [[ -z "$VIRTUAL_ENV" ]]; then
        source .venv/bin/activate
    fi
    
    # 安装基础依赖
    pip install -r src/requirements.txt
    
    # 安装额外的AI桌宠依赖
    local ai_packages=(
        "google-generativeai>=0.3.0"
        "pvporcupine>=3.0.0"
        "edge-tts>=6.1.0"
        "pygame>=2.1.0"
        "openai-whisper>=20231117"
        "torch>=1.13.0"
        "torchaudio>=0.13.0"
        "jieba>=0.42.1"
        "adafruit-circuitpython-ssd1306>=2.12.0"
        "adafruit-blinka>=8.0.0"
        "Pillow>=9.0.0"
        "asyncio"
        "aiofiles"
        "sqlite3"
    )
    
    log_info "安装AI桌宠专用依赖..."
    for package in "${ai_packages[@]}"; do
        log_info "安装: $package"
        pip install "$package"
    done
}

# 配置硬件接口
configure_hardware() {
    log_step "配置硬件接口..."
    
    # 启用I2C
    if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
        log_info "启用I2C接口..."
        echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
    fi
    
    # 启用摄像头
    if ! grep -q "^start_x=1" /boot/config.txt; then
        log_info "启用摄像头接口..."
        echo "start_x=1" | sudo tee -a /boot/config.txt
        echo "gpu_mem=128" | sudo tee -a /boot/config.txt
    fi
    
    # 配置音频权限
    log_info "配置音频权限..."
    sudo usermod -a -G audio $USER
    
    # 加载音频模块
    sudo modprobe snd-usb-audio
}

# 创建配置文件
create_config_files() {
    log_step "创建配置文件..."
    
    # 创建环境变量配置文件
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
EOF
    
    # 添加到bashrc
    if ! grep -q "source ~/.ai_pet_env" ~/.bashrc; then
        echo "source ~/.ai_pet_env" >> ~/.bashrc
    fi
    
    # 创建数据目录
    mkdir -p src/data/ai_memory
    mkdir -p src/data/logs
    mkdir -p src/data/temp
    
    log_info "配置文件创建完成"
}

# 创建systemd服务
create_systemd_service() {
    log_step "创建systemd服务..."
    
    local service_file="/etc/systemd/system/ai-desktop-pet.service"
    local current_user=$(whoami)
    local current_dir=$(pwd)
    
    sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=AI Desktop Pet Robot Control Service
After=network.target sound.target
Wants=network.target

[Service]
Type=simple
User=$current_user
Group=$current_user
WorkingDirectory=$current_dir/src
Environment=PATH=$current_dir/.venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=VIRTUAL_ENV=$current_dir/.venv
ExecStartPre=/bin/bash -c 'source ~/.ai_pet_env'
ExecStart=$current_dir/.venv/bin/python robot_voice_web_control.py
Restart=on-failure
RestartSec=10
StartLimitIntervalSec=60
StartLimitBurst=3
StandardOutput=journal
StandardError=journal

# 资源限制
MemoryMax=1G
CPUQuota=80%

[Install]
WantedBy=multi-user.target
EOF
    
    # 重新加载systemd配置
    sudo systemctl daemon-reload
    
    log_info "systemd服务创建完成"
}

# 运行系统测试
run_system_tests() {
    log_step "运行系统测试..."
    
    # 确保虚拟环境激活
    source .venv/bin/activate
    
    cd src
    
    # 测试基础功能
    log_info "测试基础配置..."
    python3 -c "import config; print('配置系统正常')"
    
    # 测试硬件接口
    log_info "测试硬件接口..."
    python3 -c "
try:
    import RPi.GPIO as GPIO
    print('GPIO接口正常')
except:
    print('GPIO接口不可用（非树莓派环境）')
"
    
    # 测试音频系统
    log_info "测试音频系统..."
    python3 -c "
try:
    import pyaudio
    p = pyaudio.PyAudio()
    print(f'音频设备数量: {p.get_device_count()}')
    p.terminate()
except Exception as e:
    print(f'音频系统测试失败: {e}')
"
    
    # 测试AI依赖
    log_info "测试AI依赖..."
    python3 -c "
try:
    import google.generativeai as genai
    print('Gemini API库正常')
except ImportError as e:
    print(f'Gemini API库导入失败: {e}')

try:
    import pvporcupine
    print('Porcupine库正常')
except ImportError as e:
    print(f'Porcupine库导入失败: {e}')

try:
    import edge_tts
    print('Edge-TTS库正常')
except ImportError as e:
    print(f'Edge-TTS库导入失败: {e}')
"
    
    cd ..
    log_info "系统测试完成"
}

# 显示安装后信息
show_post_install_info() {
    log_step "安装完成！"
    
    echo
    echo "======================================"
    echo "🎉 AI桌宠系统安装成功！"
    echo "======================================"
    echo
    echo "📋 接下来的步骤："
    echo
    echo "1. 配置API密钥："
    echo "   编辑 ~/.ai_pet_env 文件，填入你的API密钥"
    echo "   nano ~/.ai_pet_env"
    echo
    echo "2. 重新加载环境变量："
    echo "   source ~/.ai_pet_env"
    echo
    echo "3. 启动系统："
    echo "   方式1 - 手动启动:"
    echo "   cd src && python3 robot_voice_web_control.py"
    echo
    echo "   方式2 - 系统服务:"
    echo "   sudo systemctl enable ai-desktop-pet"
    echo "   sudo systemctl start ai-desktop-pet"
    echo
    echo "4. 访问Web界面："
    echo "   http://$(hostname -I | awk '{print $1}'):5000"
    echo
    echo "🔧 API密钥获取地址："
    echo "   • Gemini API: https://makersuite.google.com/app/apikey"
    echo "   • Picovoice: https://console.picovoice.ai/"
    echo
    echo "📚 文档位置："
    echo "   • 用户指南: USER_GUIDE.md"
    echo "   • API文档: API_DOCUMENTATION.md"
    echo "   • 故障排除: TROUBLESHOOTING_GUIDE.md"
    echo
    echo "🧪 测试命令："
    echo "   • 基础测试: python3 src/test_integration_suite.py"
    echo "   • AI对话测试: python3 src/test_ai_conversation.py"
    echo "   • 语音测试: python3 src/test_enhanced_voice_system.py"
    echo
    echo "⚠️  重要提醒："
    echo "   • 确保USB麦克风已连接"
    echo "   • 确保OLED显示屏正确连接到I2C"
    echo "   • 首次使用建议在安静环境中测试"
    echo "   • 如果是树莓派，可能需要重启以启用硬件接口"
    echo
    echo "🆘 获取帮助："
    echo "   • 查看日志: journalctl -u ai-desktop-pet -f"
    echo "   • 故障排除: cat TROUBLESHOOTING_GUIDE.md"
    echo
}

# 主安装流程
main() {
    echo "======================================"
    echo "🤖 AI桌宠系统安装程序"
    echo "======================================"
    echo
    
    check_root
    check_system
    check_python
    
    echo "即将开始安装，这可能需要10-30分钟..."
    read -p "按Enter键继续，或Ctrl+C取消: "
    
    update_system
    install_system_dependencies
    create_virtual_env
    install_python_dependencies
    configure_hardware
    create_config_files
    create_systemd_service
    run_system_tests
    show_post_install_info
    
    log_info "安装程序执行完成！"
}

# 错误处理
trap 'log_error "安装过程中发生错误，请检查上面的错误信息"; exit 1' ERR

# 运行主程序
main "$@"