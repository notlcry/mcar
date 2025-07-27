#!/usr/bin/env python3
# 直接测试Vosk中文语音识别

import os
import sys
import speech_recognition as sr

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

def test_vosk_recognition():
    """直接测试Vosk中文识别"""
    print("🎤 Vosk中文语音识别测试")
    print("=" * 40)
    
    try:
        from vosk_recognizer import VoskRecognizer
        
        # 创建Vosk识别器
        vosk_rec = VoskRecognizer()
        
        if not vosk_rec.is_available:
            print("❌ Vosk不可用")
            return False
        
        print("✅ Vosk识别器初始化成功")
        print("🎙️  请说中文，按Ctrl+C停止...")
        
        # 创建SpeechRecognition实例
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        # 调整环境噪音
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
        
        print(f"环境噪音阈值: {recognizer.energy_threshold}")
        print("开始监听...")
        
        while True:
            try:
                # 监听音频
                with microphone as source:
                    audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                
                print("🔄 正在识别...")
                
                # 使用Vosk识别
                result = vosk_rec.recognize_from_speech_recognition_audio(audio)
                
                if result:
                    print(f"✅ Vosk识别结果: '{result}'")
                else:
                    print("⚪ 未识别到内容")
                
            except sr.WaitTimeoutError:
                # 超时是正常的，继续监听
                pass
            except KeyboardInterrupt:
                print("\n👋 测试结束")
                break
            except Exception as e:
                print(f"❌ 识别错误: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_voice_controller():
    """测试增强语音控制器的语音识别"""
    print("\n🤖 测试增强语音控制器语音识别")
    print("=" * 40)
    
    try:
        from enhanced_voice_control import EnhancedVoiceController
        
        # 创建模拟机器人
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        mock_robot = MockRobot()
        
        # 创建增强语音控制器
        voice_controller = EnhancedVoiceController(robot=mock_robot)
        
        print(f"Vosk可用: {voice_controller.use_vosk}")
        
        if voice_controller.use_vosk and voice_controller.vosk_recognizer:
            print("✅ 增强语音控制器中的Vosk正常")
            
            # 模拟语音识别过程
            recognizer = sr.Recognizer()
            microphone = sr.Microphone()
            
            print("🎙️  说中文测试增强语音控制器...")
            
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
            
            # 使用增强语音控制器的Vosk识别
            result = voice_controller.vosk_recognizer.recognize_from_speech_recognition_audio(audio)
            
            if result:
                print(f"✅ 增强语音控制器识别结果: '{result}'")
            else:
                print("⚪ 未识别到内容")
            
            return True
        else:
            print("❌ 增强语音控制器中的Vosk不可用")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Vosk中文语音识别直接测试")
    print("=" * 50)
    
    # 测试独立的Vosk识别器
    vosk_ok = test_vosk_recognition()
    
    # 测试增强语音控制器中的Vosk
    enhanced_ok = test_enhanced_voice_controller()
    
    print("\n" + "=" * 50)
    print("📊 测试结果")
    print("=" * 50)
    
    if vosk_ok and enhanced_ok:
        print("🎉 Vosk中文语音识别完全正常！")
        print("\n💡 现在你可以:")
        print("• 通过Web界面进行AI文字对话")
        print("• 语音识别功能已就绪，只是唤醒词有问题")
        print("• 可以考虑修复唤醒词或使用其他方式触发语音识别")
    else:
        print("❌ 部分功能仍有问题")
    
    print(f"\n🌐 Web界面: http://192.168.2.201:5000")