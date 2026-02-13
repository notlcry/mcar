#!/bin/bash
# MCAR机器人主程序启动脚本

echo "🤖 启动MCAR机器人系统..."

# 设置环境变量
if [ -f ".ai_pet_env" ]; then
    source .ai_pet_env
    echo "✅ 环境变量已加载"
else
    echo "⚠️ 未找到.ai_pet_env文件"
fi

# 检查必要的API密钥
if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ 缺少GEMINI_API_KEY，请配置.ai_pet_env文件"
    exit 1
fi

if [ -z "$PICOVOICE_ACCESS_KEY" ]; then
    echo "⚠️ 缺少PICOVOICE_ACCESS_KEY，唤醒词功能将不可用"
fi

# 进入src目录
cd src

# 检查Python依赖
echo "🔍 检查依赖..."
python3 -c "import flask, RPi.GPIO" 2>/dev/null && echo "✅ 基础依赖正常" || echo "❌ 缺少基础依赖"

# 启动主程序
echo "🚀 启动机器人控制系统..."
python3 robot_voice_web_control.py

echo "⏹️ 机器人系统已停止"