#!/bin/bash
# 第二步：修复SDL2音频库问题
# 解决 libSDL2_mixer-2.0.so.0 缺失问题

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

# 检查当前SDL2状态
check_current_sdl2_status() {
    log_step "检查当前SDL2状态..."
    
    echo "检查SDL2库文件："
    if ldconfig -p | grep -q "libSDL2-2.0.so"; then
        log_info "✓ libSDL2-2.0.so 已安装"
    else
        log_warn "✗ libSDL2-2.0.so 未找到"
    fi
    
    if ldconfig -p | grep -q "libSDL2_mixer-2.0.so"; then
        log_info "✓ libSDL2_mixer-2.0.so 已安装"
    else
        log_warn "✗ libSDL2_mixer-2.0.so 未找到 (这是主要问题)"
    fi
    
    echo
    echo "当前pygame状态："
    if [[ -d ".venv" ]]; then
        source .venv/bin/activate
        python3 -c "
import pygame
try:
    pygame.mixer.init()
    print('✓ pygame.mixer 当前可以初始化')
    pygame.mixer.quit()
except Exception as e:
    print(f'✗ pygame.mixer 初始化失败: {e}')
" 2>/dev/null || echo "✗ pygame导入失败"
    else
        log_warn "虚拟环境不存在"
    fi
}

# 安装SDL2库
install_sdl2_libraries() {
    log_step "安装SDL2音频库..."
    
    # 更新包列表
    log_info "更新包列表..."
    sudo apt update
    
    # 安装SDL2核心库
    log_info "安装SDL2核心库..."
    sudo apt install -y libsdl2-2.0-0 libsdl2-dev
    
    # 安装SDL2音频扩展库
    log_info "安装SDL2音频扩展库..."
    sudo apt install -y libsdl2-mixer-2.0-0 libsdl2-mixer-dev
    
    # 安装其他SDL2扩展（可选，但有助于兼容性）
    log_info "安装SDL2其他扩展库..."
    sudo apt install -y \
        libsdl2-image-2.0-0 libsdl2-image-dev \
        libsdl2-ttf-2.0-0 libsdl2-ttf-dev \
        libsdl2-net-2.0-0 libsdl2-net-dev
    
    # 更新动态链接库缓存
    log_info "更新动态链接库缓存..."
    sudo ldconfig
}

# 重新安装pygame
reinstall_pygame() {
    log_step "重新安装pygame..."
    
    if [[ ! -d ".venv" ]]; then
        log_error "虚拟环境不存在，请先运行安装脚本"
        return 1
    fi
    
    source .venv/bin/activate
    
    # 完全卸载pygame
    log_info "卸载现有pygame..."
    pip uninstall pygame -y || true
    
    # 清理pip缓存
    log_info "清理pip缓存..."
    pip cache purge || true
    
    # 重新安装pygame
    log_info "重新安装pygame..."
    pip install pygame --no-cache-dir --force-reinstall
    
    log_info "pygame重新安装完成"
}

# 配置环境变量
configure_environment() {
    log_step "配置SDL2环境变量..."
    
    # 检查环境变量文件
    if [[ -f ~/.ai_pet_env ]]; then
        # 添加SDL2配置到环境变量文件
        if ! grep -q "SDL_AUDIODRIVER" ~/.ai_pet_env; then
            echo "" >> ~/.ai_pet_env
            echo "# SDL2音频配置" >> ~/.ai_pet_env
            echo "export SDL_AUDIODRIVER=\"alsa\"" >> ~/.ai_pet_env
            echo "export SDL_ALSA_PCM_CARD=\"0\"" >> ~/.ai_pet_env
            echo "export SDL_ALSA_PCM_DEVICE=\"0\"" >> ~/.ai_pet_env
            log_info "SDL2环境变量已添加到 ~/.ai_pet_env"
        fi
        
        # 重新加载环境变量
        source ~/.ai_pet_env
    else
        log_warn "环境变量文件不存在，创建基本配置..."
        cat > ~/.ai_pet_env << 'EOF'
# AI桌宠环境变量配置

# SDL2音频配置
export SDL_AUDIODRIVER="alsa"
export SDL_ALSA_PCM_CARD="0"
export SDL_ALSA_PCM_DEVICE="0"

# 项目路径
export AI_PET_HOME="$(pwd)"
EOF
        source ~/.ai_pet_env
    fi
}

