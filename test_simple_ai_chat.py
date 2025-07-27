#!/usr/bin/env python3
"""
简化的AI对话测试
专门测试语音识别 + AI回复的完整流程
"""

import os
import sys
import time
import threading
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
def load_env():
    try:
        with open('.ai_pet_env', 'r') as f:
            for line in f:
                if line.startswith('export ') and '=' in line:
                    line = line.replace('export ', '').strip()
                    key, value = line.split('=', 1)
                    value = value.strip('"')
                    os.environ[key] = value
        logger.info("✅ 环境变量加载成功")
    except Exception as e:
        logger.warning(f"⚠️  环境变量加载失败: {e}")

load_env()
sys.path.insert(0, 'src')

def test_simple_ai_conversation():
    """简化的AI对话测试"""
    print("🤖 简化AI对话测试")
    print("=" * 60)
    
    try:
        from enhanced_voice_control import EnhancedVoiceController
        
        # 创建简单的模拟机器人
        class SimpleRobot:
            def t_stop(self, duration=0):
                print(f"🤖 机器人停止 {duration}秒")
            
            def turnRight(self, angle, duration):
                print(f"🤖 机器人右转 {angle}度")
            
            def turnLeft(self, angle, duration):
                print(f"🤖 机器人左转 {angle}度")
        
        robot = SimpleRobot()
        
        # 创建语音控制器
        print("🔧 初始化语音控制器...")
        voice_controller = EnhancedVoiceController(robot=robot)
        
        # 检查初始化状态
        status = voice_controller.get_conversation_status()
        print("📊 系统状态:")
        print(f"   Vosk可用: {status['use_vosk']}")
        print(f"   Whisper可用: {status['use_whisper']}")
        print(f"   唤醒词检测: {status['use_porcupine']}")
        
        # 启动对话模式
        print("\n🚀 启动对话模式...")
        if not voice_controller.start_conversation_mode():
            print("❌ 对话模式启动失败")
            return False
        
        print("✅ 对话模式启动成功")
        
        # 强制唤醒
        print("🔔 强制唤醒AI...")
        voice_controller.force_wake_up()
        
        print("\n" + "=" * 60)
        print("🎙️  简化AI对话测试准备就绪")
        print("=" * 60)
        print("📋 测试说明:")
        print("• 系统已唤醒，直接说话即可")
        print("• 建议测试:")
        print("  - '你好' (简单问候)")
        print("  - '你是谁' (身份询问)")
        print("  - '转个圈' (动作指令)")
        print("• 观察语音识别和AI回复过程")
        print("• 按Ctrl+C退出")
        print("=" * 60)
        
        # 启动监听
        def listen_worker():
            """监听工作线程"""
            voice_controller.listen_continuously()
        
        listen_thread = threading.Thread(target=listen_worker, daemon=True)
        listen_thread.start()
        
        # 状态监控
        def status_monitor():
            """状态监控线程"""
            while voice_controller.conversation_mode:
                try:
                    status = voice_controller.get_conversation_status()
                    logger.debug(f"状态: 对话={status['conversation_mode']}, "
                               f"唤醒={status['wake_word_detected']}, "
                               f"TTS队列={status['tts_queue_size']}")
                    time.sleep(5)
                except:
                    break
        
        monitor_thread = threading.Thread(target=status_monitor, daemon=True)
        monitor_thread.start()
        
        # 保持运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 停止测试...")
            voice_controller.stop_conversation_mode()
            print("✅ 测试结束")
            return True
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_manual_input_ai():
    """手动输入测试AI回复"""
    print("\n⌨️  手动输入AI测试")
    print("=" * 60)
    
    try:
        from ai_conversation import AIConversationManager
        
        # 创建简单机器人
        class SimpleRobot:
            def t_stop(self, duration=0):
                print(f"🤖 停止 {duration}秒")
        
        robot = SimpleRobot()
        
        # 创建AI管理器
        print("🧠 初始化AI对话管理器...")
        ai_manager = AIConversationManager(robot)
        
        # 检查AI状态
        status = ai_manager.get_status()
        print("📊 AI状态:")
        print(f"   模型可用: {status['model_available']}")
        print(f"   API配置: {status['api_configured']}")
        
        if not status['model_available']:
            print("❌ AI模型不可用，请检查API配置")
            return False
        
        # 启动对话
        if not ai_manager.start_conversation_mode():
            print("❌ AI对话启动失败")
            return False
        
        print("✅ AI对话启动成功")
        print("\n💬 手动输入测试开始")
        print("💡 输入'quit'退出测试")
        
        while True:
            user_input = input("\n你: ").strip()
            
            if user_input.lower() in ['quit', 'exit', '退出']:
                break
            
            if not user_input:
                continue
            
            print("🤔 AI思考中...")
            
            # 处理输入
            context = ai_manager.process_user_input(user_input)
            
            if context:
                print(f"🤖 AI: {context.ai_response}")
                print(f"😊 情感: {context.emotion_detected}")
            else:
                print("❌ AI处理失败")
        
        ai_manager.stop_conversation_mode()
        print("✅ 手动测试结束")
        return True
        
    except Exception as e:
        print(f"❌ 手动测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🤖 简化AI对话测试工具")
    print("=" * 60)
    
    while True:
        print("\n选择测试模式:")
        print("1. 完整语音+AI对话测试")
        print("2. 手动输入AI测试（跳过语音识别）")
        print("3. 退出")
        
        choice = input("\n请选择 (1-3): ").strip()
        
        if choice == '1':
            test_simple_ai_conversation()
        elif choice == '2':
            test_manual_input_ai()
        elif choice == '3':
            print("👋 测试结束")
            break
        else:
            print("❌ 无效选择，请重试")