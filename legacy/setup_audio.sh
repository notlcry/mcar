#!/bin/bash
# 音频系统配置脚本 - 幂等安装
# 可以重复运行，不会破坏现有配置

echo "🔧 配置音频系统..."

# 检查并安装必要的音频包
echo "检查音频包..."
PACKAGES_TO_INSTALL=""

if ! dpkg -l | grep -q alsa-utils; then
    PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL alsa-utils"
fi

if ! dpkg -l | grep -q pulseaudio; then
    PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL pulseaudio"
fi

if [ -n "$PACKAGES_TO_INSTALL" ]; then
    echo "安装缺失的包: $PACKAGES_TO_INSTALL"
    sudo apt-get update -qq
    sudo apt-get install -y $PACKAGES_TO_INSTALL
else
    echo "✅ 所有必要的音频包已安装"
fi

# 配置ALSA
echo "配置ALSA..."
if [ -f ~/.asoundrc ]; then
    # 备份现有配置
    if ! cmp -s .asoundrc ~/.asoundrc; then
        cp ~/.asoundrc ~/.asoundrc.backup.$(date +%s)
        echo "已备份现有ALSA配置"
    fi
fi

# 复制新配置
cp .asoundrc ~/.asoundrc
echo "✅ ALSA配置已更新"

# 重启音频服务
echo "重启音频服务..."
pulseaudio --kill 2>/dev/null || true
sudo alsa force-reload 2>/dev/null || true
sleep 2

echo "✅ 音频系统配置完成"

# 验证配置
echo "验证音频配置..."
if arecord -l >/dev/null 2>&1; then
    echo "✅ ALSA录音设备可用"
else
    echo "⚠️  ALSA录音设备检查失败"
fi