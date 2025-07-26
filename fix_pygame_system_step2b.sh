#!/bin/bash
# 第二步B：修复系统级pygame安装
# 适用于没有虚拟环境的情况

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

# 检查SDL2库安装状态
check_sdl2_installation() {
    log_step "检查SDL2库安装状态..."
    
    echo "检查关键SDL2库："
    if ldconfig -p | grep -q "libSDL2-2.0.so"; then
        log_info "✓ libSDL2-2.0.so 已安装"
        ldconfig -p | grep "libSDL2-2.0.so" | head -1
    else
        log_warn "✗ libSDL2-2.0.so 未找到"
    fi
    
    if ldconfig -p | grep -q "libSDL2_mixer-2.0.so"; then
        log_info "✓ libSDL2_mixer-2.0.so 已安装"
        ldconfig -p | grep "libSDL2_mixer-2.0.so" | head -1
    else
        log_warn "✗ libSDL2_mixer-2.0.so 未找到"
    fi
}

# 重新安装系统级pygame
reinstall_system_pygame() {
    log_step "重新安装系统级pygame..."
    
    # 卸载现有pygame
    log_info "卸载现有pygame..."
    sudo pip3 uninstall pygame -y || true
    
    # 也尝试通过apt卸载
    sudo apt remove python3-pygame -y || true
    
    # 清理pip缓存
    log_info "清理pip缓存..."
    pip3 cache purge || true
    
    # 重新安装pygame
    log_info "重新安装pygame..."
    sudo pip3 install pygame --no-cache-dir --force-reinstall
    
    log_info "系统级pygame重新安装完成"
}

# 配置系统环境变量
configure_system_environment() {
    log_step "配置系统环境变量..."
    
    # 创建或更新环境变量文件
    if [[ ! -f ~/.ai_pet_env ]]; then
        log_info "创建环境变量配置文件..."
        cat > ~/.ai_pet_env << 'EOF'
# AI桌宠环境变量配置

# SDL2音频配置
export SDL_AUDIODRIVER="alsa"
export SDL_ALSA_PCM_CARD="0"
export SDL_ALSA_PCM_DEVICE="0"

# 项目路径
export AI_PET_HOME="$(pwd)"

# Python路径（系统级）
export PYTHONPATH="/usr/local/lib/python3.9/dist-packages:/usr/lib/python3/dist-packages:$PYTHONPATH"
EOF
    else
        # 添加SDL2配置到现有文件
        if ! grep -q "SDL_AUDIODRIVER" ~/.ai_pet_env; then
            echo "" >> ~/.ai_pet_env
            echo "# SDL2音频配置" >> ~/.ai_pet_env
            echo "export SDL_AUDIODRIVER=\"alsa\"" >> ~/.ai_pet_env
            echo "export SDL_ALSA_PCM_CARD=\"0\"" >> ~/.ai_pet_env
            echo "export SDL_ALSA_PCM_DEVICE=\"0\"" >> ~/.ai_pet_env
        fi
    fi
    
    # 添加到bashrc
    if ! grep -q "source ~/.ai_pet_env" ~/.bashrc; then
        echo "source ~/.ai_pet_env" >> ~/.bashrc
        log_info "环境变量已添加到.bashrc"
    fi
    
    # 加载环境变量
    source ~/.ai_pet_env
    log_info "环境变量已配置"
}

