#!/usr/bin/env python3
# 调试语音识别问题

import os
import sys
import logging

# 设置详细日志
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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

def debug_voice_recognition():
    print("🔍 调试语音识别问题")
    print("=" * 50)
    
    try:
        # 1. 测试Vosk识别器单独工作
        print("1. 测试Vosk识别器...")
        from vosk_recognizer import VoskRecognizer
        
        vosk_rec = VoskRecognizer()
        print(f"   Vosk可用: {vosk_rec.is_available}")
        
        if vosk_rec.is_available:
            print("   ✅ Vosk识别器单独工作正常")
        else:
            print("   ❌ Vosk识别器不可用")
            return False
        
        # 2. 测试增强语音控制器中的Vosk
        print("\n2. 测试增强语音控制器中的Vosk...")
        from enhanced_voice_control import EnhancedVoiceController
        
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        mock_robot = MockRobot()
        voice_controller = EnhancedVoiceController(robot=mock_robot)
        
        print(f"   use_vosk: {voice_controller.use_vosk}")
        print(f"   vosk_recognizer存在: {hasattr(voice_controller, 'vosk_recognizer')}")
        
        if hasattr(voice_controller, 'vosk_recognizer') and voice_controller.vosk_recognizer:
            print(f"   vosk_recognizer.is_available: {voice_controller.vosk_recognizer.is_available}")
        
        # 3. 模拟语音识别过程
        print("\n3. 模拟语音识别过程...")
        
        # 创建一个模拟的音频数据
        import speech_recognition as sr
        
        # 创建静音音频用于测试
        sample_rate = 16000
        duration = 0.1
        frames = int(sample_rate * duration)
        audio_data = b'\x00\x00' * frames
        audio = sr.AudioData(audio_data, sample_rate, 2)
        
        # 测试Vosk识别
        if voice_controller.use_vosk and voice_controller.vosk_recognizer:
            try:
                result = voice_controller.vosk_recognizer.recognize_from_speech_recognition_audio(audio)
                print(f"   Vosk测试结果: {result}")
                print("   ✅ Vosk在增强语音控制器中工作正常")
            except Exception as e:
                print(f"   ❌ Vosk测试失败: {e}")
        else:
            print("   ❌ Vosk在增强语音控制器中不可用")
        
        return True
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_import_issues():
    print("\n🔍 检查导入问题")
    print("=" * 50)
    
    try:
        # 检查所有相关模块的导入
        modules_to_check = [
            'vosk',
            'vosk_recognizer', 
            'enhanced_voice_control',
            'speech_recognition'
        ]
        
        for module_name in modules_to_check:
            try:
                if module_name == 'vosk_recognizer':
                    sys.path.insert(0, 'src')
                
                __import__(module_name)
                print(f"✅ {module_name} 导入成功")
            except ImportError as e:
                print(f"❌ {module_name} 导入失败: {e}")
            except Exception as e:
                print(f"⚠️  {module_name} 导入有问题: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查导入失败: {e}")
        return False

def suggest_fix():
    print("\n💡 问题修复建议")
    print("=" * 50)
    
    print("基于调试结果，可能的问题和解决方案:")
    print()
    print("1. 如果Vosk单独工作但在增强语音控制器中不工作:")
    print("   • 可能是导入路径问题")
    print("   • 需要重启Python进程让新代码生效")
    print()
    print("2. 如果Vosk完全不可用:")
    print("   • 检查模型文件是否存在")
    print("   • 检查Vosk库是否正确安装")
    print()
    print("3. 强制重启解决方案:")
    print("   • 停止当前AI桌宠系统 (Ctrl+C)")
    print("   • 清理Python缓存: find . -name '*.pyc' -delete")
    print("   • 重新启动: ./start_ai_pet_quiet.sh")
    print()
    print("4. 添加调试日志:")
    print("   • 在语音识别代码中添加更多日志")
    print("   • 确认哪个识别引擎被实际调用")

if __name__ == "__main__":
    print("🔧 语音识别调试工具")
    print("=" * 50)
    
    import_ok = check_import_issues()
    debug_ok = debug_voice_recognition()
    
    suggest_fix()
    
    print("\n" + "=" * 50)
    print("📊 调试结果")
    print("=" * 50)
    
    if import_ok and debug_ok:
        print("✅ 基础功能正常，问题可能在运行时")
        print("建议重启AI桌宠系统让新代码生效")
    else:
        print("❌ 发现基础问题，需要先解决导入或配置问题")
    
    print("\n🚀 下一步:")
    print("1. 重启AI桌宠系统")
    print("2. 观察启动日志中的Vosk初始化信息")
    print("3. 测试中文语音，观察识别日志")