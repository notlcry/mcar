#!/bin/bash
# 树莓派4B安装修复脚本
# 解决torch依赖问题

set -e

echo "🔧 树莓派4B安装修复脚本"
echo "=========================="
echo

# 检查Python版本
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Python版本: $PYTHON_VERSION"

# 检查内存
TOTAL_MEM=$(free -m | awk 'NR==2{print $2}')
echo "总内存: ${TOTAL_MEM}MB"

echo

# 激活虚拟环境
if [[ -f ".venv/bin/activate" ]]; then
    echo "激活虚拟环境..."
    source .venv/bin/activate
else
    echo "❌ 未找到虚拟环境，请先创建："
    echo "python3 -m venv .venv"
    exit 1
fi

echo "✅ 虚拟环境已激活"
echo

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装基础依赖（不包含torch）
echo "安装基础依赖（跳过torch）..."
pip install -r requirements_pi4b.txt

echo
echo "🎉 基础依赖安装完成！"
echo

# 询问是否安装torch
echo "是否安装PyTorch和Whisper？"
echo "注意：这将需要较长时间（30分钟-1小时）"
echo "如果只是测试基础功能，可以暂时跳过"
echo

read -p "安装PyTorch? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "开始安装PyTorch..."
    
    # 检查架构
    ARCH=$(uname -m)
    echo "系统架构: $ARCH"
    
    if [[ "$ARCH" == "aarch64" ]]; then
        echo "安装ARM64版本的PyTorch..."
        pip install torch==2.0.1 --index-url https://download.pytorch.org/whl/cpu
        pip install torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cpu
    else
        echo "安装ARM32版本的PyTorch..."
        pip install torch==1.13.1 --index-url https://download.pytorch.org/whl/cpu
        pip install torchaudio==0.13.1 --index-url https://download.pytorch.org/whl/cpu
    fi
    
    echo "安装Whisper..."
    pip install openai-whisper
    
    echo "✅ PyTorch和Whisper安装完成"
else
    echo "⏭️  跳过PyTorch安装"
    echo "如需后续安装，运行: ./install_torch_raspberry_pi.sh"
fi

echo
echo "🧪 测试基础功能..."

# 测试配置系统
python3 -c "
import sys
sys.path.append('src')

try:
    from config import ConfigManager
    config = ConfigManager('src/ai_pet_config.json')
    print('✅ 配置系统正常')
except Exception as e:
    print(f'❌ 配置系统错误: {e}')

try:
    import RPi.GPIO as GPIO
    print('✅ GPIO库正常')
except Exception as e:
    print(f'❌ GPIO库错误: {e}')

try:
    import cv2
    print('✅ OpenCV正常')
except Exception as e:
    print(f'❌ OpenCV错误: {e}')

try:
    import google.generativeai as genai
    print('✅ Gemini API库正常')
except Exception as e:
    print(f'❌ Gemini API库错误: {e}')

try:
    import edge_tts
    print('✅ Edge-TTS正常')
except Exception as e:
    print(f'❌ Edge-TTS错误: {e}')
"

echo
echo "=============================="
echo "🎉 修复完成！"
echo "=============================="
echo
echo "接下来的步骤："
echo "1. 配置API密钥: ./setup_api_keys.sh"
echo "2. 启动系统: cd src && python3 robot_voice_web_control.py"
echo
echo "如果需要完整的AI功能（包括Whisper），请稍后运行："
echo "./install_torch_raspberry_pi.sh"
echo