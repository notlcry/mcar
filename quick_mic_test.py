#!/usr/bin/env python3
# 快速麦克风测试

import speech_recognition as sr
import pyaudio

def quick_test():
    print("🔍 快速麦克风诊断")
    print("=" * 30)
    
    # 1. 测试PyAudio
    try:
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()
        print(f"PyAudio设备数: {device_count}")
        
        input_devices = []
        for i in range(device_count):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                input_devices.append(i)
                print(f"输入设备 {i}: {info['name']}")
        
        print(f"输入设备总数: {len(input_devices)}")
        
        # 测试默认输入设备
        try:
            default_input = p.get_default_input_device_info()
            print(f"✅ 默认输入设备: {default_input['name']}")
        except Exception as e:
            print(f"❌ 默认输入设备: {e}")
        
        p.terminate()
        
    except Exception as e:
        print(f"❌ PyAudio失败: {e}")
    
    # 2. 测试SpeechRecognition
    try:
        print("\n测试SpeechRecognition...")
        recognizer = sr.Recognizer()
        
        # 列出麦克风
        mic_list = sr.Microphone.list_microphone_names()
        print(f"SR麦克风列表: {mic_list}")
        
        # 尝试创建麦克风
        microphone = sr.Microphone()
        print("✅ SR麦克风创建成功")
        
        # 尝试调整噪音
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print("✅ 环境噪音调整成功")
        
    except Exception as e:
        print(f"❌ SpeechRecognition失败: {e}")

if __name__ == "__main__":
    quick_test()