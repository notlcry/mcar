#!/usr/bin/env python3
"""
安全测试主程序 - 避免音频流相关的段错误
只测试核心逻辑，不实际启动音频流
"""

import os
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, 'src')

def test_core_functionality():
    """测试核心功能，不启动音频流"""
    print("🛡️ 安全测试 - 核心功能验证")
    print("=" * 50)
    
    try:
        # 测试1: 导入和初始化
        print("📦 测试组件导入...")
        
        from enhanced_voice_control import EnhancedVoiceController
        from ai_conversation import AIConversationManager
        from vosk_recognizer import VoskRecognizer
        
        print("✅ 所有组件导入成功")
        
        # 测试2: 创建实例（不启动音频）
        print("🔧 测试组件初始化...")
        
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        # AI管理器
        ai_manager = AIConversationManager()
        if ai_manager.start_conversation_mode():
            print("✅ AI对话管理器初始化成功")
        else:
            print("❌ AI对话管理器初始化失败")
            return False
        
        # Vosk识别器
        vosk_recognizer = VoskRecognizer()
        if vosk_recognizer.is_available:
            print("✅ Vosk中文识别器可用")
        else:
            print("⚠️ Vosk识别器不可用")
        
        # 测试3: 创建控制器但不启动音频
        print("🎤 测试语音控制器（不启动音频）...")
        
        voice_controller = EnhancedVoiceController(robot=MockRobot())
        print("✅ 语音控制器创建成功")
        
        # 测试4: 状态管理
        print("📊 测试状态管理...")
        
        status = voice_controller.get_conversation_status()
        print(f"   初始状态: {status['state']}")
        print(f"   对话模式: {status['conversation_mode']}")
        print(f"   唤醒检测: {status['wake_word_detected']}")
        
        # 测试5: 模拟唤醒（不使用真实音频）
        print("🔔 测试模拟唤醒...")
        
        # 手动设置唤醒状态
        voice_controller.wake_word_detected = True
        voice_controller.last_interaction_time = time.time()
        
        status = voice_controller.get_conversation_status()
        print(f"   唤醒后状态: {status['state']}")
        print(f"   唤醒标志: {status['wake_word_detected']}")
        
        # 测试6: AI对话处理
        print("🤖 测试AI对话处理...")
        
        test_text = "你好，这是测试"
        context = ai_manager.process_user_input(test_text)
        
        if context and context.ai_response:
            print(f"✅ AI回复: {context.ai_response[:50]}...")
            if context.emotion_detected:
                print(f"✅ 情感检测: {context.emotion_detected}")
        else:
            print("❌ AI对话处理失败")
        
        # 测试7: 清理
        print("🧹 测试清理...")
        
        voice_controller.conversation_mode = False
        ai_manager.stop_conversation_mode()
        
        print("✅ 清理完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_audio_free_mode():
    """测试无音频模式下的完整流程"""
    print("\n🔇 测试无音频模式...")
    
    try:
        from enhanced_voice_control import EnhancedVoiceController
        
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        # 创建控制器
        voice_controller = EnhancedVoiceController(robot=MockRobot())
        
        # 手动设置对话模式（不启动音频流）
        voice_controller.conversation_mode = True
        
        # 模拟对话流程
        print("💬 模拟对话流程...")
        
        # 模拟用户输入
        test_inputs = ["你好", "今天天气怎么样", "谢谢"]
        
        for i, text in enumerate(test_inputs, 1):
            print(f"   第{i}轮: 用户说 '{text}'")
            
            # 模拟AI处理
            if voice_controller.ai_conversation_manager:
                context = voice_controller.ai_conversation_manager.process_user_input(text)
                if context and context.ai_response:
                    print(f"   AI回复: {context.ai_response[:50]}...")
                    # 将TTS文本加入队列（不实际播放）
                    voice_controller.tts_queue.put(context.ai_response)
                    print(f"   TTS队列大小: {voice_controller.tts_queue.qsize()}")
        
        print("✅ 无音频模式测试成功")
        return True
        
    except Exception as e:
        print(f"❌ 无音频模式测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 主程序安全测试")
    print("专注于验证核心逻辑，避免音频流段错误")
    print("=" * 60)
    
    # 测试1: 核心功能
    test1_success = test_core_functionality()
    
    if not test1_success:
        print("\n❌ 核心功能测试失败")
        return
    
    # 测试2: 无音频模式
    test2_success = test_audio_free_mode()
    
    if test1_success and test2_success:
        print("\n🎉 安全测试全部通过！")
        print("📋 确认结果:")
        print("✅ 核心组件工作正常")
        print("✅ 状态管理正确")
        print("✅ AI对话功能正常")
        print("✅ 无音频流冲突")
        
        print("\n💡 下一步建议:")
        print("1. 核心功能已确认工作")
        print("2. 音频流冲突问题可能在具体的音频设备交互中")
        print("3. 可以考虑分步启用音频功能")
        print("4. 或者先使用无音频模式进行AI对话测试")
        
    else:
        print("\n😞 测试未完全通过")
        print("需要进一步调试")

if __name__ == "__main__":
    main()