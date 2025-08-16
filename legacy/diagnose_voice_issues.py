#!/usr/bin/env python3
"""
语音功能诊断脚本 - 逐步检查语音识别和唤醒功能
"""

import os
import sys
import time
import subprocess

def load_env():
    """加载环境变量"""
    try:
        with open('.ai_pet_env', 'r') as f:
            for line in f:
                if line.startswith('export ') and '=' in line:
                    line = line.replace('export ', '').strip()
                    key, value = line.split('=', 1)
                    value = value.strip('"')
                    os.environ[key] = value
        print("✅ 环境变量加载成功")
        return True
    except Exception as e:
        print(f"❌ 环境变量加载失败: {e}")
        return False

def check_audio_system():
    """检查音频系统"""
    print("\n🔊 步骤1: 检查音频系统")
    print("-" * 40)
    
    # 检查ALSA
    try:
        result = subprocess.run(['arecord', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ALSA录音设备:")
            print(result.stdout)
        else:
            print("❌ ALSA录音设备检查失败")
            return False
    except FileNotFoundError:
        print("❌ arecord命令不存在，ALSA可能未安装")
        return False
    
    # 检查播放设备
    try:
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ALSA播放设备:")
            print(result.stdout)
        else:
            print("❌ ALSA播放设备检查失败")
    except FileNotFoundError:
        print("❌ aplay命令不存在")
    
    return True

def check_microphone():
    """检查麦克风"""
    print("\n🎤 步骤2: 检查麦克风")
    print("-" * 40)
    
    try:
        import pyaudio
        
        # 初始化PyAudio
        p = pyaudio.PyAudio()
        
        print("✅ PyAudio初始化成功")
        print(f"   音频设备数量: {p.get_device_count()}")
        
        # 列出所有音频设备
        print("\n📱 可用音频设备:")
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:  # 输入设备
                print(f"   设备 {i}: {info['name']} (输入通道: {info['maxInputChannels']})")
        
        # 测试默认输入设备
        try:
            default_input = p.get_default_input_device_info()
            print(f"\n✅ 默认输入设备: {default_input['name']}")
            print(f"   采样率: {default_input['defaultSampleRate']}")
            print(f"   输入通道: {default_input['maxInputChannels']}")
            
            # 尝试打开音频流
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
            print("✅ 音频流打开成功")
            stream.close()
            
        except Exception as e:
            print(f"❌ 默认输入设备测试失败: {e}")
            p.terminate()
            return False
        
        p.terminate()
        return True
        
    except ImportError:
        print("❌ PyAudio未安装")
        return False
    except Exception as e:
        print(f"❌ 麦克风检查失败: {e}")
        return False

def check_porcupine():
    """检查Porcupine唤醒词检测"""
    print("\n🐷 步骤3: 检查Porcupine唤醒词检测")
    print("-" * 40)
    
    try:
        import pvporcupine
        
        access_key = os.getenv('PICOVOICE_ACCESS_KEY')
        if not access_key:
            print("❌ PICOVOICE_ACCESS_KEY未设置")
            return False
        
        print(f"✅ API密钥已设置: {access_key[:20]}...")
        
        # 测试内置唤醒词
        try:
            porcupine = pvporcupine.create(
                access_key=access_key,
                keywords=['picovoice']
            )
            print("✅ 内置唤醒词 'picovoice' 初始化成功")
            print(f"   帧长度: {porcupine.frame_length}")
            print(f"   采样率: {porcupine.sample_rate}")
            porcupine.delete()
        except Exception as e:
            print(f"❌ 内置唤醒词测试失败: {e}")
            return False
        
        # 测试自定义唤醒词（如果存在）
        custom_wake_word_path = 'src/wake_words/kk_zh_raspberry-pi_v3_0_0.ppn'
        model_path = 'src/wake_words/porcupine_params_zh.pv'
        
        if os.path.exists(custom_wake_word_path) and os.path.exists(model_path):
            try:
                porcupine = pvporcupine.create(
                    access_key=access_key,
                    model_path=model_path,
                    keyword_paths=[custom_wake_word_path]
                )
                print("✅ 自定义唤醒词 'kk' 初始化成功")
                porcupine.delete()
            except Exception as e:
                print(f"⚠️  自定义唤醒词测试失败: {e}")
                print("   将使用内置唤醒词")
        else:
            print("ℹ️  自定义唤醒词文件不存在，使用内置唤醒词")
        
        return True
        
    except ImportError:
        print("❌ pvporcupine未安装")
        return False
    except Exception as e:
        print(f"❌ Porcupine检查失败: {e}")
        return False

def check_speech_recognition():
    """检查语音识别"""
    print("\n🗣️  步骤4: 检查语音识别")
    print("-" * 40)
    
    try:
        import speech_recognition as sr
        
        # 创建识别器
        r = sr.Recognizer()
        
        print("✅ SpeechRecognition库加载成功")
        
        # 检查麦克风
        try:
            with sr.Microphone() as source:
                print("✅ 麦克风访问成功")
                print("   正在调整环境噪音...")
                r.adjust_for_ambient_noise(source, duration=1)
                print(f"   环境噪音阈值: {r.energy_threshold}")
        except Exception as e:
            print(f"❌ 麦克风访问失败: {e}")
            return False
        
        # 检查可用的识别引擎
        print("\n🔍 可用的识别引擎:")
        engines = []
        
        # 测试Google识别（需要网络）
        try:
            # 这里不实际测试，只检查方法是否存在
            if hasattr(r, 'recognize_google'):
                engines.append("Google (在线)")
        except:
            pass
        
        # 测试Whisper（如果安装了）
        try:
            import whisper
            engines.append("Whisper (离线)")
        except ImportError:
            pass
        
        # 测试PocketSphinx（离线）
        try:
            if hasattr(r, 'recognize_sphinx'):
                engines.append("PocketSphinx (离线)")
        except:
            pass
        
        if engines:
            for engine in engines:
                print(f"   ✅ {engine}")
        else:
            print("   ❌ 没有可用的识别引擎")
            return False
        
        return True
        
    except ImportError:
        print("❌ speech_recognition未安装")
        return False
    except Exception as e:
        print(f"❌ 语音识别检查失败: {e}")
        return False

def check_voice_modules():
    """检查语音模块"""
    print("\n📦 步骤5: 检查语音模块")
    print("-" * 40)
    
    sys.path.insert(0, 'src')
    
    modules_to_check = [
        ('enhanced_voice_control', '增强语音控制'),
        ('wake_word_detector', '唤醒词检测器'),
        ('voice_control', '基础语音控制')
    ]
    
    success_count = 0
    
    for module_name, display_name in modules_to_check:
        try:
            module = __import__(module_name)
            print(f"✅ {display_name} - 模块加载成功")
            
            # 检查关键类是否存在
            if module_name == 'enhanced_voice_control' and hasattr(module, 'EnhancedVoiceController'):
                print(f"   ✅ EnhancedVoiceController类存在")
            elif module_name == 'wake_word_detector' and hasattr(module, 'WakeWordDetector'):
                print(f"   ✅ WakeWordDetector类存在")
            elif module_name == 'voice_control' and hasattr(module, 'VoiceController'):
                print(f"   ✅ VoiceController类存在")
            
            success_count += 1
            
        except ImportError as e:
            print(f"❌ {display_name} - 导入失败: {e}")
        except Exception as e:
            print(f"⚠️  {display_name} - 有问题: {e}")
    
    return success_count > 0

def test_voice_initialization():
    """测试语音系统初始化"""
    print("\n🚀 步骤6: 测试语音系统初始化")
    print("-" * 40)
    
    try:
        sys.path.insert(0, 'src')
        
        # 测试增强语音控制器初始化
        from enhanced_voice_control import EnhancedVoiceController
        
        print("正在初始化增强语音控制器...")
        
        # 创建一个模拟的机器人控制器
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        mock_robot = MockRobot()
        
        # 尝试创建语音控制器
        voice_controller = EnhancedVoiceController(robot=mock_robot)
        print("✅ 增强语音控制器创建成功")
        
        # 检查关键组件
        if hasattr(voice_controller, 'wake_word_detector'):
            print("✅ 唤醒词检测器组件存在")
        else:
            print("❌ 唤醒词检测器组件缺失")
        
        if hasattr(voice_controller, 'speech_recognizer'):
            print("✅ 语音识别器组件存在")
        else:
            print("❌ 语音识别器组件缺失")
        
        return True
        
    except Exception as e:
        print(f"❌ 语音系统初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 50)
    print("🔍 AI桌宠语音功能诊断")
    print("=" * 50)
    
    if not load_env():
        print("\n❌ 环境变量加载失败，请检查.ai_pet_env文件")
        return False
    
    # 逐步检查
    checks = [
        ("音频系统", check_audio_system),
        ("麦克风", check_microphone),
        ("Porcupine唤醒词", check_porcupine),
        ("语音识别", check_speech_recognition),
        ("语音模块", check_voice_modules),
        ("语音系统初始化", test_voice_initialization)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
            
            if not result:
                print(f"\n⚠️  {check_name}检查失败，可能影响语音功能")
                
        except Exception as e:
            print(f"\n❌ {check_name}检查出错: {e}")
            results.append((check_name, False))
    
    # 显示诊断结果
    print("\n" + "=" * 50)
    print("📊 诊断结果总结")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for check_name, result in results:
        status = "✅ 正常" if result else "❌ 异常"
        print(f"{check_name:20} {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 项检查通过")
    
    # 给出建议
    print("\n💡 问题排查建议:")
    
    if passed == total:
        print("   🎉 所有检查都通过了！语音功能应该可以正常工作")
        print("   如果仍有问题，可能是配置或权限问题")
    else:
        print("   📝 根据失败的检查项目:")
        
        for check_name, result in results:
            if not result:
                if "音频系统" in check_name:
                    print("   • 运行: sudo apt-get install alsa-utils")
                elif "麦克风" in check_name:
                    print("   • 检查麦克风连接和权限")
                    print("   • 运行: pip3 install pyaudio")
                elif "Porcupine" in check_name:
                    print("   • 检查PICOVOICE_ACCESS_KEY是否正确")
                    print("   • 运行: pip3 install pvporcupine")
                elif "语音识别" in check_name:
                    print("   • 运行: pip3 install SpeechRecognition")
                elif "语音模块" in check_name:
                    print("   • 检查src/目录下的语音模块文件")
                elif "初始化" in check_name:
                    print("   • 检查模块依赖和配置文件")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)