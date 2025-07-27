#!/usr/bin/env python3
"""
AI对话功能测试和调试
专门测试语音识别在对话模式下的准确性
"""

import os
import sys
import time
import threading
import speech_recognition as sr
import tempfile
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
    except:
        pass

load_env()
sys.path.insert(0, 'src')

def test_speech_recognition_engines():
    """测试各种语音识别引擎的准确性"""
    print("🎤 测试语音识别引擎准确性")
    print("=" * 50)
    
    # 初始化识别器
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    # 调整识别器参数
    with microphone as source:
        print("🔧 调整环境噪音...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
    
    recognizer.energy_threshold = 300
    recognizer.pause_threshold = 0.8
    recognizer.timeout = 1
    
    print(f"✅ 识别器参数: energy_threshold={recognizer.energy_threshold}, pause_threshold={recognizer.pause_threshold}")
    
    # 测试不同的识别引擎
    engines = [
        ("Vosk中文", test_vosk_recognition),
        ("Google中文", test_google_recognition),
        ("Whisper", test_whisper_recognition),
        ("PocketSphinx英文", test_sphinx_recognition)
    ]
    
    for engine_name, test_func in engines:
        print(f"\n🧪 测试 {engine_name} 识别引擎")
        print("-" * 30)
        
        try:
            success = test_func(recognizer, microphone)
            if success:
                print(f"✅ {engine_name} 测试成功")
            else:
                print(f"❌ {engine_name} 测试失败")
        except Exception as e:
            print(f"❌ {engine_name} 测试出错: {e}")
        
        print()

def test_vosk_recognition(recognizer, microphone):
    """测试Vosk中文识别"""
    try:
        from vosk_recognizer import VoskRecognizer
        
        vosk_recognizer = VoskRecognizer()
        if not vosk_recognizer.is_available:
            print("⚠️  Vosk不可用")
            return False
        
        print("🎙️  请说一句中文（5秒内）...")
        print("💡 建议测试: '你好机器人' 或 '今天天气怎么样'")
        
        with microphone as source:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        
        print("🔍 Vosk识别中...")
        text = vosk_recognizer.recognize_from_speech_recognition_audio(audio)
        
        if text:
            print(f"✅ Vosk识别结果: '{text}'")
            return True
        else:
            print("❌ Vosk未识别到内容")
            return False
            
    except Exception as e:
        print(f"❌ Vosk测试失败: {e}")
        return False

def test_google_recognition(recognizer, microphone):
    """测试Google中文识别"""
    try:
        print("🎙️  请说一句中文（5秒内）...")
        print("💡 建议测试: '你好机器人' 或 '今天天气怎么样'")
        
        with microphone as source:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        
        print("🔍 Google识别中...")
        text = recognizer.recognize_google(audio, language='zh-CN')
        
        if text:
            print(f"✅ Google识别结果: '{text}'")
            return True
        else:
            print("❌ Google未识别到内容")
            return False
            
    except sr.UnknownValueError:
        print("❌ Google无法理解音频")
        return False
    except sr.RequestError as e:
        print(f"❌ Google服务错误: {e}")
        return False
    except Exception as e:
        print(f"❌ Google测试失败: {e}")
        return False

def test_whisper_recognition(recognizer, microphone):
    """测试Whisper识别"""
    try:
        from whisper_integration import get_whisper_recognizer
        
        whisper_recognizer = get_whisper_recognizer("base")
        if not whisper_recognizer.model:
            print("⚠️  Whisper不可用")
            return False
        
        print("🎙️  请说一句话（5秒内，中文或英文）...")
        print("💡 建议测试: '你好机器人' 或 'Hello robot'")
        
        with microphone as source:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        
        print("🔍 Whisper识别中...")
        
        # 将音频保存为临时文件
        wav_data = audio.get_wav_data()
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(wav_data)
            temp_file_path = temp_file.name
        
        try:
            text = whisper_recognizer.recognize_audio_file(temp_file_path)
            if text:
                print(f"✅ Whisper识别结果: '{text}'")
                return True
            else:
                print("❌ Whisper未识别到内容")
                return False
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            
    except Exception as e:
        print(f"❌ Whisper测试失败: {e}")
        return False

def test_sphinx_recognition(recognizer, microphone):
    """测试PocketSphinx英文识别"""
    try:
        print("🎙️  请说一句英文（5秒内）...")
        print("💡 建议测试: 'Hello robot' 或 'How are you'")
        
        with microphone as source:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        
        print("🔍 PocketSphinx识别中...")
        text = recognizer.recognize_sphinx(audio)
        
        if text:
            print(f"✅ PocketSphinx识别结果: '{text}'")
            return True
        else:
            print("❌ PocketSphinx未识别到内容")
            return False
            
    except sr.UnknownValueError:
        print("❌ PocketSphinx无法理解音频")
        return False
    except Exception as e:
        print(f"❌ PocketSphinx测试失败: {e}")
        return False

def test_ai_conversation_flow():
    """测试完整的AI对话流程"""
    print("\n🤖 测试完整AI对话流程")
    print("=" * 50)
    
    try:
        from enhanced_voice_control import EnhancedVoiceController
        from ai_conversation import AIConversationManager
        
        # 创建模拟机器人
        class MockRobot:
            def t_stop(self, duration=0):
                pass
            def turnRight(self, angle, duration):
                print(f"🤖 机器人右转 {angle}度，持续{duration}秒")
            def turnLeft(self, angle, duration):
                print(f"🤖 机器人左转 {angle}度，持续{duration}秒")
        
        mock_robot = MockRobot()
        
        # 创建AI对话管理器
        ai_manager = AIConversationManager(mock_robot)
        
        # 创建增强语音控制器
        voice_controller = EnhancedVoiceController(
            robot=mock_robot,
            ai_conversation_manager=ai_manager
        )
        
        print("✅ AI对话系统初始化成功")
        
        # 启动对话模式
        if voice_controller.start_conversation_mode():
            print("✅ 对话模式启动成功")
            
            # 强制唤醒进行测试
            voice_controller.force_wake_up()
            
            print("\n🎙️  AI对话测试说明:")
            print("• 现在处于唤醒状态，可以直接对话")
            print("• 尝试说: '你好' '你是谁' '今天天气怎么样'")
            print("• 系统会显示识别结果和AI回复")
            print("• 按Ctrl+C退出测试")
            
            # 启动监听线程
            listen_thread = threading.Thread(target=voice_controller.listen_continuously, daemon=True)
            listen_thread.start()
            
            # 保持运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 停止AI对话测试...")
                voice_controller.stop_conversation_mode()
                print("✅ 测试结束")
                
        else:
            print("❌ 对话模式启动失败")
            return False
            
    except Exception as e:
        print(f"❌ AI对话测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def interactive_recognition_test():
    """交互式语音识别测试"""
    print("\n🎯 交互式语音识别测试")
    print("=" * 50)
    
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    # 调整环境噪音
    with microphone as source:
        print("🔧 调整环境噪音...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
    
    print("🎙️  交互式测试开始")
    print("💡 每次会提示你说话，然后显示各引擎的识别结果")
    print("💡 输入 'q' 退出测试")
    
    test_count = 1
    
    while True:
        print(f"\n--- 测试 {test_count} ---")
        user_input = input("按Enter开始录音，或输入'q'退出: ").strip()
        
        if user_input.lower() == 'q':
            break
        
        print("🎙️  请说话（3秒内）...")
        
        try:
            with microphone as source:
                audio = recognizer.listen(source, timeout=3, phrase_time_limit=5)
            
            print("🔍 正在使用多个引擎识别...")
            
            # 测试Google识别
            try:
                google_result = recognizer.recognize_google(audio, language='zh-CN')
                print(f"🌐 Google: '{google_result}'")
            except Exception as e:
                print(f"🌐 Google: 识别失败 ({e})")
            
            # 测试Vosk识别
            try:
                from vosk_recognizer import VoskRecognizer
                vosk_recognizer = VoskRecognizer()
                if vosk_recognizer.is_available:
                    vosk_result = vosk_recognizer.recognize_from_speech_recognition_audio(audio)
                    print(f"🇨🇳 Vosk: '{vosk_result}'")
                else:
                    print("🇨🇳 Vosk: 不可用")
            except Exception as e:
                print(f"🇨🇳 Vosk: 识别失败 ({e})")
            
            # 测试Whisper识别
            try:
                from whisper_integration import get_whisper_recognizer
                whisper_recognizer = get_whisper_recognizer("base")
                if whisper_recognizer.model:
                    wav_data = audio.get_wav_data()
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                        temp_file.write(wav_data)
                        temp_file_path = temp_file.name
                    
                    try:
                        whisper_result = whisper_recognizer.recognize_audio_file(temp_file_path)
                        print(f"🌍 Whisper: '{whisper_result}'")
                    finally:
                        if os.path.exists(temp_file_path):
                            os.unlink(temp_file_path)
                else:
                    print("🌍 Whisper: 不可用")
            except Exception as e:
                print(f"🌍 Whisper: 识别失败 ({e})")
            
            test_count += 1
            
        except sr.WaitTimeoutError:
            print("⏰ 录音超时，请重试")
        except Exception as e:
            print(f"❌ 录音失败: {e}")
    
    print("✅ 交互式测试结束")

if __name__ == "__main__":
    print("🤖 AI对话功能测试")
    print("=" * 60)
    
    while True:
        print("\n选择测试模式:")
        print("1. 测试各语音识别引擎")
        print("2. 完整AI对话流程测试")
        print("3. 交互式识别测试")
        print("4. 退出")
        
        choice = input("\n请选择 (1-4): ").strip()
        
        if choice == '1':
            test_speech_recognition_engines()
        elif choice == '2':
            test_ai_conversation_flow()
        elif choice == '3':
            interactive_recognition_test()
        elif choice == '4':
            print("👋 测试结束")
            break
        else:
            print("❌ 无效选择，请重试")