#!/bin/bash
# 启动AI对话系统 - 自动开启唤醒词监听
# 这个脚本直接启动AI对话模式，无需Web界面

# 设置环境变量，抑制ALSA错误
export ALSA_QUIET=1
export SDL_AUDIODRIVER=alsa
export ALSA_PCM_CARD=0
export ALSA_PCM_DEVICE=0

# 重定向ALSA错误到/dev/null
exec 2> >(grep -v "ALSA lib\|Expression.*GetExactSampleRate\|fork_posix" >&2)

echo "🤖 启动AI对话系统..."
echo "🎤 将自动开启唤醒词监听..."
echo "💬 说 '快快' 开始对话"
echo "✨ 按 Ctrl+C 停止系统"
echo "=" * 50

# 加载环境变量（重要！）
if [ -f ".ai_pet_env" ]; then
    source .ai_pet_env
    echo "✅ 环境变量已加载"
else
    echo "⚠️ 未找到.ai_pet_env文件"
fi

cd src

# 启动AI对话系统并自动开启对话模式
python3 -c "
import sys
import time
import logging
import signal
from enhanced_voice_control import EnhancedVoiceController

# 设置日志级别
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def signal_handler(sig, frame):
    print('\n🛑 正在停止AI对话系统...')
    if 'controller' in globals():
        controller.stop_conversation_mode()
        time.sleep(1)
    print('✅ 系统已停止')
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

try:
    # 初始化语音控制器
    print('🔧 初始化AI语音控制器...')
    controller = EnhancedVoiceController()
    
    # 启动对话模式
    print('🎤 启动AI对话模式...')
    result = controller.start_conversation_mode()
    
    if result:
        print('✅ AI对话系统已启动！')
        print('🗣️ 请说 \"快快\" 来唤醒AI')
        print('💡 AI将听取你的话并智能回复')
        
        # 保持运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        print('❌ AI对话系统启动失败')
        sys.exit(1)
        
except Exception as e:
    logger.error(f'系统启动失败: {e}')
    sys.exit(1)
finally:
    if 'controller' in locals():
        controller.stop_conversation_mode()
"