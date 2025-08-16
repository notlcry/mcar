#!/bin/bash
# 修复音频权限问题 - 幂等脚本

echo "🔧 修复音频权限问题..."

# 获取当前用户
CURRENT_USER=$(whoami)
echo "👤 当前用户: $CURRENT_USER"

# 检查并添加用户到音频相关组
echo "📋 检查用户组..."

# 音频相关的组
AUDIO_GROUPS=("audio" "pulse" "pulse-access")

for group in "${AUDIO_GROUPS[@]}"; do
    if getent group "$group" > /dev/null 2>&1; then
        echo "✅ 组 $group 存在"
        
        # 检查用户是否已在组中
        if groups "$CURRENT_USER" | grep -q "\b$group\b"; then
            echo "   ✅ 用户 $CURRENT_USER 已在 $group 组中"
        else
            echo "   🔄 添加用户 $CURRENT_USER 到 $group 组..."
            sudo usermod -a -G "$group" "$CURRENT_USER"
            if [ $? -eq 0 ]; then
                echo "   ✅ 成功添加到 $group 组"
            else
                echo "   ❌ 添加到 $group 组失败"
            fi
        fi
    else
        echo "⚠️  组 $group 不存在，跳过"
    fi
done

# 检查音频设备权限
echo -e "\n🔍 检查音频设备权限..."

AUDIO_DEVICES=("/dev/snd" "/dev/dsp" "/dev/audio")

for device in "${AUDIO_DEVICES[@]}"; do
    if [ -e "$device" ]; then
        echo "📱 设备 $device:"
        ls -la "$device"
        
        # 如果是目录，检查内部文件
        if [ -d "$device" ]; then
            echo "   内部文件:"
            ls -la "$device"/ | head -5
        fi
    else
        echo "⚠️  设备 $device 不存在"
    fi
done

# 修复设备权限
echo -e "\n🔧 修复设备权限..."

if [ -d "/dev/snd" ]; then
    echo "🔄 修复 /dev/snd 权限..."
    sudo chmod -R 666 /dev/snd/* 2>/dev/null || true
    sudo chgrp -R audio /dev/snd/* 2>/dev/null || true
    echo "✅ /dev/snd 权限已修复"
fi

# 重启音频服务
echo -e "\n🔄 重启音频服务..."

services=("alsa-state" "sound")

for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service" 2>/dev/null; then
        echo "🔄 重启 $service 服务..."
        sudo systemctl restart "$service"
        if [ $? -eq 0 ]; then
            echo "✅ $service 服务重启成功"
        else
            echo "❌ $service 服务重启失败"
        fi
    else
        echo "⚠️  $service 服务未运行或不存在"
    fi
done

# 加载音频模块
echo -e "\n🔄 加载音频模块..."

modules=("snd_bcm2835" "snd_pcm" "snd_mixer_oss")

for module in "${modules[@]}"; do
    if lsmod | grep -q "$module"; then
        echo "✅ 模块 $module 已加载"
    else
        echo "🔄 加载模块 $module..."
        sudo modprobe "$module" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "✅ 模块 $module 加载成功"
        else
            echo "⚠️  模块 $module 加载失败或不存在"
        fi
    fi
done

# 设置音量和取消静音
echo -e "\n🔊 设置音频参数..."

# 尝试设置音量
if command -v amixer &> /dev/null; then
    echo "🔄 设置音量..."
    
    # 获取可用的控制器
    controls=$(amixer controls 2>/dev/null | head -5)
    echo "可用控制器:"
    echo "$controls"
    
    # 尝试设置常见的音量控制
    volume_controls=("PCM" "Master" "Headphone" "Speaker")
    
    for control in "${volume_controls[@]}"; do
        if amixer get "$control" &>/dev/null; then
            echo "🔄 设置 $control 音量到 80%..."
            amixer set "$control" 80% unmute &>/dev/null
            if [ $? -eq 0 ]; then
                echo "✅ $control 设置成功"
            fi
        fi
    done
else
    echo "⚠️  amixer 命令不可用"
fi

echo -e "\n🎉 音频权限修复完成！"
echo -e "\n💡 重要提示:"
echo "• 需要重新登录或重启系统使组权限生效"
echo "• 如果仍有问题，请运行: newgrp audio"
echo "• 或者重启系统: sudo reboot"

echo -e "\n📋 当前用户组:"
groups "$CURRENT_USER"

echo -e "\n🧪 建议测试命令:"
echo "• python3 test_audio_output_fixed.py"
echo "• aplay /usr/share/sounds/alsa/Front_Left.wav"