#!/bin/bash
# 创建可工作的ALSA配置

echo "🔧 创建可工作的ALSA配置..."

# 备份现有配置
if [ -f ".asoundrc" ]; then
    cp .asoundrc .asoundrc.backup
    echo "✅ 已备份现有配置到 .asoundrc.backup"
fi

# 创建最简单的配置
cat > .asoundrc << 'EOF'
# 最简单的ALSA配置 - 直接指定设备
defaults.pcm.card 0
defaults.pcm.device 0
defaults.ctl.card 0
EOF

echo "✅ 创建了最简单的ALSA配置"
echo "📄 配置内容:"
cat .asoundrc

echo -e "\n🧪 测试播放..."
if aplay ~/test.wav 2>/dev/null; then
    echo "✅ 简单配置工作正常！"
else
    echo "❌ 简单配置仍然失败，尝试更直接的方法..."
    
    # 创建更直接的配置
    cat > .asoundrc << 'EOF'
# 直接硬件访问配置
pcm.!default "hw:0,0"
ctl.!default "hw:0"
EOF
    
    echo "📄 尝试直接硬件配置:"
    cat .asoundrc
    
    echo -e "\n🧪 再次测试播放..."
    if aplay ~/test.wav 2>/dev/null; then
        echo "✅ 直接硬件配置工作正常！"
    else
        echo "❌ 直接硬件配置也失败"
        echo "💡 可能需要删除配置文件，使用系统默认"
        
        # 尝试删除配置文件
        rm -f .asoundrc
        echo "🗑️  已删除 .asoundrc，使用系统默认配置"
        
        echo -e "\n🧪 测试系统默认配置..."
        if aplay ~/test.wav 2>/dev/null; then
            echo "✅ 系统默认配置工作正常！"
            echo "💡 建议不使用自定义 .asoundrc 配置"
        else
            echo "❌ 系统默认配置也失败"
            echo "💡 只能使用 aplay -D hw:0,0 的方式播放"
            
            # 恢复备份
            if [ -f ".asoundrc.backup" ]; then
                mv .asoundrc.backup .asoundrc
                echo "🔄 已恢复原始配置"
            fi
        fi
    fi
fi

echo -e "\n🎯 结论:"
echo "• 硬件播放正常: aplay -D hw:0,0 ~/test.wav"
echo "• 如果默认配置不工作，Python库可以指定设备"