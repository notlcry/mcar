#!/bin/bash
# 修复安装问题脚本

set -e

echo "🔧 修复AI桌宠安装问题"
echo "====================="
echo

# 1. 修复Google Generative AI的GLIBC问题
echo "1. 修复Google Generative AI依赖问题..."
echo "   问题：GLIBC版本不兼容"
echo "   解决：重新安装兼容版本"

# 卸载有问题的版本
pip3 uninstall -y google-generativeai grpcio grpcio-status

# 安装兼容的版本
echo "   安装兼容版本..."
pip3 install --no-cache-dir google-generativeai==0.3.2
pip3 install --no-cache-dir grpcio==1.48.2

echo "   ✅ Google Generative AI修复完成"
echo

# 2. 修复I2C接口问题
echo "2. 修复I2C接口问题..."

# 检查I2C是否在config.txt中启用
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "   启用I2C接口..."
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
    echo "   ✅ I2C已在配置文件中启用"
else
    echo "   ✅ I2C已在配置文件中启用"
fi

# 加载I2C模块
echo "   加载I2C模块..."
sudo modprobe i2c-dev
sudo modprobe i2c-bcm2835

# 检查I2C设备
if [ -c /dev/i2c-1 ]; then
    echo "   ✅ I2C设备节点存在"
else
    echo "   ❌ I2C设备节点不存在，需要重启"
fi

# 添加用户到i2c组
sudo usermod -a -G i2c $USER
echo "   ✅ 用户已添加到i2c组"
echo

# 3. 修复音频设备问题
echo "3. 修复音频设备问题..."

# 检查音频模块
echo "   加载音频模块..."
sudo modprobe snd-usb-audio

# 检查USB设备
echo "   检查USB音频设备..."
lsusb | grep -i audio && echo "   ✅ 找到USB音频设备" || echo "   ⚠️ 未找到USB音频设备"

# 检查ALSA配置
echo "   检查ALSA音频配置..."
if command -v arecord >/dev/null 2>&1; then
    arecord -l | head -5
else
    echo "   ❌ arecord命令不可用"
fi

# 添加用户到audio组
sudo usermod -a -G audio $USER
echo "   ✅ 用户已添加到audio组"
echo

# 4. 测试修复结果
echo "4. 测试修复结果..."
echo

python3 -c "
print('=== 修复后测试 ===')

# 测试Google Generative AI
try:
    import google.generativeai as genai
    print('✅ Google Generative AI: 修复成功')
except Exception as e:
    print(f'❌ Google Generative AI: {e}')

# 测试I2C（需要重启后才能完全生效）
import subprocess
try:
    result = subprocess.run(['i2cdetect', '-y', '1'], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print('✅ I2C接口: 可用')
    else:
        print('⚠️ I2C接口: 需要重启后生效')
except Exception as e:
    print(f'⚠️ I2C接口: 需要重启后生效 ({e})')

# 测试音频
try:
    result = subprocess.run(['arecord', '-l'], capture_output=True, text=True, timeout=5)
    if 'card' in result.stdout:
        print('✅ 音频录制设备: 可用')
    else:
        print('❌ 音频录制设备: 请检查麦克风连接')
except Exception as e:
    print(f'❌ 音频录制设备: {e}')
"

echo
echo "=============================="
echo "🎉 修复完成！"
echo "=============================="
echo
echo "修复内容："
echo "✅ Google Generative AI - 安装兼容版本"
echo "✅ I2C接口 - 启用并配置权限"
echo "✅ 音频权限 - 添加用户到audio组"
echo
echo "⚠️  重要提醒："
echo "1. 请重新登录或重启树莓派以应用权限更改"
echo "2. 如果I2C仍不工作，请重启后再测试"
echo "3. 确保USB麦克风已正确连接"
echo
echo "重启后测试："
echo "python3 src/test_hardware.py"
echo
echo "如果一切正常，可以启动系统："
echo "cd src && python3 robot_voice_web_control.py"
echo