#!/bin/bash
# 树莓派Torch安装脚本
# 可选组件，用于Whisper语音识别

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

# 检查是否为树莓派
check_raspberry_pi() {
    if [[ ! -f "/proc/device-tree/model" ]] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
        log_error "此脚本仅适用于树莓派"
        exit 1
    fi
    
    # 检查树莓派型号
    PI_MODEL=$(cat /proc/device-tree/model)
    log_info "检测到设备: $PI_MODEL"
}

# 检查系统资源
check_resources() {
    log_step "检查系统资源..."
    
    # 检查内存
    TOTAL_MEM=$(free -m | awk 'NR==2{print $2}')
    log_info "总内存: ${TOTAL_MEM}MB"
    
    if [ $TOTAL_MEM -lt 2048 ]; then
        log_warn "内存不足2GB，不建议安装Torch"
        read -p "是否继续安装? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # 检查磁盘空间
    AVAILABLE_SPACE=$(df -m . | awk 'NR==2{print $4}')
    log_info "可用磁盘空间: ${AVAILABLE_SPACE}MB"
    
    if [ $AVAILABLE_SPACE -lt 1024 ]; then
        log_error "磁盘空间不足1GB，无法安装Torch"
        exit 1
    fi
}

# 安装Torch
install_torch() {
    log_step "安装PyTorch..."
    
    # 确保虚拟环境激活
    if [[ -z "$VIRTUAL_ENV" ]]; then
        if [[ -f ".venv/bin/activate" ]]; then
            source .venv/bin/activate
        else
            log_error "未找到虚拟环境，请先运行安装脚本"
            exit 1
        fi
    fi
    
    # 检查Python版本
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log_info "Python版本: $PYTHON_VERSION"
    
    # 根据架构选择安装方式
    ARCH=$(uname -m)
    log_info "系统架构: $ARCH"
    
    case $ARCH in
        "armv7l")
            log_info "安装ARM32版本的PyTorch..."
            # 对于ARM32，使用CPU版本
            pip install torch==1.13.1 --index-url https://download.pytorch.org/whl/cpu
            pip install torchaudio==0.13.1 --index-url https://download.pytorch.org/whl/cpu
            ;;
        "aarch64")
            log_info "安装ARM64版本的PyTorch..."
            # 对于ARM64，可以使用更新的版本
            pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
            ;;
        *)
            log_warn "未知架构: $ARCH，尝试通用安装..."
            pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
            ;;
    esac
}

# 安装Whisper
install_whisper() {
    log_step "安装OpenAI Whisper..."
    
    # 安装Whisper
    pip install openai-whisper
    
    # 下载基础模型
    log_info "下载Whisper基础模型..."
    python3 -c "
import whisper
try:
    model = whisper.load_model('tiny')
    print('Whisper tiny模型下载成功')
    model = whisper.load_model('base')
    print('Whisper base模型下载成功')
except Exception as e:
    print(f'模型下载失败: {e}')
"
}

# 测试安装
test_installation() {
    log_step "测试安装..."
    
    # 测试Torch
    python3 -c "
import torch
print(f'PyTorch版本: {torch.__version__}')
print(f'CUDA可用: {torch.cuda.is_available()}')

# 简单测试
x = torch.randn(2, 3)
print(f'测试张量: {x.shape}')
print('PyTorch安装成功!')
"
    
    # 测试Whisper
    python3 -c "
try:
    import whisper
    print(f'Whisper安装成功')
    
    # 列出可用模型
    print('可用模型:', whisper.available_models())
except Exception as e:
    print(f'Whisper测试失败: {e}')
"
}

# 主函数
main() {
    echo "======================================"
    echo "🔥 树莓派PyTorch安装程序"
    echo "======================================"
    echo
    echo "⚠️  警告：此安装可能需要很长时间（30分钟-2小时）"
    echo "建议在稳定的网络环境下进行"
    echo
    
    check_raspberry_pi
    check_resources
    
    read -p "是否继续安装PyTorch和Whisper? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "安装已取消"
        exit 0
    fi
    
    install_torch
    install_whisper
    test_installation
    
    echo
    echo "======================================"
    echo "🎉 PyTorch和Whisper安装完成！"
    echo "======================================"
    echo
    echo "现在可以使用以下功能："
    echo "• 本地Whisper语音识别"
    echo "• 更高质量的语音处理"
    echo "• 离线语音识别能力"
    echo
    echo "注意：首次使用Whisper时会下载模型文件"
    echo
}

# 错误处理
trap 'log_error "安装过程中发生错误"; exit 1' ERR

# 运行主程序
main "$@"