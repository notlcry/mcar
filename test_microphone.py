#!/usr/bin/env python3
# 麦克风功能测试脚本

import speech_recognition as sr
import pyaudio
import sys

def test_pyaudio():
    """测试PyAudio麦克风访问"""
    print("🎤 测试PyAudio...")
    try:
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()
        print(f"   设备总数: {device_count}")
        
        input_devices = []
        for i in range(device_count):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                input_devices.append((i, info['name']))
        
        print(f"   输入设备: {len(input_devices)} 个")
        for i, name in input_devices:
            print(f"     设备 {i}: {name}")
        
        # 测试默认输入设备
        try:
            default_input = p.get_default_input_device_info()
            print(f"   ✅ 默认输入设备: {default_input['name']}")
            return True
        except Exception as e:
            print(f"   ❌ 默认输入设备: {e}")
            return False
        finally:
            p.terminate()
            
    except Exception as e:
        print(f"   ❌ PyAudio失败: {e}")
        return False

def test_speech_recognition():
    """测试SpeechRecognition麦克风访问"""
    print("🎙️  测试SpeechRecognition...")
    try:
        recognizer = sr.Recognizer()
        
        # 列出麦克风
        mic_list = sr.Microphone.list_microphone_names()
        print(f"   麦克风列表: {len(mic_list)} 个")
        
        # 创建麦克风实例
        microphone = sr.Microphone()
        print("   ✅ 麦克风实例创建成功")
        
        # 测试环境噪音调整
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print(f"   ✅ 环境噪音调整成功，阈值: {recognizer.energy_threshold}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ SpeechRecognition失败: {e}")
        return False

def test_voice_controller():
    """测试VoiceController初始化"""
    print("🤖 测试VoiceController...")
    try:
        import sys
        import os
        sys.path.insert(0, 'src')
        
        from voice_control import VoiceController
        
        # 创建模拟机器人
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        mock_robot = MockRobot()
        voice_controller = VoiceController(mock_robot)
        
        if voice_controller.microphone:
            print("   ✅ VoiceController麦克风初始化成功")
            return True
        else:
            print("   ❌ VoiceController麦克风初始化失败")
            return False
            
    except Exception as e:
        print(f"   ❌ VoiceController测试失败: {e}")
        return False

def main():
    print("🔍 麦克风功能测试")
    print("=" * 40)
    
    results = []
    
    # 运行所有测试
    results.append(("PyAudio", test_pyaudio()))
    results.append(("SpeechRecognition", test_speech_recognition()))
    results.append(("VoiceController", test_voice_controller()))
    
    # 显示结果
    print("\n📊 测试结果:")
    print("-" * 40)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name:20} {status}")
        if not passed:
            all_passed = False
    
    print("-" * 40)
    
    if all_passed:
        print("🎉 所有测试通过！麦克风功能正常")
        print("\n💡 现在可以:")
        print("• 启动AI桌宠系统")
        print("• 在Web界面启用语音控制")
        print("• 测试Vosk中文语音识别")
    else:
        print("❌ 部分测试失败")
        print("\n💡 建议:")
        print("• 运行: ./setup_audio.sh")
        print("• 检查USB麦克风连接")
        print("• 重启系统后再次测试")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)