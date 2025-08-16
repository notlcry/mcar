#!/usr/bin/env python3
"""
测试修复后的Vosk中文识别
专注于验证FinalResult()修复是否有效
"""

import os
import sys
import speech_recognition as sr
import logging

# 设置简单日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, 'src')

def test_fixed_vosk():
    """测试修复后的Vosk识别"""
    print("🔧 测试修复后的Vosk中文识别")
    print("=" * 40)
    
    # 初始化
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    # 导入修复后的Vosk
    try:
        from vosk_recognizer import VoskRecognizer
        vosk_recognizer = VoskRecognizer()
        
        if not vosk_recognizer.is_available:
            print("❌ Vosk不可用")
            return False
            
        print("✅ Vosk中文识别器初始化成功")
    except Exception as e:
        print(f"❌ Vosk初始化失败: {e}")
        return False
    
    # 简单测试
    print("\n🎙️ 请说一句中文（如：你好、今天天气很好）")
    input("按Enter开始录音...")
    
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("正在录音...")
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=6)
        
        print("📍 开始Vosk识别...")
        result = vosk_recognizer.recognize_from_speech_recognition_audio(audio)
        
        if result and result.strip():
            print(f"🎉 识别成功: '{result}'")
            return True
        else:
            print("😞 Vosk仍然返回空结果")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_google_as_backup():
    """测试Google识别作为备选"""
    print("\n🌐 测试Google识别（需要网络）")
    
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    print("🎙️ 请再说一句中文")
    input("按Enter开始录音...")
    
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=6)
        
        print("📍 开始Google识别...")
        result = recognizer.recognize_google(audio, language='zh-CN')
        
        if result and result.strip():
            print(f"🎉 Google识别成功: '{result}'")
            return True
        else:
            print("😞 Google返回空结果")
            return False
            
    except sr.UnknownValueError:
        print("❌ Google无法理解音频")
        return False
    except sr.RequestError as e:
        print(f"❌ Google请求错误: {e}")
        print("💡 可能需要安装: sudo apt-get install flac")
        return False
    except Exception as e:
        print(f"❌ Google识别失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 修复后的中文语音识别测试")
    print("重点测试FinalResult()修复是否有效")
    print("=" * 50)
    
    # 测试修复后的Vosk
    vosk_success = test_fixed_vosk()
    
    if vosk_success:
        print("\n🎉 Vosk修复成功！中文识别正常工作")
    else:
        print("\n⚠️ Vosk仍有问题，测试Google备选方案...")
        google_success = test_google_as_backup()
        
        if google_success:
            print("\n💡 建议：优先使用Google识别，Vosk作为离线备选")
        else:
            print("\n😞 两个引擎都有问题")
            print("💡 可能需要:")
            print("1. 安装flac: sudo apt-get install flac")
            print("2. 检查网络连接")
            print("3. 在更安静环境中测试")
    
    print("\n📋 总结:")
    print("- 如果Vosk修复成功，就可以用于离线中文识别")
    print("- 如果Google可用，可以作为在线备选方案")
    print("- PocketSphinx可以保留用于英文识别")