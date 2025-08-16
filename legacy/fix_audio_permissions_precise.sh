#!/bin/bash
# 精确修复音频权限问题

echo "🔧 精确修复音频权限问题..."
echo "已确认: root可以播放，barry用户不能播放 = 权限问题"

USER_NAME="barry"

echo "👤 目标用户: $USER_NAME"

# 1. 添加用户到audio组
echo "🔄 添加用户到audio组..."
sudo usermod -a -G audio $USER_NAME
if [ $? -eq 0 ]; then
    echo "✅ 用户已添加到audio组"
else
    echo "❌ 添加到audio组失败"
fi

# 2. 检查并修复设备权限
echo "🔄 修复音频设备权限..."
if [ -d "/dev/snd" ]; then
    # 设置正确的组和权限
    sudo chgrp -R audio /dev/snd/*
    sudo chmod -R 664 /dev/snd/*
    echo "✅ /dev/snd 权限已修复"
else
    echo "❌ /dev/snd 目录不存在"
fi

# 3. 创建udev规则确保权限持久化
echo "🔄 创建udev规则..."
sudo tee /etc/udev/rules.d/99-audio-permissions.rules > /dev/null << 'EOF'
# 音频设备权限规则
SUBSYSTEM=="sound", GROUP="audio", MODE="0664"
KERNEL=="controlC[0-9]*", GROUP="audio", MODE="0664"
KERNEL=="pcmC[0-9]*D[0-9]*[cp]", GROUP="audio", MODE="0664"
KERNEL=="midiC[0-9]*D[0-9]*", GROUP="audio", MODE="0664"
KERNEL=="timer", GROUP="audio", MODE="0664"
KERNEL=="seq", GROUP="audio", MODE="0664"
EOF

if [ $? -eq 0 ]; then
    echo "✅ udev规则已创建"
    
    # 重新加载udev规则
    sudo udevadm control --reload-rules
    sudo udevadm trigger --subsystem-match=sound
    echo "✅ udev规则已重新加载"
else
    echo "❌ 创建udev规则失败"
fi

# 4. 应用新的组权限（避免重新登录）
echo "🔄 应用新的组权限..."
echo "💡 方法1: 使用newgrp命令"
echo "   运行: newgrp audio"
echo "   然后测试: aplay ~/test.wav"

echo "💡 方法2: 使用sg命令直接测试"
echo "   运行: sg audio -c 'aplay ~/test.wav'"

# 5. 显示当前状态
echo -e "\n📋 当前用户组:"
groups $USER_NAME

echo -e "\n📋 音频设备权限:"
ls -la /dev/snd/ | head -5

echo -e "\n🎯 测试命令:"
echo "1. sg audio -c 'aplay ~/test.wav'  # 临时测试"
echo "2. newgrp audio                     # 切换到audio组"
echo "3. sudo reboot                      # 重启系统（推荐）"

echo -e "\n🎉 权限修复完成！"