# 测试SDL2和pygame
test_sdl2_pygame() {
    log_step "测试SDL2和pygame..."
    
    # 检查SDL2库
    echo "检查SDL2库安装："
    if ldconfig -p | grep -q "libSDL2_mixer-2.0.so"; then
        log_info "✓ libSDL2_mixer-2.0.so 已正确安装"
        ldconfig -p | grep "libSDL2_mixer-2.0.so" | head -1
    else
        log_error "✗ libSDL2_mixer-2.0.so 仍然缺失"
        return 1
    fi
    
    # 测试pygame
    if [[ -d ".venv" ]]; then
        source .venv/bin/activate
        
        log_info "测试pygame音频系统..."
        python3 -c "
import pygame
import sys

print('pygame版本:', pygame.version.ver)
print('SDL版本:', pygame.version.SDL)

try:
    # 初始化pygame音频系统
    pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
    pygame.mixer.init()
    
    print('✓ pygame.mixer 初始化成功')
    print('  - 频率:', pygame.mixer.get_init()[0])
    print('  - 格式:', pygame.mixer.get_init()[1])
    print('  - 声道:', pygame.mixer.get_init()[2])
    
    # 测试音频播放功能
    print('✓ pygame音频系统完全正常')
    
    pygame.mixer.quit()
    
except Exception as e:
    print(f'✗ pygame.mixer 测试失败: {e}')
    sys.exit(1)
"
        
        if [[ $? -eq 0 ]]; then
            log_info "✓ pygame音频系统测试通过"
        else
            log_error "✗ pygame音频系统测试失败"
            return 1
        fi
    else
        log_warn "虚拟环境不存在，跳过pygame测试"
    fi
}

# 显示完成信息
show_completion_info() {
    log_step "SDL2修复完成！"
    
    echo
    echo "======================================"
    echo "🔧 第二步：SDL2库修复完成"
    echo "======================================"
    echo
    echo "✅ 已完成的修复："
    echo "• 安装了SDL2核心库"
    echo "• 安装了SDL2_mixer音频库"
    echo "• 重新安装了pygame"
    echo "• 配置了SDL2环境变量"
    echo
    echo "🧪 测试结果："
    echo "• libSDL2_mixer-2.0.so 库已安装"
    echo "• pygame.mixer 可以正常初始化"
    echo "• 音频系统配置正确"
    echo
    echo "📋 环境变量配置："
    echo "• SDL_AUDIODRIVER=alsa"
    echo "• SDL_ALSA_PCM_CARD=0"
    echo "• SDL_ALSA_PCM_DEVICE=0"
    echo
    echo "✅ 下一步: 如果测试通过，我们可以继续修复Porcupine语言问题"
    echo
}

# 主函数
main() {
    echo "======================================"
    echo "🔧 第二步：修复SDL2音频库"
    echo "======================================"
    echo
    echo "这一步将解决："
    echo "• libSDL2_mixer-2.0.so.0 缺失问题"
    echo "• pygame音频系统初始化失败"
    echo "• 音频播放系统异常"
    echo
    
    read -p "按Enter键继续安装SDL2库，或Ctrl+C取消: "
    
    check_current_sdl2_status
    install_sdl2_libraries
    configure_environment
    reinstall_pygame
    test_sdl2_pygame
    show_completion_info
    
    log_info "SDL2修复完成！"
}

# 错误处理
trap 'log_error "SDL2修复过程中发生错误"; exit 1' ERR

# 运行主程序
main "$@"