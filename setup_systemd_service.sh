#!/bin/bash
# AI桌宠系统服务安装脚本
# 用于设置systemd自动启动服务

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

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要以root用户运行此脚本"
        exit 1
    fi
}

# 检查systemd是否可用
check_systemd() {
    if ! command -v systemctl &> /dev/null; then
        log_error "systemd不可用，无法创建系统服务"
        exit 1
    fi
    
    if ! systemctl --version &> /dev/null; then
        log_error "systemctl命令不可用"
        exit 1
    fi
    
    log_info "systemd版本: $(systemctl --version | head -n1)"
}

# 获取当前用户和路径信息
get_system_info() {
    CURRENT_USER=$(whoami)
    CURRENT_DIR=$(pwd)
    HOME_DIR=$(eval echo ~$CURRENT_USER)
    
    log_info "当前用户: $CURRENT_USER"
    log_info "项目路径: $CURRENT_DIR"
    log_info "用户主目录: $HOME_DIR"
    
    # 检查项目结构
    if [[ ! -f "src/robot_voice_web_control.py" ]]; then
        log_error "未找到主程序文件，请确保在项目根目录运行此脚本"
        exit 1
    fi
    
    if [[ ! -d ".venv" ]]; then
        log_error "未找到Python虚拟环境，请先运行安装脚本"
        exit 1
    fi
}

# 创建systemd服务文件
create_service_file() {
    log_step "创建systemd服务文件..."
    
    local service_name="ai-desktop-pet@${CURRENT_USER}.service"
    local service_file="/etc/systemd/system/$service_name"
    
    # 检查是否已存在服务文件
    if [[ -f "$service_file" ]]; then
        log_warn "服务文件已存在，是否覆盖? (y/N)"
        read -p "" -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "跳过服务文件创建"
            return
        fi
    fi
    
    # 创建服务文件内容
    sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=AI Desktop Pet Robot Control Service for %i
Documentation=file://$CURRENT_DIR/USER_GUIDE.md
After=network-online.target sound.target multi-user.target
Wants=network-online.target
Requires=sound.target

[Service]
Type=simple
User=%i
Group=%i
WorkingDirectory=$CURRENT_DIR/src
Environment=PATH=$CURRENT_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=VIRTUAL_ENV=$CURRENT_DIR/.venv
Environment=PYTHONPATH=$CURRENT_DIR/src
Environment=AI_PET_HOME=$CURRENT_DIR
EnvironmentFile=-$HOME_DIR/.ai_pet_env

# 启动前检查和准备
ExecStartPre=/bin/bash -c 'test -f $HOME_DIR/.ai_pet_env && source $HOME_DIR/.ai_pet_env || echo "Warning: Environment file not found"'
ExecStartPre=/bin/bash -c 'test -d $CURRENT_DIR/.venv || (echo "Virtual environment not found" && exit 1)'
ExecStartPre=/bin/bash -c 'test -f $CURRENT_DIR/src/robot_voice_web_control.py || (echo "Main program not found" && exit 1)'

# 主程序启动
ExecStart=$CURRENT_DIR/.venv/bin/python robot_voice_web_control.py

# 停止命令
ExecStop=/bin/kill -TERM \$MAINPID
ExecStopPost=/bin/bash -c 'pkill -f "robot_voice_web_control.py" || true'

# 重启策略
Restart=on-failure
RestartSec=15
StartLimitIntervalSec=300
StartLimitBurst=5

# 超时设置
TimeoutStartSec=120
TimeoutStopSec=30

# 输出设置
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-desktop-pet

# 资源限制
MemoryMax=1.5G
CPUQuota=90%
TasksMax=200

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$CURRENT_DIR/src/data
ReadWritePaths=/tmp
ReadWritePaths=/var/tmp

# 权限设置 - 树莓派硬件访问
SupplementaryGroups=audio video i2c gpio spi dialout

# 环境变量
Environment=PULSE_RUNTIME_PATH=/run/user/%i/pulse

[Install]
WantedBy=multi-user.target
EOF
    
    log_info "服务文件已创建: $service_file"
}

