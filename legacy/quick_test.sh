#!/bin/bash
# 快速测试脚本 - 直接加载当前目录的环境变量

# 加载环境变量
source .ai_pet_env

echo "======================================"
echo "🧪 快速系统测试"
echo "======================================"

echo "1. 环境变量检查:"
echo "GEMINI_API_KEY: ${GEMINI_API_KEY:0:20}..."
echo "PICOVOICE_ACCESS_KEY: ${PICOVOICE_ACCESS_KEY:0:20}..."

echo
echo "2. 测试Porcupine:"
python3 -c "
import os
import pvporcupine

access_key = os.getenv('PICOVOICE_ACCESS_KEY')
print(f'Access Key: {access_key[:20] if access_key else \"未设置\"}...')

try:
    porcupine = pvporcupine.create(
        access_key=access_key,
        keywords=['picovoice']
    )
    print('✓ Porcupine初始化成功')
    porcupine.delete()
except Exception as e:
    print(f'✗ Porcupine初始化失败: {e}')
"

echo
echo "3. 测试Gemini API:"
python3 -c "
import os
import google.generativeai as genai

api_key = os.getenv('GEMINI_API_KEY')
print(f'API Key: {api_key[:20] if api_key else \"未设置\"}...')

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content('Hello, reply with just \"OK\"')
    print('✓ Gemini API连接成功')
    print(f'  回复: {response.text}')
except Exception as e:
    print(f'✗ Gemini API测试失败: {e}')
"

echo
echo "4. 测试pygame音频:"
python3 -c "
import pygame
try:
    pygame.mixer.init()
    print('✓ pygame音频系统正常')
    pygame.mixer.quit()
except Exception as e:
    print(f'✗ pygame音频系统异常: {e}')
"

echo
echo "======================================"
echo "✅ 快速测试完成"
echo "======================================"
echo
echo "如果所有测试都通过，可以启动系统:"
echo "cd src && python3 robot_voice_web_control.py"