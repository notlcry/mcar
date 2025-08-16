#!/bin/bash
# 设置中文唤醒词支持 - 幂等脚本

echo "🇨🇳 设置中文唤醒词支持..."

# 检查是否有中文唤醒词文件
if [ ! -f "wake_words/kk_zh_raspberry-pi_v3_0_0.ppn" ]; then
    echo "❌ 未找到中文唤醒词文件"
    exit 1
fi

echo "✅ 找到中文唤醒词文件: kk_zh_raspberry-pi_v3_0_0.ppn"

# 创建模型目录
mkdir -p models/porcupine

# 下载中文语言模型
echo "📦 下载Porcupine中文语言模型..."

CHINESE_MODEL_URL="https://github.com/Picovoice/porcupine/raw/master/lib/common/porcupine_params_zh.pv"
CHINESE_MODEL_PATH="models/porcupine/porcupine_params_zh.pv"

if [ ! -f "$CHINESE_MODEL_PATH" ]; then
    echo "🔄 下载中文模型..."
    wget -O "$CHINESE_MODEL_PATH" "$CHINESE_MODEL_URL"
    
    if [ $? -eq 0 ]; then
        echo "✅ 中文模型下载成功"
    else
        echo "❌ 中文模型下载失败"
        exit 1
    fi
else
    echo "✅ 中文模型已存在"
fi

echo "🎉 中文唤醒词支持设置完成！"
echo ""
echo "💡 使用说明:"
echo "• 中文唤醒词: 'kk' (你好)"
echo "• 现在可以使用中文唤醒AI桌宠了"
echo ""
echo "🔧 如果仍有问题，请检查:"
echo "• PICOVOICE_ACCESS_KEY 是否正确设置"
echo "• 网络连接是否正常"