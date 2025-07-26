#!/bin/bash
# 自定义唤醒词配置脚本

set -e

echo "🎤 自定义唤醒词配置向导"
echo "=========================="
echo

# 检查wake_words目录
if [ ! -d "wake_words" ]; then
    echo "创建wake_words目录..."
    mkdir -p wake_words
fi

# 列出现有的.ppn文件
echo "检查现有的唤醒词模型文件..."
ppn_files=(wake_words/*.ppn)

if [ -f "${ppn_files[0]}" ]; then
    echo "找到以下唤醒词模型文件："
    for file in "${ppn_files[@]}"; do
        echo "  - $(basename "$file")"
    done
    echo
else
    echo "❌ 未找到.ppn文件"
    echo
    echo "请按以下步骤操作："
    echo "1. 从Picovoice控制台下载训练好的.ppn文件"
    echo "2. 将文件复制到 wake_words/ 目录"
    echo "3. 重新运行此脚本"
    echo
    echo "下载地址: https://console.picovoice.ai/"
    exit 1
fi

# 选择唤醒词文件
echo "请选择要使用的唤醒词模型："
select ppn_file in "${ppn_files[@]}" "取消"; do
    case $ppn_file in
        "取消")
            echo "配置已取消"
            exit 0
            ;;
        *.ppn)
            echo "选择了: $(basename "$ppn_file")"
            SELECTED_PPN="$ppn_file"
            break
            ;;
        *)
            echo "无效选择，请重新选择"
            ;;
    esac
done

# 检查Picovoice访问密钥
echo
echo "检查Picovoice访问密钥..."

if [ -f ".ai_pet_env" ]; then
    source .ai_pet_env
    if [ -n "$PICOVOICE_ACCESS_KEY" ] && [ "$PICOVOICE_ACCESS_KEY" != "your_picovoice_access_key_here" ]; then
        echo "✅ 访问密钥已配置"
    else
        echo "❌ 访问密钥未配置或使用默认值"
        read -p "请输入你的Picovoice访问密钥: " access_key
        
        if [ -n "$access_key" ]; then
            # 更新.ai_pet_env文件
            sed -i.bak "s/your_picovoice_access_key_here/$access_key/" .ai_pet_env
            echo "✅ 访问密钥已更新"
        else
            echo "❌ 访问密钥不能为空"
            exit 1
        fi
    fi
else
    echo "❌ 未找到.ai_pet_env文件"
    echo "请先运行: ./setup_api_keys.sh"
    exit 1
fi

# 更新配置文件
echo
echo "更新AI桌宠配置..."

# 读取当前配置
if [ -f "src/ai_pet_config.json" ]; then
    # 使用Python更新配置
    python3 -c "
import json
import os

config_file = 'src/ai_pet_config.json'
ppn_file = '$SELECTED_PPN'

# 读取配置
with open(config_file, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 更新唤醒词配置
if 'voice' not in config:
    config['voice'] = {}

config['voice']['custom_wake_word_path'] = ppn_file
config['voice']['use_custom_wake_word'] = True

# 保存配置
with open(config_file, 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print('配置文件已更新')
"
    echo "✅ 配置文件已更新"
else
    echo "❌ 未找到配置文件 src/ai_pet_config.json"
    exit 1
fi

# 测试唤醒词
echo
echo "🧪 测试自定义唤醒词..."

cd src
python3 -c "
import sys
sys.path.append('.')

try:
    from wake_word_detector import WakeWordDetector
    import os
    
    # 加载环境变量
    if os.path.exists('../.ai_pet_env'):
        with open('../.ai_pet_env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    if line.startswith('export '):
                        line = line[7:]
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('\"\'')
    
    access_key = os.getenv('PICOVOICE_ACCESS_KEY')
    ppn_path = '../$SELECTED_PPN'
    
    if access_key and access_key != 'your_picovoice_access_key_here':
        detector = WakeWordDetector(
            access_key=access_key,
            keyword_paths=[ppn_path]
        )
        
        if detector.initialize():
            print('✅ 自定义唤醒词初始化成功！')
            print(f'唤醒词文件: $(basename \"$SELECTED_PPN\")')
            print('可以开始使用自定义唤醒词了')
        else:
            print('❌ 唤醒词初始化失败')
    else:
        print('❌ Picovoice访问密钥无效')
        
except Exception as e:
    print(f'❌ 测试失败: {e}')
    print('请检查.ppn文件和访问密钥是否正确')
"

echo
echo "=============================="
echo "🎉 自定义唤醒词配置完成！"
echo "=============================="
echo
echo "配置信息："
echo "• 唤醒词文件: $(basename "$SELECTED_PPN")"
echo "• 访问密钥: 已配置"
echo "• 配置文件: 已更新"
echo
echo "使用方法："
echo "1. 启动AI桌宠系统:"
echo "   cd src && python3 robot_voice_web_control.py"
echo
echo "2. 说出你训练的唤醒词来激活语音控制"
echo
echo "3. 如果唤醒词不工作，请检查："
echo "   • .ppn文件是否正确"
echo "   • Picovoice访问密钥是否有效"
echo "   • 麦克风是否正常工作"
echo
echo "调试命令："
echo "   cd src && python3 test_wake_word.py"
echo