#!/usr/bin/env python3
"""
简化的AI对话测试 - 逐步排查段错误问题
避免复杂的音频流初始化
"""

import os
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, 'src')

def test_step1_basic_imports():
    """测试1: 基础导入"""
    print("🧪 测试1: 基础组件导入")
    try:
        from ai_conversation import AIConversationManager
        print("✅ AI对话管理器导入成功")
        
        from vosk_recognizer import VoskRecognizer
        print("✅ Vosk识别器导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 基础导入失败: {e}")
        return False

def test_step2_ai_only():
    """测试2: 只测试AI对话（无音频）"""
    print("\n🧪 测试2: AI对话功能（无音频）")
    try:
        from ai_conversation import AIConversationManager
        
        ai_manager = AIConversationManager()
        print("✅ AI管理器初始化成功")
        
        if ai_manager.start_conversation_mode():
            print("✅ 对话模式启动成功")
            
            # 文本输入测试
            context = ai_manager.process_user_input("你好")
            if context and context.ai_response:
                print(f"🤖 AI回复: {context.ai_response}")
                print("✅ AI对话核心功能正常")
                ai_manager.stop_conversation_mode()
                return True
            else:
                print("❌ AI回复失败")
                return False
        else:
            print("❌ 对话模式启动失败")
            return False
            
    except Exception as e:
        print(f"❌ AI对话测试失败: {e}")
        return False

def test_step3_vosk_only():
    """测试3: 只测试Vosk识别（已知工作）"""
    print("\n🧪 测试3: Vosk语音识别")
    try:
        import speech_recognition as sr
        from vosk_recognizer import VoskRecognizer
        
        vosk_recognizer = VoskRecognizer()
        if not vosk_recognizer.is_available:
            print("❌ Vosk不可用")
            return False
        
        print("✅ Vosk准备就绪")
        
        # 简单录音测试
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        print("🎙️ 请说一句中文...")
        input("按Enter开始录音...")
        
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        
        result = vosk_recognizer.recognize_from_speech_recognition_audio(audio)
        if result:
            print(f"✅ 识别成功: {result}")
            return True
        else:
            print("❌ 识别失败")
            return False
            
    except Exception as e:
        print(f"❌ Vosk测试失败: {e}")
        return False

def test_step4_combined_simple():
    """测试4: 简单组合（无实时流）"""
    print("\n🧪 测试4: AI+语音组合（非实时）")
    try:
        import speech_recognition as sr
        from vosk_recognizer import VoskRecognizer
        from ai_conversation import AIConversationManager
        
        # 初始化组件
        vosk_recognizer = VoskRecognizer()
        ai_manager = AIConversationManager()
        
        if not vosk_recognizer.is_available:
            print("❌ Vosk不可用")
            return False
        
        if not ai_manager.start_conversation_mode():
            print("❌ AI对话模式启动失败")
            return False
        
        print("✅ 组件初始化成功")
        
        # 简单的语音->AI流程
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        print("🎙️ 请说一句话给AI...")
        input("按Enter开始录音...")
        
        # 录音
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        
        # 识别
        text = vosk_recognizer.recognize_from_speech_recognition_audio(audio)
        if not text:
            print("❌ 语音识别失败")
            return False
        
        print(f"📝 识别结果: {text}")
        
        # AI处理
        context = ai_manager.process_user_input(text)
        if context and context.ai_response:
            print(f"🤖 AI回复: {context.ai_response}")
            print("✅ 完整语音AI对话流程成功！")
            ai_manager.stop_conversation_mode()
            return True
        else:
            print("❌ AI处理失败")
            return False
            
    except Exception as e:
        print(f"❌ 组合测试失败: {e}")
        return False

def test_step5_wake_word_check():
    """测试5: 检查唤醒词组件"""
    print("\n🧪 测试5: 唤醒词组件检查")
    try:
        from wake_word_detector import WakeWordDetector, SimpleWakeWordDetector
        
        # 不启动实时检测，只检查初始化
        detector = WakeWordDetector()
        print("✅ 唤醒词检测器导入成功")
        
        # 检查是否是这个组件导致的问题
        print("⚠️ 注意：唤醒词检测可能包含实时音频流")
        print("⚠️ 这可能是段错误的源头")
        
        return True
        
    except Exception as e:
        print(f"❌ 唤醒词组件测试失败: {e}")
        return False

def main():
    """主测试流程"""
    print("🔍 AI对话系统分步诊断")
    print("目标：找出段错误的确切原因")
    print("=" * 50)
    
    # 逐步测试
    tests = [
        ("基础导入", test_step1_basic_imports),
        ("AI对话（无音频）", test_step2_ai_only),
        ("Vosk识别", test_step3_vosk_only),
        ("简单组合", test_step4_combined_simple),
        ("唤醒词检查", test_step5_wake_word_check),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        
        try:
            success = test_func()
            if success:
                print(f"✅ {test_name} 通过")
            else:
                print(f"❌ {test_name} 失败")
                print("🛑 在此步骤停止，避免段错误")
                break
        except Exception as e:
            print(f"💥 {test_name} 出现异常: {e}")
            print("🛑 在此步骤停止，避免段错误")
            break
    
    print("\n📋 诊断总结:")
    print("如果前4个测试都通过，问题可能在于:")
    print("1. 唤醒词检测的实时音频流")
    print("2. EnhancedVoiceController的复杂初始化")
    print("3. 多个音频流的并发冲突")

if __name__ == "__main__":
    main()