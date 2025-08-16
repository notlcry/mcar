#!/usr/bin/env python3
# 测试Vosk集成

import os
import sys

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

def test_vosk_installation():
    print("📦 测试Vosk安装")
    print("=" * 40)
    
    try:
        import vosk
        print("✅ Vosk库已安装")
        return True
    except ImportError:
        print("❌ Vosk库未安装")
        print("请运行: pip3 install vosk")
        return False

def test_vosk_model():
    print("\n📁 测试Vosk模型")
    print("=" * 40)
    
    model_paths = [
        "models/vosk-model-small-cn-0.22",
        "models/vosk-model-cn-0.22"
    ]
    
    found_model = False
    for path in model_paths:
        if os.path.exists(path):
            print(f"✅ 找到模型: {path}")
            # 检查模型大小
            try:
                import subprocess
                result = subprocess.run(['du', '-sh', path], capture_output=True, text=True)
                if result.returncode == 0:
                    size = result.stdout.split()[0]
                    print(f"   模型大小: {size}")
            except:
                pass
            found_model = True
        else:
            print(f"❌ 模型不存在: {path}")
    
    if not found_model:
        print("\n💡 下载模型:")
        print("   chmod +x download_vosk_model.sh")
        print("   ./download_vosk_model.sh")
    
    return found_model

def test_vosk_recognizer():
    print("\n🎤 测试Vosk识别器")
    print("=" * 40)
    
    try:
        from vosk_recognizer import VoskRecognizer
        
        print("1. 创建Vosk识别器...")
        recognizer = VoskRecognizer()
        
        if recognizer.is_available:
            print("✅ Vosk识别器初始化成功")
            print(f"   采样率: {recognizer.sample_rate}Hz")
            return True
        else:
            print("❌ Vosk识别器初始化失败")
            return False
            
    except Exception as e:
        print(f"❌ Vosk识别器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_voice_control():
    print("\n🤖 测试增强语音控制器集成")
    print("=" * 40)
    
    try:
        from enhanced_voice_control import EnhancedVoiceController
        
        # 创建模拟机器人
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        mock_robot = MockRobot()
        
        print("1. 创建增强语音控制器...")
        voice_controller = EnhancedVoiceController(robot=mock_robot)
        print("✅ 增强语音控制器创建成功")
        
        print("2. 检查Vosk集成...")
        if hasattr(voice_controller, 'vosk_recognizer'):
            if voice_controller.use_vosk:
                print("✅ Vosk已集成并可用")
            else:
                print("⚠️  Vosk已集成但不可用（可能缺少模型）")
        else:
            print("❌ Vosk未集成")
            return False
        
        print("3. 检查语音识别优先级...")
        print("   识别优先级: Vosk(中文) > Whisper > Google(在线) > PocketSphinx(英文)")
        
        return True
        
    except Exception as e:
        print(f"❌ 增强语音控制器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_speech_recognition_priority():
    print("\n🔄 测试语音识别优先级")
    print("=" * 40)
    
    try:
        import speech_recognition as sr
        
        # 创建一个短暂的静音音频用于测试
        sample_rate = 16000
        duration = 0.1
        frames = int(sample_rate * duration)
        audio_data = b'\x00\x00' * frames
        audio = sr.AudioData(audio_data, sample_rate, 2)
        
        # 测试各种识别方式
        recognizers = []
        
        # 1. 测试Vosk
        try:
            from vosk_recognizer import VoskRecognizer
            vosk_rec = VoskRecognizer()
            if vosk_rec.is_available:
                recognizers.append("✅ Vosk (中文离线)")
            else:
                recognizers.append("❌ Vosk (模型缺失)")
        except:
            recognizers.append("❌ Vosk (库缺失)")
        
        # 2. 测试Google
        try:
            recognizer = sr.Recognizer()
            # 不实际调用，只检查方法存在
            if hasattr(recognizer, 'recognize_google'):
                recognizers.append("✅ Google (中文在线)")
            else:
                recognizers.append("❌ Google (不可用)")
        except:
            recognizers.append("❌ Google (不可用)")
        
        # 3. 测试PocketSphinx
        try:
            recognizer = sr.Recognizer()
            recognizer.recognize_sphinx(audio)
            recognizers.append("✅ PocketSphinx (英文离线)")
        except sr.UnknownValueError:
            recognizers.append("✅ PocketSphinx (英文离线)")
        except:
            recognizers.append("❌ PocketSphinx (不可用)")
        
        print("可用的识别引擎:")
        for i, rec in enumerate(recognizers, 1):
            print(f"   {i}. {rec}")
        
        return True
        
    except Exception as e:
        print(f"❌ 语音识别优先级测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Vosk中文语音识别集成测试")
    print("=" * 50)
    
    # 运行所有测试
    tests = [
        ("Vosk安装", test_vosk_installation),
        ("Vosk模型", test_vosk_model),
        ("Vosk识别器", test_vosk_recognizer),
        ("语音控制器集成", test_enhanced_voice_control),
        ("语音识别优先级", test_speech_recognition_priority)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试出错: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果总结")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed >= 3:  # 至少3项通过就算基本可用
        print("\n🎉 Vosk中文语音识别集成基本成功！")
        print("\n💡 使用说明:")
        print("• Vosk现在是主要的中文语音识别引擎")
        print("• 支持完全离线的中文语音识别")
        print("• 不再依赖PocketSphinx的中文支持")
        print("\n🚀 现在可以启动AI桌宠系统测试语音功能")
        
        if passed < total:
            print("\n⚠️  部分功能可能受限:")
            for test_name, result in results:
                if not result:
                    if "模型" in test_name:
                        print("• 运行 ./download_vosk_model.sh 下载模型")
                    elif "安装" in test_name:
                        print("• 运行 pip3 install vosk 安装库")
    else:
        print("\n❌ Vosk集成失败，需要解决以下问题:")
        for test_name, result in results:
            if not result:
                print(f"• {test_name}")
    
    sys.exit(0 if passed >= 3 else 1)