# 创建服务管理脚本
create_service_scripts() {
    log_step "创建服务管理脚本..."
    
    # 创建启动脚本
    cat > start_ai_pet_service.sh << 'EOF'
#!/bin/bash
# AI桌宠服务启动脚本

CURRENT_USER=$(whoami)
SERVICE_NAME="ai-desktop-pet@${CURRENT_USER}.service"

echo "启动AI桌宠服务..."

# 重新加载systemd配置
sudo systemctl daemon-reload

# 启用服务（开机自启）
sudo systemctl enable "$SERVICE_NAME"

# 启动服务
sudo systemctl start "$SERVICE_NAME"

# 检查服务状态
sleep 3
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "✅ AI桌宠服务启动成功！"
    echo "服务状态:"
    systemctl status "$SERVICE_NAME" --no-pager -l
    echo ""
    echo "查看日志: journalctl -u $SERVICE_NAME -f"
    echo "停止服务: sudo systemctl stop $SERVICE_NAME"
    echo "重启服务: sudo systemctl restart $SERVICE_NAME"
else
    echo "❌ AI桌宠服务启动失败"
    echo "查看错误日志:"
    journalctl -u "$SERVICE_NAME" --no-pager -l
    exit 1
fi
EOF
    
    # 创建停止脚本
    cat > stop_ai_pet_service.sh << 'EOF'
#!/bin/bash
# AI桌宠服务停止脚本

CURRENT_USER=$(whoami)
SERVICE_NAME="ai-desktop-pet@${CURRENT_USER}.service"

echo "停止AI桌宠服务..."

# 停止服务
sudo systemctl stop "$SERVICE_NAME"

# 禁用开机自启（可选）
read -p "是否禁用开机自启? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo systemctl disable "$SERVICE_NAME"
    echo "已禁用开机自启"
fi

echo "✅ AI桌宠服务已停止"
EOF
    
    # 创建状态检查脚本
    cat > check_ai_pet_service.sh << 'EOF'
#!/bin/bash
# AI桌宠服务状态检查脚本

CURRENT_USER=$(whoami)
SERVICE_NAME="ai-desktop-pet@${CURRENT_USER}.service"

echo "=== AI桌宠服务状态 ==="
systemctl status "$SERVICE_NAME" --no-pager -l

echo ""
echo "=== 最近日志 ==="
journalctl -u "$SERVICE_NAME" --no-pager -l -n 20

echo ""
echo "=== 服务信息 ==="
echo "服务名称: $SERVICE_NAME"
echo "是否启用: $(systemctl is-enabled $SERVICE_NAME 2>/dev/null || echo 'disabled')"
echo "是否运行: $(systemctl is-active $SERVICE_NAME 2>/dev/null || echo 'inactive')"

echo ""
echo "=== 管理命令 ==="
echo "启动服务: sudo systemctl start $SERVICE_NAME"
echo "停止服务: sudo systemctl stop $SERVICE_NAME"
echo "重启服务: sudo systemctl restart $SERVICE_NAME"
echo "查看日志: journalctl -u $SERVICE_NAME -f"
echo "启用自启: sudo systemctl enable $SERVICE_NAME"
echo "禁用自启: sudo systemctl disable $SERVICE_NAME"
EOF
    
    # 设置执行权限
    chmod +x start_ai_pet_service.sh
    chmod +x stop_ai_pet_service.sh
    chmod +x check_ai_pet_service.sh
    
    log_info "服务管理脚本已创建"
}

# 创建日志轮转配置
create_logrotate_config() {
    log_step "创建日志轮转配置..."
    
    local logrotate_file="/etc/logrotate.d/ai-desktop-pet"
    
    sudo tee "$logrotate_file" > /dev/null << EOF
# AI桌宠日志轮转配置
$CURRENT_DIR/src/data/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 $CURRENT_USER $CURRENT_USER
    postrotate
        systemctl reload-or-restart ai-desktop-pet@$CURRENT_USER.service > /dev/null 2>&1 || true
    endscript
}
EOF
    
    log_info "日志轮转配置已创建: $logrotate_file"
}

# 配置系统权限
configure_permissions() {
    log_step "配置系统权限..."
    
    # 添加用户到必要的组
    local groups=("audio" "video" "i2c" "gpio" "spi" "dialout")
    
    for group in "${groups[@]}"; do
        if getent group "$group" > /dev/null 2>&1; then
            if ! groups "$CURRENT_USER" | grep -q "\b$group\b"; then
                sudo usermod -a -G "$group" "$CURRENT_USER"
                log_info "已将用户 $CURRENT_USER 添加到 $group 组"
            else
                log_info "用户 $CURRENT_USER 已在 $group 组中"
            fi
        else
            log_warn "组 $group 不存在，跳过"
        fi
    done
    
    # 创建数据目录并设置权限
    mkdir -p "$CURRENT_DIR/src/data/logs"
    mkdir -p "$CURRENT_DIR/src/data/ai_memory"
    mkdir -p "$CURRENT_DIR/src/data/temp"
    
    chmod 755 "$CURRENT_DIR/src/data"
    chmod 755 "$CURRENT_DIR/src/data/logs"
    chmod 755 "$CURRENT_DIR/src/data/ai_memory"
    chmod 755 "$CURRENT_DIR/src/data/temp"
    
    log_info "数据目录权限配置完成"
}

