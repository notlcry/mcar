#!/bin/bash
"""
唤醒词测试启动脚本 - 加载环境变量并运行测试
"""

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 加载环境变量
echo "🔧 加载环境变量..."
source .ai_pet_env

# 验证关键环境变量
echo "📋 环境变量检查:"
echo "   PICOVOICE_ACCESS_KEY: ${PICOVOICE_ACCESS_KEY:0:10}..."
echo "   AZURE_TTS_API_KEY: ${AZURE_TTS_API_KEY:0:10}..."
echo "   GEMINI_API_KEY: ${GEMINI_API_KEY:0:10}..."

# 切换到src目录
cd src

# 运行唤醒词测试
echo ""
echo "🎤 开始唤醒词检测测试..."
python3 test_wake_word_only.py