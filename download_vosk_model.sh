#!/bin/bash
# 下载Vosk中文语音识别模型

echo "🔽 下载Vosk中文语音识别模型"
echo "=================================="

# 创建模型目录
mkdir -p models
cd models

# 检查是否已经有模型
if [ -d "vosk-model-small-cn-0.22" ]; then
    echo "✅ 小型中文模型已存在"
    SMALL_EXISTS=true
else
    SMALL_EXISTS=false
fi

if [ -d "vosk-model-cn-0.22" ]; then
    echo "✅ 完整中文模型已存在"
    FULL_EXISTS=true
else
    FULL_EXISTS=false
fi

# 如果都不存在，询问用户要下载哪个
if [ "$SMALL_EXISTS" = false ] && [ "$FULL_EXISTS" = false ]; then
    echo
    echo "请选择要下载的模型:"
    echo "1. 小型中文模型 (约40MB, 推荐用于树莓派)"
    echo "2. 完整中文模型 (约1.2GB, 识别精度更高)"
    echo "3. 两个都下载"
    echo
    read -p "请输入选择 (1/2/3): " choice
    
    case $choice in
        1)
            DOWNLOAD_SMALL=true
            DOWNLOAD_FULL=false
            ;;
        2)
            DOWNLOAD_SMALL=false
            DOWNLOAD_FULL=true
            ;;
        3)
            DOWNLOAD_SMALL=true
            DOWNLOAD_FULL=true
            ;;
        *)
            echo "无效选择，默认下载小型模型"
            DOWNLOAD_SMALL=true
            DOWNLOAD_FULL=false
            ;;
    esac
else
    DOWNLOAD_SMALL=false
    DOWNLOAD_FULL=false
fi

# 下载小型模型
if [ "$DOWNLOAD_SMALL" = true ]; then
    echo
    echo "📥 下载小型中文模型 (约40MB)..."
    
    if command -v wget >/dev/null 2>&1; then
        wget -c https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip
    elif command -v curl >/dev/null 2>&1; then
        curl -L -C - -O https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip
    else
        echo "❌ 需要wget或curl来下载文件"
        exit 1
    fi
    
    if [ -f "vosk-model-small-cn-0.22.zip" ]; then
        echo "📦 解压小型模型..."
        unzip -q vosk-model-small-cn-0.22.zip
        
        if [ -d "vosk-model-small-cn-0.22" ]; then
            echo "✅ 小型中文模型下载并解压成功"
            rm vosk-model-small-cn-0.22.zip
        else
            echo "❌ 小型模型解压失败"
        fi
    else
        echo "❌ 小型模型下载失败"
    fi
fi

# 下载完整模型
if [ "$DOWNLOAD_FULL" = true ]; then
    echo
    echo "📥 下载完整中文模型 (约1.2GB)..."
    echo "⚠️  这可能需要较长时间，请耐心等待..."
    
    if command -v wget >/dev/null 2>&1; then
        wget -c https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip
    elif command -v curl >/dev/null 2>&1; then
        curl -L -C - -O https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip
    else
        echo "❌ 需要wget或curl来下载文件"
        exit 1
    fi
    
    if [ -f "vosk-model-cn-0.22.zip" ]; then
        echo "📦 解压完整模型..."
        unzip -q vosk-model-cn-0.22.zip
        
        if [ -d "vosk-model-cn-0.22" ]; then
            echo "✅ 完整中文模型下载并解压成功"
            rm vosk-model-cn-0.22.zip
        else
            echo "❌ 完整模型解压失败"
        fi
    else
        echo "❌ 完整模型下载失败"
    fi
fi

# 返回上级目录
cd ..

# 检查最终结果
echo
echo "=================================="
echo "📊 模型下载结果:"

if [ -d "models/vosk-model-small-cn-0.22" ]; then
    echo "✅ 小型中文模型: models/vosk-model-small-cn-0.22"
    SMALL_SIZE=$(du -sh models/vosk-model-small-cn-0.22 2>/dev/null | cut -f1)
    echo "   大小: $SMALL_SIZE"
fi

if [ -d "models/vosk-model-cn-0.22" ]; then
    echo "✅ 完整中文模型: models/vosk-model-cn-0.22"
    FULL_SIZE=$(du -sh models/vosk-model-cn-0.22 2>/dev/null | cut -f1)
    echo "   大小: $FULL_SIZE"
fi

# 安装Vosk Python库
echo
echo "📦 安装Vosk Python库..."
pip3 install vosk

if [ $? -eq 0 ]; then
    echo "✅ Vosk库安装成功"
else
    echo "❌ Vosk库安装失败"
    echo "请手动运行: pip3 install vosk"
fi

echo
echo "🎉 Vosk中文语音识别配置完成！"
echo
echo "💡 使用说明:"
echo "• Vosk现在是主要的中文语音识别引擎"
echo "• 支持完全离线的中文语音识别"
echo "• 识别精度比PocketSphinx高很多"
echo
echo "🚀 现在可以重新启动AI桌宠系统:"
echo "   ./start_ai_pet_quiet.sh"