# 测试服务配置
test_service_config() {
    log_step "测试服务配置..."
    
    local service_name="ai-desktop-pet@${CURRENT_USER}.service"
    
    # 重新加载systemd配置
    sudo systemctl daemon-reload
    
    # 检查服务文件语法
    if systemctl cat "$service_name" > /dev/null 2>&1; then
        log_info "服务文件语法正确"
    else
        log_error "服务文件语法错误"
        return 1
    fi
    
    # 检查依赖
    log_info "检查服务依赖..."
    systemctl list-dependencies "$service_name" --plain | head -10
    
    # 验证环境
    log_info "验证运行环境..."
    if [[ -f "$HOME_DIR/.ai_pet_env" ]]; then
        log_info "环境变量文件存在"
    else
        log_warn "环境变量文件不存在，请运行: cp ~/.ai_pet_env.example ~/.ai_pet_env"
    fi
    
    if [[ -d "$CURRENT_DIR/.venv" ]]; then
        log_info "Python虚拟环境存在"
    else
        log_error "Python虚拟环境不存在"
        return 1
    fi
    
    if [[ -f "$CURRENT_DIR/src/robot_voice_web_control.py" ]]; then
        log_info "主程序文件存在"
    else
        log_error "主程序文件不存在"
        return 1
    fi
    
    log_info "服务配置测试完成"
}

# 显示安装后信息
show_post_install_info() {
    local service_name="ai-desktop-pet@${CURRENT_USER}.service"
    
    echo
    echo "======================================"
    echo "🎉 systemd服务配置完成！"
    echo "======================================"
    echo
    echo "📋 服务信息:"
    echo "   服务名称: $service_name"
    echo "   配置文件: /etc/systemd/system/$service_name"
    echo "   工作目录: $CURRENT_DIR/src"
    echo "   运行用户: $CURRENT_USER"
    echo
    echo "🚀 启动服务:"
    echo "   ./start_ai_pet_service.sh"
    echo "   或者手动执行:"
    echo "   sudo systemctl enable $service_name"
    echo "   sudo systemctl start $service_name"
    echo
    echo "🔧 管理命令:"
    echo "   查看状态: ./check_ai_pet_service.sh"
    echo "   停止服务: ./stop_ai_pet_service.sh"
    echo "   查看日志: journalctl -u $service_name -f"
    echo "   重启服务: sudo systemctl restart $service_name"
    echo
    echo "📁 重要文件:"
    echo "   环境配置: ~/.ai_pet_env"
    echo "   日志目录: $CURRENT_DIR/src/data/logs/"
    echo "   数据目录: $CURRENT_DIR/src/data/"
    echo
    echo "⚠️  注意事项:"
    echo "   • 确保已配置API密钥 (~/.ai_pet_env)"
    echo "   • 确保硬件连接正确"
    echo "   • 首次启动可能需要较长时间"
    echo "   • 如果修改了组权限，可能需要重新登录"
    echo
    echo "🆘 故障排除:"
    echo "   • 查看服务状态: systemctl status $service_name"
    echo "   • 查看详细日志: journalctl -u $service_name -f"
    echo "   • 检查权限: groups $CURRENT_USER"
    echo "   • 测试手动启动: cd src && python3 robot_voice_web_control.py"
    echo
}

# 主函数
main() {
    echo "======================================"
    echo "🔧 AI桌宠systemd服务配置"
    echo "======================================"
    echo
    
    check_root
    check_systemd
    get_system_info
    
    echo "即将配置systemd服务，这将需要sudo权限..."
    read -p "按Enter键继续，或Ctrl+C取消: "
    
    create_service_file
    create_service_scripts
    create_logrotate_config
    configure_permissions
    test_service_config
    show_post_install_info
    
    log_info "systemd服务配置完成！"
}

# 错误处理
trap 'log_error "配置过程中发生错误，请检查上面的错误信息"; exit 1' ERR

# 运行主程序
main "$@"