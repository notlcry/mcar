#!/bin/bash
# 清理临时修复脚本

echo "🧹 清理临时修复脚本"
echo "=================================="

# 要清理的临时修复脚本列表
FIX_SCRIPTS=(
    "fix_audio_and_ai_issues.sh"
    "fix_pygame_system_step2b.sh"
    "fix_porcupine_step3.sh"
    "fix_porcupine_access_key_step4.sh"
    "fix_gemini_model_step5.sh"
    "fix_gemini_init_and_logs.py"
    "fix_alsa_simple.sh"
    "fix_microphone.sh"
    "fix_alsa_complete.sh"
    "fix_final_audio_issues.sh"
    "fix_alsa_clean.sh"
    "fix_audio_permissions.sh"
    "fix_sdl2_step2.sh"
    "fix_usb_microphone.sh"
    "fix_sample_rate_issue.sh"
    "final_voice_fix.sh"
    "fix_microphone_default_device.sh"
    "fix_alsa_simple_working.sh"
    "test_all_components.sh"
    "quick_test.sh"
    "test_gemini_2.py"
    "final_system_test.py"
    "diagnose_voice_issues.py"
    "detect_audio_devices.py"
    "test_current_voice_system.py"
    "debug_voice_recognition.py"
    "test_voice_logs.py"
    "test_speech_recognition_fix.py"
    "test_vosk_integration.py"
    "quick_mic_test.py"
    "test_microphone_fix.py"
)

# 要保留的重要脚本
KEEP_SCRIPTS=(
    "install_complete_system.sh"
    "setup_voice_system.sh"
    "download_vosk_model.sh"
    "start_ai_pet_quiet.sh"
    "verify_system.py"
)

echo "以下脚本将被清理:"
for script in "${FIX_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        echo "  - $script"
    fi
done

echo
echo "以下重要脚本将被保留:"
for script in "${KEEP_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        echo "  + $script"
    fi
done

echo
read -p "确认清理这些临时修复脚本？(y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo
    echo "🗑️  开始清理..."
    
    # 创建备份目录
    BACKUP_DIR="fix_scripts_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    cleaned_count=0
    backed_up_count=0
    
    for script in "${FIX_SCRIPTS[@]}"; do
        if [ -f "$script" ]; then
            # 备份到备份目录
            cp "$script" "$BACKUP_DIR/"
            backed_up_count=$((backed_up_count + 1))
            
            # 删除原文件
            rm "$script"
            cleaned_count=$((cleaned_count + 1))
            echo "  ✅ 已清理: $script"
        fi
    done
    
    echo
    echo "=================================="
    echo "🎉 清理完成！"
    echo "=================================="
    echo "📊 清理统计:"
    echo "  • 已清理脚本: $cleaned_count 个"
    echo "  • 已备份脚本: $backed_up_count 个"
    echo "  • 备份位置: $BACKUP_DIR/"
    echo
    echo "📋 保留的重要脚本:"
    echo "  • install_complete_system.sh - 完整系统安装"
    echo "  • setup_voice_system.sh - 语音系统配置"
    echo "  • download_vosk_model.sh - Vosk模型下载"
    echo "  • start_ai_pet_quiet.sh - 系统启动"
    echo "  • verify_system.py - 系统验证"
    echo
    echo "💡 如果需要恢复某个脚本，可以从备份目录复制"
    echo "💡 如果确认不再需要备份，可以删除: rm -rf $BACKUP_DIR"
else
    echo "❌ 清理已取消"
fi