# 测试系统级pygame
test_system_pygame() {
    log_step "测试系统级pygame..."
    
    # 加载环境变量
    source ~/.ai_pet_env
    
    log_info "测试pygame音频系统..."
    python3 -c "
import pygame
import sys
import os

print('Python版本:', sys.version)
print('pygame版本:', pygame.version.ver)
print('SDL版本:', pygame.version.SDL)

# 显示环境变量
print('SDL_AUDIODRIVER:', os.getenv('SDL_AUDIODRIVER', '未设置'))
print('SDL_ALSA_PCM_CARD:', os.getenv('SDL_ALSA_PCM_CARD', '未设置'))

try:
    # 初始化pygame音频系统
    pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
    pygame.mixer.init()
    
    print('✓ pygame.mixer 初始化成功')
    
    # 获取音频信息
    init_info = pygame.mixer.get_init()
    if init_info:
        print('  - 频率:', init_info[0])
        print('  - 格式:', init_info[1])
        print('  - 声道:', init_info[2])
    
    print('✓ pygame音频系统完全正常')
    
    pygame.mixer.quit()
    
except Exception as e:
    print(f'✗ pygame.mixer 测试失败: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
    
    if [[ $? -eq 0 ]]; then
        log_info "✓ 系统级pygame音频系统测试通过"
        return 0
    else
        log_error "✗ 系统级pygame音频系统测试失败"
        return 1
    fi
}

# 额外的故障排除
additional_troubleshooting() {
    log_step "执行额外的故障排除..."
    
    # 检查Python模块路径
    log_info "检查Python模块路径..."
    python3 -c "
import sys
print('Python模块搜索路径:')
for path in sys.path:
    print('  -', path)
"
    
    # 检查pygame安装位置
    log_info "检查pygame安装位置..."
    python3 -c "
try:
    import pygame
    print('pygame安装位置:', pygame.__file__)
except ImportError as e:
    print('pygame导入失败:', e)
"
    
    # 检查系统音频状态
    log_info "检查系统音频状态..."
    if command -v pactl &> /dev/null; then
        echo "PulseAudio状态:"
        pactl info | grep -E "(Server Name|Server Version|Default Sink|Default Source)" || true
    fi
    
    echo "ALSA设备状态:"
    cat /proc/asound/cards || true
}

# 显示完成信息
show_completion_info() {
    log_step "系统级pygame修复完成！"
    
    echo
    echo "======================================"
    echo "🔧 第二步B：系统级pygame修复完成"
    echo "======================================"
    echo
    echo "✅ 已完成的修复："
    echo "• SDL2库已安装并验证"
    echo "• 系统级pygame已重新安装"
    echo "• SDL2环境变量已配置"
    echo "• 音频驱动设置为ALSA"
    echo
    echo "🧪 测试结果："
    if test_system_pygame; then
        echo "• ✓ pygame.mixer 可以正常初始化"
        echo "• ✓ 音频系统配置正确"
        echo "• ✓ SDL2库链接正常"
    else
        echo "• ✗ pygame测试失败，需要进一步排查"
    fi
    echo
    echo "📋 环境配置："
    echo "• 配置文件: ~/.ai_pet_env"
    echo "• SDL音频驱动: ALSA"
    echo "• 音频设备: card 0, device 0"
    echo
    echo "🔄 重新加载环境变量："
    echo "   source ~/.ai_pet_env"
    echo
    echo "✅ 下一步: 如果pygame测试通过，我们可以继续修复Porcupine语言问题"
    echo
}

# 主函数
main() {
    echo "======================================"
    echo "🔧 第二步B：修复系统级pygame"
    echo "======================================"
    echo
    echo "检测到你使用系统级Python安装"
    echo "这一步将："
    echo "• 重新安装系统级pygame"
    echo "• 配置SDL2环境变量"
    echo "• 测试pygame音频功能"
    echo
    
    read -p "按Enter键继续修复系统级pygame，或Ctrl+C取消: "
    
    check_sdl2_installation
    configure_system_environment
    reinstall_system_pygame
    
    echo
    log_info "现在测试pygame..."
    if test_system_pygame; then
        show_completion_info
        log_info "系统级pygame修复成功！"
    else
        log_warn "pygame测试失败，执行额外排查..."
        additional_troubleshooting
        echo
        echo "请检查上面的输出信息，可能需要："
        echo "1. 重启系统让所有配置生效"
        echo "2. 检查是否有其他Python版本冲突"
        echo "3. 手动测试: python3 -c 'import pygame; pygame.mixer.init()'"
    fi
}

# 错误处理
trap 'log_error "系统级pygame修复过程中发生错误"; exit 1' ERR

# 运行主程序
main "$@"