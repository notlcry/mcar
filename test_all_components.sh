#!/bin/bash
# 最终测试脚本 - 验证所有组件是否正常工作

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 加载环境变量
load_environment() {
    log_step "加载环境变量..."
    
    # 尝试多个可能的环境变量文件位置
    env_files=("~/.ai_pet_env" ".ai_pet_env" "./.ai_pet_env")
    
    for env_file in "${env_files[@]}"; do
        # 展开波浪号
        expanded_file="${env_file/#\~/$HOME}"
        
        if [[ -f "$expanded_file" ]]; then
            log_info "找到环境变量文件: $expanded_file"
            source "$expanded_file"
            
            # 验证关键变量是否加载
            if [[ -n "$GEMINI_API_KEY" ]]; then
                log_info "✓ GEMINI_API_KEY 已加载"
            fi
            if [[ -n "$PICOVOICE_ACCESS_KEY" ]]; then
                log_info "✓ PICOVOICE_ACCESS_KEY 已加载"
            fi
            
            log_info "✓ 环境变量已加载"
            return 0
        fi
    done
    
    log_error "✗ 环境变量文件不存在"
    return 1
}

# 测试音频系统
test_audio_system() {
    log_step "测试音频系统..."
    
    echo "1. 测试ALSA配置:"
    if aplay -l | grep -q "card"; then
        log_info "✓ ALSA播放设备正常"
    else
        log_warn "✗ ALSA播放设备异常"
    fi
    
    if arecord -l | grep -q "card"; then
        log_info "✓ ALSA录音设备正常"
    else
        log_warn "✗ ALSA录音设备异常"
    fi
    
    echo "2. 测试pygame音频:"
    python3 -c "
import pygame
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    print('✓ pygame音频系统正常')
    pygame.mixer.quit()
except Exception as e:
    print(f'✗ pygame音频系统异常: {e}')
"
}

# 测试Porcupine唤醒词检测
test_porcupine() {
    log_step "测试Porcupine唤醒词检测..."
    
    python3 -c "
import os
import pvporcupine

access_key = os.getenv('PICOVOICE_ACCESS_KEY')
if not access_key:
    print('✗ PICOVOICE_ACCESS_KEY未设置')
    exit(1)

try:
    porcupine = pvporcupine.create(
        access_key=access_key,
        keywords=['picovoice']
    )
    print('✓ Porcupine初始化成功')
    print(f'  - 采样率: {porcupine.sample_rate}')
    print(f'  - 帧长度: {porcupine.frame_length}')
    porcupine.delete()
except Exception as e:
    print(f'✗ Porcupine初始化失败: {e}')
    exit(1)
"
}

# 测试Gemini API
test_gemini_api() {
    log_step "测试Gemini API..."
    
    python3 -c "
import os
import google.generativeai as genai

api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print('✗ GEMINI_API_KEY未设置')
    exit(1)

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    
    # 测试简单对话
    response = model.generate_content('你好，请简单回复一句话')
    print('✓ Gemini API连接成功')
    print(f'  - 测试回复: {response.text[:50]}...')
    
except Exception as e:
    print(f'✗ Gemini API测试失败: {e}')
    exit(1)
"
}

# 测试语音识别
test_speech_recognition() {
    log_step "测试语音识别..."
    
    python3 -c "
try:
    import speech_recognition as sr
    r = sr.Recognizer()
    print('✓ SpeechRecognition库可用')
    
    # 测试麦克风
    with sr.Microphone() as source:
        print('✓ 麦克风访问正常')
        
except ImportError:
    print('⚠️  SpeechRecognition库未安装，尝试安装...')
    import subprocess
    subprocess.run(['pip3', 'install', 'SpeechRecognition'], check=True)
    print('✓ SpeechRecognition库已安装')
    
except Exception as e:
    print(f'✗ 语音识别测试失败: {e}')
"
}

# 测试Edge TTS
test_edge_tts() {
    log_step "测试Edge TTS..."
    
    python3 -c "
try:
    import edge_tts
    print('✓ Edge TTS库可用')
    
    # 测试语音合成
    import asyncio
    
    async def test_tts():
        communicate = edge_tts.Communicate('你好，这是测试', 'zh-CN-XiaoxiaoNeural')
        audio_data = b''
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                audio_data += chunk['data']
        return len(audio_data) > 0
    
    result = asyncio.run(test_tts())
    if result:
        print('✓ Edge TTS语音合成正常')
    else:
        print('✗ Edge TTS语音合成失败')
        
except ImportError:
    print('⚠️  Edge TTS库未安装')
except Exception as e:
    print(f'✗ Edge TTS测试失败: {e}')
"
}

# 运行完整的系统测试
run_integration_test() {
    log_step "运行系统集成测试..."
    
    echo "测试AI桌宠主要组件的集成..."
    
    python3 -c "
import os
import sys
sys.path.insert(0, 'src')

# 测试配置加载
try:
    import config
    print('✓ 配置模块加载成功')
except:
    print('⚠️  配置模块不存在，使用默认配置')

# 测试主要模块导入
modules_to_test = [
    'enhanced_voice_control',
    'ai_conversation_manager', 
    'emotion_engine',
    'oled_display_controller',
    'personality_movement_controller'
]

for module in modules_to_test:
    try:
        __import__(module)
        print(f'✓ {module} 模块导入成功')
    except ImportError as e:
        print(f'⚠️  {module} 模块导入失败: {e}')
    except Exception as e:
        print(f'⚠️  {module} 模块有问题: {e}')

print('✓ 系统集成测试完成')
"
}

# 显示测试结果总结
show_test_summary() {
    log_step "测试结果总结"
    
    echo
    echo "======================================"
    echo "🧪 AI桌宠系统测试完成"
    echo "======================================"
    echo
    echo "✅ 已测试的组件："
    echo "• 音频系统 (ALSA + pygame)"
    echo "• Porcupine唤醒词检测"
    echo "• Gemini AI对话"
    echo "• 语音识别"
    echo "• 语音合成 (Edge TTS)"
    echo "• 系统模块集成"
    echo
    echo "🚀 启动AI桌宠系统："
    echo "   cd src && python3 robot_voice_web_control.py"
    echo
    echo "🌐 访问Web界面："
    echo "   http://$(hostname -I | awk '{print $1}'):5000"
    echo
    echo "🎤 使用说明："
    echo "• 说 'picovoice' 唤醒系统"
    echo "• 通过Web界面控制机器人"
    echo "• 与AI进行语音对话"
    echo
    echo "📚 如有问题，查看故障排除指南："
    echo "   cat TROUBLESHOOTING_GUIDE.md"
    echo
}

# 主函数
main() {
    echo "======================================"
    echo "🧪 AI桌宠系统完整测试"
    echo "======================================"
    echo
    echo "这将测试所有修复的组件："
    echo "• 音频系统"
    echo "• Porcupine唤醒词"
    echo "• Gemini API"
    echo "• 语音识别和合成"
    echo "• 系统集成"
    echo
    
    read -p "按Enter键开始测试，或Ctrl+C取消: "
    
    load_environment
    test_audio_system
    test_porcupine
    test_gemini_api
    test_speech_recognition
    test_edge_tts
    run_integration_test
    show_test_summary
    
    log_info "所有测试完成！"
}

# 错误处理
trap 'log_error "测试过程中发生错误"; exit 1' ERR

# 运行主程序
main "$@"