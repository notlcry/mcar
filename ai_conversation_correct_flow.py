#!/usr/bin/env python3
"""
正确的AI对话流程设计
唤醒词监听 -> 停止监听 -> 语音对话 -> 恢复监听
避免音频流冲突
"""

import os
import sys
import time
import logging
import threading
import speech_recognition as sr

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, 'src')

class CorrectAIConversationSystem:
    """正确的AI对话系统 - 避免音频流冲突"""
    
    def __init__(self):
        self.state = "waiting"  # waiting, listening, conversation
        self.ai_manager = None
        self.vosk_recognizer = None
        self.wake_detector = None
        self.sr_recognizer = None
        self.microphone = None
        
        self.running = False
        self.conversation_timeout = 30  # 30秒对话超时
        self.last_conversation_time = 0
        
    def initialize(self):
        """初始化所有组件"""
        print("🔧 初始化AI对话系统...")
        
        try:
            # 1. AI管理器
            from ai_conversation import AIConversationManager
            self.ai_manager = AIConversationManager()
            if not self.ai_manager.start_conversation_mode():
                print("❌ AI管理器初始化失败")
                return False
            print("✅ AI管理器就绪")
            
            # 2. Vosk识别器
            from vosk_recognizer import VoskRecognizer
            self.vosk_recognizer = VoskRecognizer()
            if not self.vosk_recognizer.is_available:
                print("❌ Vosk识别器不可用")
                return False
            print("✅ Vosk识别器就绪")
            
            # 3. 唤醒词检测器
            from wake_word_detector import WakeWordDetector
            self.wake_detector = WakeWordDetector()
            if not self.wake_detector.porcupine:
                print("❌ 唤醒词检测器不可用")
                return False
            print("✅ 唤醒词检测器就绪")
            
            # 4. 语音识别器
            self.sr_recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            print("✅ 语音识别器就绪")
            
            # 5. TTS (简单版本)
            self.init_simple_tts()
            
            return True
            
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            return False
    
    def init_simple_tts(self):
        """初始化简单TTS"""
        try:
            from enhanced_voice_control import EnhancedVoiceController
            
            class MockRobot:
                def t_stop(self, duration=0):
                    pass
            
            # 只为获取TTS方法而创建，不启动完整功能
            temp_controller = EnhancedVoiceController(robot=MockRobot())
            self.tts_method = temp_controller._generate_and_play_speech
            print("✅ TTS系统就绪")
        except Exception as e:
            print(f"⚠️ TTS初始化失败: {e}")
            self.tts_method = None
    
    def start_system(self):
        """启动系统"""
        if not self.initialize():
            return False
        
        self.running = True
        self.state = "waiting"
        
        print("\n🤖 AI对话系统启动成功！")
        print("📋 系统状态: 等待唤醒词")
        print("🔔 请说 '喵喵小车' 来唤醒AI")
        print("按Ctrl+C退出系统")
        
        try:
            self.main_loop()
        except KeyboardInterrupt:
            print("\n🛑 用户终止系统")
        finally:
            self.stop_system()
        
        return True
    
    def main_loop(self):
        """主循环 - 正确的状态机"""
        while self.running:
            if self.state == "waiting":
                # 状态1: 等待唤醒词
                self.wait_for_wake_word()
                
            elif self.state == "conversation":
                # 状态2: 进行对话
                self.handle_conversation()
                
            else:
                time.sleep(0.1)
    
    def wait_for_wake_word(self):
        """状态1: 等待唤醒词（单一音频流）"""
        print("\n🔔 监听唤醒词...")
        
        try:
            # 启动唤醒词检测（单一音频流）
            if self.wake_detector.start_detection(self.on_wake_word_detected):
                
                # 等待唤醒或超时
                timeout = 60  # 60秒检查一次
                start_time = time.time()
                
                while self.state == "waiting" and self.running:
                    time.sleep(0.1)
                    
                    # 定期重新启动检测（避免挂起）
                    if time.time() - start_time > timeout:
                        print("🔄 重新启动唤醒词检测...")
                        self.wake_detector.stop_detection()
                        if self.wake_detector.start_detection(self.on_wake_word_detected):
                            start_time = time.time()
                        else:
                            print("❌ 唤醒词检测重启失败")
                            break
                
                # 停止唤醒词检测
                self.wake_detector.stop_detection()
            else:
                print("❌ 唤醒词检测启动失败")
                time.sleep(5)
                
        except Exception as e:
            print(f"❌ 唤醒词监听错误: {e}")
            time.sleep(5)
    
    def on_wake_word_detected(self, keyword):
        """唤醒词检测回调"""
        print(f"\n🎉 唤醒词检测到: {keyword}")
        
        # 改变状态到对话模式
        self.state = "conversation"
        self.last_conversation_time = time.time()
        
        # 播放唤醒提示
        if self.tts_method:
            try:
                self.tts_method("你好！我是快快，有什么可以帮你的吗？")
            except:
                print("🤖 你好！我是快快，有什么可以帮你的吗？")
        else:
            print("🤖 你好！我是快快，有什么可以帮你的吗？")
    
    def handle_conversation(self):
        """状态2: 处理对话（单一音频流）"""
        print("\n💬 进入对话模式...")
        
        conversation_rounds = 0
        max_rounds = 5  # 最多5轮对话
        
        while (self.state == "conversation" and 
               self.running and 
               conversation_rounds < max_rounds):
            
            # 检查对话超时
            if time.time() - self.last_conversation_time > self.conversation_timeout:
                print("⏰ 对话超时，返回待机模式")
                break
            
            # 进行一轮对话
            if self.single_conversation_round():
                conversation_rounds += 1
                self.last_conversation_time = time.time()
            else:
                print("❌ 对话失败，返回待机模式")
                break
        
        # 对话结束，返回待机状态
        print(f"💤 对话结束（{conversation_rounds}轮），返回待机模式")
        if self.tts_method:
            try:
                self.tts_method("好的，我先休息一下，需要时再叫我哦！")
            except:
                print("🤖 好的，我先休息一下，需要时再叫我哦！")
        
        self.state = "waiting"
    
    def single_conversation_round(self):
        """单轮对话"""
        try:
            print("\n🎙️ 请说话...")
            
            # 录音（单一音频流）
            with self.microphone as source:
                self.sr_recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.sr_recognizer.listen(source, timeout=10, phrase_time_limit=8)
            
            # 识别
            text = self.vosk_recognizer.recognize_from_speech_recognition_audio(audio)
            if not text or not text.strip():
                print("❌ 未识别到语音")
                return False
            
            print(f"📝 识别: {text}")
            
            # AI处理
            context = self.ai_manager.process_user_input(text)
            if context and context.ai_response:
                print(f"🤖 AI: {context.ai_response}")
                
                # 语音输出
                if self.tts_method:
                    try:
                        self.tts_method(context.ai_response)
                    except Exception as e:
                        print(f"⚠️ TTS失败: {e}")
                
                return True
            else:
                print("❌ AI处理失败")
                return False
                
        except sr.WaitTimeoutError:
            print("⏰ 录音超时")
            return False
        except Exception as e:
            print(f"❌ 对话错误: {e}")
            return False
    
    def stop_system(self):
        """停止系统"""
        print("\n🛑 停止AI对话系统...")
        
        self.running = False
        
        if self.wake_detector:
            self.wake_detector.stop_detection()
        
        if self.ai_manager:
            self.ai_manager.stop_conversation_mode()
        
        print("✅ 系统已停止")

def main():
    """主函数"""
    print("🤖 正确的AI对话系统")
    print("避免音频流冲突的状态机设计")
    print("=" * 50)
    
    system = CorrectAIConversationSystem()
    system.start_system()

if __name__ == "__main__":
    main()