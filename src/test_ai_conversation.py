#!/usr/bin/python3
"""
AI对话系统测试脚本
测试Google Gemini API连接、语音识别、TTS和唤醒词检测
"""

import os
import sys
import time
import logging
from ai_conversation import AIConversationManager
from enhanced_voice_control import EnhancedVoiceController
from wake_word_detector import WakeWordDetector, SimpleWakeWordDetector

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gemini_api():
    """测试Gemini API连接"""
    print("\n=== 测试Gemini API连接 ===")
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ 未设置GEMINI_API_KEY环境变量")
        print("请运行: export GEMINI_API_KEY='your_api_key'")
        return False
    
    try:
        ai_manager = AIConversationManager()
        
        if not ai_manager.model:
            print("❌ Gemini模型初始化失败")
            return False
        
        # 测试简单对话
        if ai_manager.start_conversation_mode():
            print("✅ Gemini API连接成功")
            
            # 测试对话
            context = ai_manager.process_user_input("你好，请简单介绍一下自己")
            
            if context and context.ai_response:
                print(f"🤖 AI回复: {context.ai_response}")
                print(f"😊 检测情感: {context.emotion_detected}")
                print("✅ 对话功能正常")
            else:
                print("❌ 对话功能异常")
                return False
            
            ai_manager.stop_conversation_mode()
            return True
        else:
            print("❌ 对话模式启动失败")
            return False
            
    except Exception as e:
        print(f"❌ Gemini API测试失败: {e}")
        return False

def test_tts():
    """测试TTS功能"""
    print("\n=== 测试TTS语音合成 ===")
    
    try:
        import edge_tts
        import asyncio
        import tempfile
        import subprocess
        
        async def test_edge_tts():
            text = "你好，我是圆滚滚，这是TTS测试"
            voice = "zh-CN-XiaoxiaoNeural"
            
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = temp_file.name
            
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(temp_path)
            
            print("✅ TTS语音生成成功")
            print(f"📁 音频文件: {temp_path}")
            
            # 尝试播放（可选）
            try:
                subprocess.run(['aplay', temp_path], check=True, capture_output=True)
                print("🔊 音频播放成功")
            except:
                print("⚠️  音频播放失败（可能需要安装aplay）")
            
            os.unlink(temp_path)
            return True
        
        return asyncio.run(test_edge_tts())
        
    except Exception as e:
        print(f"❌ TTS测试失败: {e}")
        return False

def test_wake_word_detection():
    """测试唤醒词检测"""
    print("\n=== 测试唤醒词检测 ===")
    
    detected = False
    
    def on_wake_word(index):
        nonlocal detected
        detected = True
        print(f"✅ 检测到唤醒词！索引: {index}")
    
    # 首先尝试Porcupine
    detector = WakeWordDetector()
    
    if detector.porcupine:
        print("🎯 使用Porcupine检测器")
        print("请说 'computer' 进行测试（10秒内）")
    else:
        print("🎯 使用简单检测器")
        detector = SimpleWakeWordDetector()
        print("请说 '喵喵小车' 进行测试（10秒内）")
    
    try:
        if detector.start_detection(on_wake_word):
            # 等待10秒
            for i in range(10):
                if detected:
                    break
                time.sleep(1)
                print(f"⏰ 等待中... {10-i}秒")
            
            detector.stop_detection()
            
            if detected:
                print("✅ 唤醒词检测功能正常")
                return True
            else:
                print("⚠️  未检测到唤醒词（可能是麦克风问题）")
                return False
        else:
            print("❌ 唤醒词检测启动失败")
            return False
            
    except Exception as e:
        print(f"❌ 唤醒词检测测试失败: {e}")
        return False

def test_speech_recognition():
    """测试语音识别"""
    print("\n=== 测试语音识别 ===")
    
    try:
        import speech_recognition as sr
        
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        print("🎤 调整环境噪音...")
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=2)
        
        print("🎤 请说话进行测试（5秒内）...")
        
        with microphone as source:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
        
        print("🔄 正在识别...")
        
        # 尝试使用PocketSphinx
        try:
            text = recognizer.recognize_sphinx(audio)
            print(f"✅ 识别结果: {text}")
            return True
        except sr.UnknownValueError:
            print("⚠️  无法理解音频内容")
            return False
        except sr.RequestError as e:
            print(f"❌ 语音识别服务错误: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 语音识别测试失败: {e}")
        return False

def test_integrated_system():
    """测试集成系统"""
    print("\n=== 测试集成系统 ===")
    
    try:
        # 创建增强语音控制器
        enhanced_voice = EnhancedVoiceController()
        
        print("🚀 启动AI对话模式...")
        if enhanced_voice.start_conversation_mode():
            print("✅ AI对话模式启动成功")
            
            # 测试状态获取
            status = enhanced_voice.get_conversation_status()
            print(f"📊 系统状态: {status}")
            
            # 测试TTS
            print("🔊 测试语音播报...")
            enhanced_voice.speak_text("系统测试完成，一切正常！")
            
            time.sleep(2)  # 等待TTS完成
            
            enhanced_voice.stop_conversation_mode()
            print("✅ 集成系统测试完成")
            return True
        else:
            print("❌ AI对话模式启动失败")
            return False
            
    except Exception as e:
        print(f"❌ 集成系统测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🤖 AI桌宠系统测试开始")
    print("=" * 50)
    
    tests = [
        ("Gemini API连接", test_gemini_api),
        ("TTS语音合成", test_tts),
        ("语音识别", test_speech_recognition),
        ("唤醒词检测", test_wake_word_detection),
        ("集成系统", test_integrated_system)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except KeyboardInterrupt:
            print(f"\n⏹️  测试被用户中断")
            break
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n" + "=" * 50)
    print("📋 测试结果汇总:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📊 总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！AI桌宠系统准备就绪")
    else:
        print("⚠️  部分测试失败，请检查配置和依赖")
        print("\n💡 常见问题解决方案:")
        print("1. 确保已设置GEMINI_API_KEY环境变量")
        print("2. 检查麦克风和音频设备连接")
        print("3. 运行 ./install_ai_dependencies.sh 安装依赖")
        print("4. 确保网络连接正常")

if __name__ == "__main__":
    main()