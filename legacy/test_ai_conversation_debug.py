#!/usr/bin/env python3
"""
AI对话调试测试脚本
专门用于调试语音识别在对话模式下的问题
"""

import os
import sys
import time
import threading
import logging

# 设置详细日志
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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

def test_ai_conversation_with_debug():
    """测试AI对话功能，包含详细调试信息"""
    print("🤖 AI对话调试测试")
    print("=" * 60)
    
    try:
        # 导入必要模块
        from enhanced_voice_control import EnhancedVoiceController
        from ai_conversation import AIConversationManager
        
        # 创建模拟机器人
        class MockRobot:
            def __init__(self):
                logger.info("🤖 模拟机器人初始化")
            
            def t_stop(self, duration=0):
                logger.info(f"🛑 机器人停止 {duration}秒")
            
            def turnRight(self, angle, duration):
                logger.info(f"➡️  机器人右转 {angle}度，持续{duration}秒")
            
            def turnLeft(self, angle, duration):
                logger.info(f"⬅️  机器人左转 {angle}度，持续{duration}秒")
            
            def t_down(self, speed, duration):
                logger.info(f"⬇️  机器人后退 速度{speed}，持续{duration}秒")
            
            def moveLeft(self, speed, duration):
                logger.info(f"⬅️  机器人左移 速度{speed}，持续{duration}秒")
            
            def moveRight(self, speed, duration):
                logger.info(f"➡️  机器人右移 速度{speed}，持续{duration}秒")
        
        mock_robot = MockRobot()
        
        # 创建AI对话管理器
        logger.info("🧠 初始化AI对话管理器...")
        ai_manager = AIConversationManager(mock_robot)
        
        # 创建增强语音控制器
        logger.info("🎤 初始化增强语音控制器...")
        voice_controller = EnhancedVoiceController(
            robot=mock_robot,
            ai_conversation_manager=ai_manager
        )
        
        # 显示系统状态
        status = voice_controller.get_conversation_status()
        logger.info("📊 系统状态:")
        for key, value in status.items():
            logger.info(f"   {key}: {value}")
        
        # 启动对话模式
        logger.info("🚀 启动对话模式...")
        if voice_controller.start_conversation_mode():
            logger.info("✅ 对话模式启动成功")
            
            # 等待系统稳定
            time.sleep(2)
            
            # 强制唤醒进行测试
            logger.info("🔔 强制唤醒AI桌宠...")
            voice_controller.force_wake_up()
            
            print("\n" + "=" * 60)
            print("🎙️  AI对话测试已准备就绪")
            print("=" * 60)
            print("📋 测试说明:")
            print("• 系统已唤醒，可以直接说话")
            print("• 建议测试短语:")
            print("  - '你好'")
            print("  - '你是谁'") 
            print("  - '今天天气怎么样'")
            print("  - '讲个笑话'")
            print("• 系统会显示详细的识别和处理过程")
            print("• 按Ctrl+C退出测试")
            print("=" * 60)
            
            # 启动监听线程
            listen_thread = threading.Thread(
                target=voice_controller.listen_continuously, 
                daemon=True
            )
            listen_thread.start()
            logger.info("🎧 语音监听线程已启动")
            
            # 监控系统状态
            def monitor_status():
                while voice_controller.conversation_mode:
                    try:
                        status = voice_controller.get_conversation_status()
                        logger.debug(f"📊 状态监控: 对话模式={status['conversation_mode']}, "
                                   f"唤醒状态={status['wake_word_detected']}, "
                                   f"TTS队列={status['tts_queue_size']}, "
                                   f"音频队列={status['audio_queue_size']}")
                        time.sleep(10)  # 每10秒监控一次
                    except Exception as e:
                        logger.error(f"❌ 状态监控错误: {e}")
                        break
            
            monitor_thread = threading.Thread(target=monitor_status, daemon=True)
            monitor_thread.start()
            
            # 保持运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 收到停止信号...")
                logger.info("🛑 停止AI对话测试...")
                voice_controller.stop_conversation_mode()
                logger.info("✅ 测试结束")
                
        else:
            logger.error("❌ 对话模式启动失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ AI对话测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_speech_recognition_accuracy():
    """测试语音识别准确性"""
    print("\n🎯 语音识别准确性测试")
    print("=" * 60)
    
    try:
        import speech_recognition as sr
        
        # 初始化识别器
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        # 优化识别器参数
        recognizer.energy_threshold = 4000
        recognizer.pause_threshold = 1.0
        recognizer.timeout = 2
        recognizer.phrase_time_limit = 10
        
        logger.info(f"🔧 识别器参数: energy_threshold={recognizer.energy_threshold}")
        logger.info(f"🔧 识别器参数: pause_threshold={recognizer.pause_threshold}")
        
        # 调整环境噪音
        with microphone as source:
            logger.info("🔧 调整环境噪音...")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            logger.info(f"🔧 环境噪音调整完成，能量阈值: {recognizer.energy_threshold}")
        
        print("\n📋 测试说明:")
        print("• 每次提示后说一句中文")
        print("• 系统会尝试多个识别引擎")
        print("• 观察哪个引擎识别最准确")
        print("• 输入'q'退出测试")
        
        test_count = 1
        
        while True:
            print(f"\n--- 测试 {test_count} ---")
            user_input = input("按Enter开始录音，或输入'q'退出: ").strip()
            
            if user_input.lower() == 'q':
                break
            
            print("🎙️  请说话（建议: '你好机器人' 或 '今天天气怎么样'）...")
            
            try:
                with microphone as source:
                    # 短暂调整噪音
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.listen(source, timeout=3, phrase_time_limit=8)
                
                logger.info("🔍 开始多引擎识别测试...")
                
                # Google识别
                try:
                    google_result = recognizer.recognize_google(audio, language='zh-CN')
                    print(f"🌐 Google: '{google_result}'")
                    logger.info(f"✅ Google识别成功: {google_result}")
                except sr.UnknownValueError:
                    print("🌐 Google: 无法理解音频")
                    logger.warning("❌ Google无法理解音频")
                except sr.RequestError as e:
                    print(f"🌐 Google: 服务错误 ({e})")
                    logger.error(f"❌ Google服务错误: {e}")
                except Exception as e:
                    print(f"🌐 Google: 识别失败 ({e})")
                    logger.error(f"❌ Google识别失败: {e}")
                
                # Vosk识别
                try:
                    from vosk_recognizer import VoskRecognizer
                    vosk_recognizer = VoskRecognizer()
                    if vosk_recognizer.is_available:
                        vosk_result = vosk_recognizer.recognize_from_speech_recognition_audio(audio)
                        if vosk_result:
                            print(f"🇨🇳 Vosk: '{vosk_result}'")
                            logger.info(f"✅ Vosk识别成功: {vosk_result}")
                        else:
                            print("🇨🇳 Vosk: 返回空结果")
                            logger.warning("❌ Vosk返回空结果")
                    else:
                        print("🇨🇳 Vosk: 不可用")
                        logger.warning("❌ Vosk不可用")
                except Exception as e:
                    print(f"🇨🇳 Vosk: 识别失败 ({e})")
                    logger.error(f"❌ Vosk识别失败: {e}")
                
                # PocketSphinx识别
                try:
                    sphinx_result = recognizer.recognize_sphinx(audio)
                    if sphinx_result:
                        print(f"🇺🇸 Sphinx: '{sphinx_result}'")
                        logger.info(f"✅ Sphinx识别成功: {sphinx_result}")
                    else:
                        print("🇺🇸 Sphinx: 返回空结果")
                        logger.warning("❌ Sphinx返回空结果")
                except Exception as e:
                    print(f"🇺🇸 Sphinx: 识别失败 ({e})")
                    logger.error(f"❌ Sphinx识别失败: {e}")
                
                test_count += 1
                
            except sr.WaitTimeoutError:
                print("⏰ 录音超时，请重试")
                logger.warning("⏰ 录音超时")
            except Exception as e:
                print(f"❌ 录音失败: {e}")
                logger.error(f"❌ 录音失败: {e}")
        
        print("✅ 识别准确性测试结束")
        
    except Exception as e:
        logger.error(f"❌ 识别测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🤖 AI对话调试测试工具")
    print("=" * 60)
    
    while True:
        print("\n选择测试模式:")
        print("1. 完整AI对话调试测试")
        print("2. 语音识别准确性测试")
        print("3. 退出")
        
        choice = input("\n请选择 (1-3): ").strip()
        
        if choice == '1':
            test_ai_conversation_with_debug()
        elif choice == '2':
            test_speech_recognition_accuracy()
        elif choice == '3':
            print("👋 测试结束")
            break
        else:
            print("❌ 无效选择，请重试")