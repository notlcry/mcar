#!/bin/bash
# API密钥配置脚本

echo "=== AI桌宠API密钥配置 ==="

# 检查是否存在配置文件
if [ ! -f ".ai_pet_env" ]; then
    if [ -f ".ai_pet_env.example" ]; then
        cp .ai_pet_env.example .ai_pet_env
        echo "已创建配置文件 .ai_pet_env"
    else
        echo "错误: 找不到示例配置文件"
        exit 1
    fi
fi

echo "请配置以下API密钥:"
echo ""

# 配置Gemini API密钥
echo "1. Google Gemini API密钥"
echo "   获取地址: https://makersuite.google.com/app/apikey"
read -p "   请输入Gemini API密钥: " gemini_key

if [ ! -z "$gemini_key" ]; then
    sed -i.bak "s/your_gemini_api_key_here/$gemini_key/" .ai_pet_env
    echo "   ✅ Gemini API密钥已配置"
else
    echo "   ⚠️ 跳过Gemini API密钥配置"
fi

echo ""

# 配置Picovoice密钥（可选）
echo "2. Picovoice访问密钥（可选，用于自定义唤醒词）"
echo "   获取地址: https://console.picovoice.ai/"
read -p "   请输入Picovoice密钥（可选，直接回车跳过）: " picovoice_key

if [ ! -z "$picovoice_key" ]; then
    sed -i.bak "s/your_picovoice_access_key_here/$picovoice_key/" .ai_pet_env
    echo "   ✅ Picovoice密钥已配置"
else
    echo "   ⚠️ 跳过Picovoice密钥配置"
fi

# 清理备份文件
rm -f .ai_pet_env.bak

echo ""
echo "=== 配置完成 ==="
echo "请运行以下命令加载环境变量:"
echo "source .ai_pet_env"
echo ""
echo "然后可以启动AI桌宠系统:"
echo "cd src && python3 robot_voice_web_control.py"