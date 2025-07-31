#!/bin/bash
"""
SSD1306显示器依赖安装脚本
安装必要的Python库和系统工具
"""

echo "🔧 安装SSD1306显示器依赖"
echo "=========================="

# 更新系统包
echo "📦 更新系统包..."
sudo apt update

# 安装I2C工具
echo "🔌 安装I2C工具..."
sudo apt install -y i2c-tools

# 安装Python图像处理库
echo "🖼️ 安装图像处理库..."
sudo apt install -y python3-pil python3-pip

# 安装字体支持
echo "🔤 安装中文字体..."
sudo apt install -y fonts-wqy-microhei fonts-wqy-zenhei

# 升级pip
echo "⬆️ 升级pip..."
python3 -m pip install --upgrade pip

# 安装Python依赖
echo "🐍 安装Python依赖..."
pip3 install adafruit-circuitpython-ssd1306
pip3 install luma.oled
pip3 install adafruit-circuitpython-busdevice
pip3 install adafruit-circuitpython-framebuf
pip3 install psutil

# 启用I2C接口
echo "🔌 配置I2C接口..."
if ! grep -q "i2c-dev" /etc/modules; then
    echo "i2c-dev" | sudo tee -a /etc/modules
fi

# 检查/boot/config.txt中的I2C设置
if ! grep -q "dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
    echo "⚠️ 已添加I2C配置到/boot/config.txt"
    REBOOT_NEEDED=true
fi

# 添加用户到i2c组
echo "👤 添加用户到i2c组..."
sudo usermod -a -G i2c $USER

# 检查I2C设备
echo "🔍 检查I2C设备..."
if command -v i2cdetect &> /dev/null; then
    echo "扫描I2C设备 (总线1):"
    sudo i2cdetect -y 1
else
    echo "i2cdetect命令不可用"
fi

echo ""
echo "✅ 依赖安装完成!"
echo ""
echo "📋 接下来的步骤:"
echo "1. 连接SSD1306显示器到树莓派:"
echo "   VCC -> 3.3V (Pin 1)"
echo "   GND -> GND (Pin 6)"  
echo "   SCL -> GPIO 3 (Pin 5)"
echo "   SDA -> GPIO 2 (Pin 3)"
echo ""
echo "2. 如果这是首次启用I2C，请重启系统:"
if [ "$REBOOT_NEEDED" = true ]; then
    echo "   sudo reboot"
    echo ""
    echo "3. 重启后运行测试程序:"
else
    echo ""
    echo "3. 运行测试程序:"
fi
echo "   python3 test_ssd1306_display.py"
echo ""
echo "4. 如果测试失败，请检查:"
echo "   - 硬件连接是否正确"
echo "   - I2C是否已启用: sudo raspi-config -> Interface Options -> I2C"
echo "   - 设备地址是否正确 (通常是0x3C或0x3D)"