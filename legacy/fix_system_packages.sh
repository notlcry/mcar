#!/bin/bash
# 修复系统包安装问题

set -e

echo "🔧 修复系统包安装问题"
echo "===================="
echo

# 安装缺失的系统包
echo "安装缺失的系统包..."
sudo apt update
sudo apt install -y \
    python3-opencv \
    python3-numpy \
    python3-rpi.gpio \
    python3-smbus \
    i2c-tools \
    python3-pyaudio

echo "✅ 系统包安装完成"
echo

# 验证安装
echo "验证系统包安装..."
python3 -c "
print('=== 系统包验证 ===')

try:
    import cv2
    print(f'✅ OpenCV: {cv2.__version__}')
except Exception as e:
    print(f'❌ OpenCV: {e}')

try:
    import numpy as np
    print(f'✅ NumPy: {np.__version__}')
except Exception as e:
    print(f'❌ NumPy: {e}')

try:
    import RPi.GPIO as GPIO
    print('✅ RPi.GPIO: 可用')
except Exception as e:
    print(f'❌ RPi.GPIO: {e}')

try:
    import smbus
    print('✅ SMBus (I2C): 可用')
except Exception as e:
    print(f'❌ SMBus (I2C): {e}')

try:
    import pyaudio
    print('✅ PyAudio: 可用')
except Exception as e:
    print(f'❌ PyAudio: {e}')
"

echo
echo "测试硬件接口..."

# 测试I2C
echo "测试I2C接口..."
if command -v i2cdetect >/dev/null 2>&1; then
    i2cdetect -y 1 && echo "✅ I2C接口可用" || echo "❌ I2C接口不可用"
else
    echo "❌ i2cdetect命令不可用"
fi

# 测试音频
echo "测试音频设备..."
if command -v arecord >/dev/null 2>&1; then
    arecord -l | head -3 && echo "✅ 音频设备检测完成" || echo "❌ 音频设备检测失败"
else
    echo "❌ arecord命令不可用"
fi

echo
echo "=============================="
echo "🎉 系统包修复完成！"
echo "=============================="
echo
echo "现在可以测试硬件："
echo "python3 src/test_hardware.py"
echo
echo "如果测试通过，可以启动系统："
echo "cd src && python3 robot_voice_web_control.py"
echo