#!/bin/bash
# AI桌宠无torch快速安装脚本
# 跳过torch依赖，使用PocketSphinx语音识别

set -e

echo "🚀 AI桌宠快速安装（无torch版本）"
echo "=================================="
echo "功能包括："
echo "✅ AI对话（Google Gemini）"
echo "✅ 语音识别（PocketSphinx）"
echo "✅ 语音合成（Edge-TTS）"
echo "✅ 机器人控制（GPIO/I2C）"
echo "✅ Web界面控制"
echo "✅ 情感表达（OLED）"
echo "❌ Whisper高质量识别（需要torch）"
echo

# 激活虚拟环境
if [[ -f ".venv/bin/activate" ]]; then
    echo "激活虚拟环境..."
    source .venv/bin/activate
else
    echo "创建虚拟环境..."
    python3 -m venv .venv
    source .venv/bin/activate
fi

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo "安装依赖包..."
pip install -r requirements_no_torch.txt

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
    print('✅ 摄像头支持')
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

try:
    from luma.oled.device import ssd1306
    print('✅ OLED显示')
except Exception as e:
    print(f'❌ OLED显示: {e}')
"

echo
echo "=============================="
echo "🎉 安装完成！"
echo "=============================="
echo
echo "接下来的步骤："
echo "1. 配置API密钥:"
echo "   ./setup_api_keys.sh"
echo
echo "2. 启动系统:"
echo "   cd src && python3 robot_voice_web_control.py"
echo
echo "3. 访问Web界面:"
echo "   http://树莓派IP:5000"
echo
echo "注意："
echo "• 此版本使用PocketSphinx进行语音识别"
echo "• 如需更高质量的Whisper识别，可运行:"
echo "  ./install_torch_raspberry_pi.sh"
echo
echo "• 语音识别效果对比："
echo "  PocketSphinx: 快速，轻量，中等准确度"
echo "  Whisper: 慢速，重型，高准确度"
echo