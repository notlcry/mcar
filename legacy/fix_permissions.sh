#!/bin/bash
# 权限修复脚本 - 解决GPIO、I2C、音频权限问题

echo "🔐 修复用户权限问题"
echo "=================="
echo

CURRENT_USER=$(whoami)
echo "当前用户: $CURRENT_USER"

# 检查当前用户组
echo "当前用户组:"
groups $CURRENT_USER

echo
echo "添加用户到必要的组..."

# 添加到各种硬件组
sudo usermod -a -G gpio $CURRENT_USER
sudo usermod -a -G i2c $CURRENT_USER
sudo usermod -a -G spi $CURRENT_USER
sudo usermod -a -G audio $CURRENT_USER
sudo usermod -a -G video $CURRENT_USER
sudo usermod -a -G dialout $CURRENT_USER

echo "✅ 用户组权限已更新"

# 设置GPIO权限规则
echo
echo "设置GPIO权限规则..."
sudo tee /etc/udev/rules.d/99-gpio.rules > /dev/null << 'EOF'
SUBSYSTEM=="gpio", KERNEL=="gpiochip*", ACTION=="add", PROGRAM="/bin/sh -c 'chown root:gpio /sys/class/gpio/export /sys/class/gpio/unexport ; chmod 220 /sys/class/gpio/export /sys/class/gpio/unexport'"
SUBSYSTEM=="gpio", KERNEL=="gpio*", ACTION=="add", PROGRAM="/bin/sh -c 'chown root:gpio /sys%p/active_low /sys%p/direction /sys%p/edge /sys%p/value ; chmod 660 /sys%p/active_low /sys%p/direction /sys%p/edge /sys%p/value'"
EOF

# 设置I2C权限
echo "设置I2C权限..."
sudo tee /etc/udev/rules.d/99-i2c.rules > /dev/null << 'EOF'
KERNEL=="i2c-[0-9]*", GROUP="i2c", MODE="0664"
EOF

# 重新加载udev规则
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "✅ 硬件权限规则已设置"

# 修复项目文件权限
echo
echo "修复项目文件权限..."
sudo chown -R $CURRENT_USER:$CURRENT_USER .
chmod +x *.sh

echo "✅ 项目文件权限已修复"

echo
echo "=============================="
echo "🎉 权限修复完成！"
echo "=============================="
echo
echo "⚠️  重要：请重新登录或重启以应用权限更改"
echo
echo "重启命令："
echo "sudo reboot"
echo
echo "重启后验证："
echo "groups \$USER  # 检查用户组"
echo "python3 src/test_hardware.py  # 测试硬件"
echo
echo "如果一切正常，启动系统："
echo "cd src && python3 robot_voice_web_control.py"
echo