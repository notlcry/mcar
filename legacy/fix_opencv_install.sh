#!/bin/bash
# 修复OpenCV安装问题的脚本

set -e

echo "🔧 修复OpenCV安装问题"
echo "====================="
echo

# 停止当前安装
echo "停止当前pip安装进程..."
pkill -f "pip install" || true

# 清理pip缓存
echo "清理pip缓存..."
pip cache purge

# 安装系统OpenCV
echo "安装系统OpenCV包..."
sudo apt update
sudo apt install -y python3-opencv

# 验证系统OpenCV
echo "验证系统OpenCV..."
python3 -c "
import cv2
print(f'OpenCV版本: {cv2.__version__}')
print('✅ 系统OpenCV安装成功')
"

# 继续安装其他依赖（跳过OpenCV）
echo "安装其他依赖包..."
pip install -r requirements_pi_fixed.txt

echo
echo "🧪 测试安装..."

# 测试核心功能
python3 -c "
import sys
sys.path.append('src')

print('测试核心组件...')

try:
    from config import ConfigManager
    print('✅ 配置系统')
except Exception as e:
    print(f'❌ 配置系统: {e}')

try:
    import RPi.GPIO as GPIO
    print('✅ GPIO控制')
except Exception as e:
    print(f'❌ GPIO控制: {e}')

try:
    import cv2
    print(f'✅ 摄像头支持 (OpenCV {cv2.__version__})')
except Exception as e:
    print(f'❌ 摄像头支持: {e}')

try:
    import google.generativeai as genai
    print('✅ AI对话（Gemini）')
except Exception as e:
    print(f'❌ AI对话: {e}')

try:
    import speech_recognition as sr
    print('✅ 语音识别（PocketSphinx）')
except Exception as e:
    print(f'❌ 语音识别: {e}')

try:
    import edge_tts
    print('✅ 语音合成（Edge-TTS）')
except Exception as e:
    print(f'❌ 语音合成: {e}')

try:
    import pygame
    print('✅ 音频播放')
except Exception as e:
    print(f'❌ 音频播放: {e}')
"

echo
echo "=============================="
echo "🎉 修复完成！"
echo "=============================="
echo
echo "解决方案："
echo "• 使用系统预装的OpenCV (python3-opencv)"
echo "• 跳过编译opencv-python-headless"
echo "• 其他依赖正常安装"
echo
echo "接下来的步骤："
echo "1. 配置API密钥: ./setup_api_keys.sh"
echo "2. 启动系统: cd src && python3 robot_voice_web_control.py"
echo