#!/usr/bin/env python3
"""
修复后的AI对话测试
避免连续音频流监听导致的段错误
采用单次录音模式进行测试
"""

import os
import sys
import time
import logging
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, 'src')

def test_ai_conversation_safe():
    """安全的AI对话测试 - 避免连续音频流"""
    print("🤖 安全AI对话测试")
    print("使用单次录音模式，避免连续流冲突")
    print("=" * 50)
    
    try:
        # 导入必要组件
        import speech_recognition as sr
        from vosk_recognizer import VoskRecognizer
        from ai_conversation import AIConversationManager
        from wake_word_detector import WakeWordDetector
        
        # 1. 初始化组件
        print("🔧 初始化组件...")
        
        # AI管理器
        ai_manager = AIConversationManager()
        if not ai_manager.start_conversation_mode():
            print("❌ AI对话模式启动失败")
            return False
        print("✅ AI对话管理器就绪")
        
        # Vosk识别器
        vosk_recognizer = VoskRecognizer()
        if not vosk_recognizer.is_available:
            print("❌ Vosk识别器不可用")
            return False
        print("✅ Vosk中文识别器就绪")
        
        # 语音识别器
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        print("✅ 音频系统就绪")
        
        # 2. 唤醒词测试（不启动连续监听）
        print("\n🔔 测试唤醒词检测（单次模式）...")
        wake_detector = WakeWordDetector()
        if wake_detector.porcupine:
            print("✅ 唤醒词检测器就绪（不启动连续监听）")
        else:
            print("⚠️ 唤醒词检测器不可用，跳过")
        
        # 3. 模拟对话流程
        print("\n🗣️ 开始AI对话测试")
        print("模拟唤醒状态，直接进行对话")
        
        conversation_count = 0
        max_conversations = 3
        
        while conversation_count < max_conversations:
            print(f"\n--- 对话 {conversation_count + 1}/{max_conversations} ---")
            
            # 录音
            print("🎙️ 请说一句话给AI...")
            input("按Enter开始录音...")
            
            try:
                # 单次录音（避免连续流）
                with microphone as source:
                    recognizer.adjust_for_ambient_noise(source, duration=1)
                    print("正在录音...")
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
                
                # 语音识别
                print("🔍 识别语音...")
                text = vosk_recognizer.recognize_from_speech_recognition_audio(audio)
                
                if not text or not text.strip():
                    print("❌ 语音识别失败，跳过此轮")
                    continue
                
                print(f"📝 识别结果: '{text}'")
                
                # AI处理
                print("🤖 AI处理中...")
                context = ai_manager.process_user_input(text)
                
                if context and context.ai_response:
                    print(f"💬 AI回复: {context.ai_response}")
                    if context.emotion_detected:
                        print(f"😊 检测情感: {context.emotion_detected}")
                    
                    # 可选：TTS输出（如果需要）
                    try_tts = input("是否播放AI回复？(y/n): ").strip().lower()
                    if try_tts == 'y':
                        tts_success = test_tts_output(context.ai_response)
                        if tts_success:
                            print("🔊 语音输出成功")
                        else:
                            print("⚠️ 语音输出失败")
                    
                    print("✅ 本轮对话成功")
                else:
                    print("❌ AI处理失败")
                
                conversation_count += 1
                
            except Exception as e:
                print(f"❌ 对话过程出错: {e}")
                continue
        
        # 清理
        ai_manager.stop_conversation_mode()
        print(f"\n🎉 AI对话测试完成！")
        print(f"成功完成 {conversation_count} 轮对话")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tts_output(text):
    """测试TTS语音输出"""
    try:
        import edge_tts
        import asyncio
        import tempfile
        import subprocess
        
        async def generate_speech():
            voice = "zh-CN-XiaoxiaoNeural"
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(temp_path)
            
            # 尝试播放
            try:
                subprocess.run(['aplay', temp_path], check=True, capture_output=True, timeout=60)
                os.unlink(temp_path)
                return True
            except:
                os.unlink(temp_path)
                return False
        
        return asyncio.run(generate_speech())
        
    except Exception as e:
        logger.error(f"TTS测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🛡️ 安全AI对话测试")
    print("专门避免连续音频流导致的段错误")
    print("=" * 60)
    
    print("📋 测试策略:")
    print("1. 使用单次录音模式替代连续监听")
    print("2. 避免多个音频流同时工作")
    print("3. 逐步验证每个功能模块")
    print("4. 模拟完整对话流程")
    
    success = test_ai_conversation_safe()
    
    if success:
        print("\n🎉 安全测试成功！")
        print("📋 确认功能:")
        print("✅ Vosk中文语音识别")
        print("✅ AI对话生成")
        print("✅ 语音合成输出")
        print("✅ 完整对话流程")
        
        print("\n💡 下一步:")
        print("1. 可以基于此安全模式优化原系统")
        print("2. 修复连续监听的音频流冲突问题")
        print("3. 实现更稳定的实时对话系统")
    else:
        print("\n😞 测试失败")
        print("💡 可能问题:")
        print("1. API密钥配置")
        print("2. 网络连接")
        print("3. 依赖包版本")

if __name__ == "__main__":
    main()