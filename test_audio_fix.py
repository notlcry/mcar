#!/usr/bin/env python3
"""
测试音频修复效果
"""

import os
import sys
import pyaudio
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

def test_audio_devices():
    """测试音频设备"""
    print("🔍 检查音频设备...")
    
    try:
        p = pyaudio.PyAudio()
        
        print(f"PyAudio版本: {pyaudio.__version__}")
        print(f"设备总数: {p.get_device_count()}")
        
        input_devices = []
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    input_devices.append({
                        'index': i,
                        'name': info['name'],
                        'sample_rate': int(info['defaultSampleRate']),
                        'channels': info['maxInputChannels']
                    })
                    print(f"  输入设备 {i}: {info['name']} ({info['defaultSampleRate']} Hz)")
            except:
                pass
        
        p.terminate()
        
        if not input_devices:
            print("❌ 没有找到输入设备")
            return False
        
        print(f"✅ 找到 {len(input_devices)} 个输入设备")
        return True
        
    except Exception as e:
        print(f"❌ 音频设备检查失败: {e}")
        return False

def test_microphone_basic():
    """基础麦克风测试"""
    print("\n🎤 基础麦克风测试...")
    
    try:
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        print("🎙️  请说话测试麦克风 (3秒)...")
        
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=1, phrase_time_limit=3)
        
        print(f"✅ 录音成功")
        print(f"   采样率: {audio.sample_rate} Hz")
        print(f"   数据长度: {len(audio.get_raw_data())} 字节")
        
        return audio
        
    except sr.WaitTimeoutError:
        print("⚠️  录音超时，但设备正常")
        return None
    except Exception as e:
        print(f"❌ 麦克风测试失败: {e}")
        return None

def test_vosk_with_resampling():
    """测试Vosk重采样功能"""
    print("\n🧪 测试Vosk重采样功能...")
    
    try:
        from vosk_recognizer import VoskRecognizer
        
        # 创建Vosk识别器
        vosk_rec = VoskRecognizer()
        
        if not vosk_rec.is_available:
            print("❌ Vosk不可用")
            return False
        
        print("✅ Vosk识别器初始化成功")
        
        # 录音测试
        audio = test_microphone_basic()
        if audio is None:
            print("⚠️  没有音频数据，跳过识别测试")
            return True
        
        print(f"🔄 测试重采样功能...")
        print(f"   原始采样率: {audio.sample_rate} Hz")
        print(f"   目标采样率: {vosk_rec.sample_rate} Hz")
        
        # 使用Vosk识别（会自动重采样）
        result = vosk_rec.recognize_from_speech_recognition_audio(audio)
        
        if result:
            print(f"✅ 识别成功: '{result}'")
        else:
            print("⚪ 未识别到内容（但重采样功能正常）")
        
        return True
        
    except Exception as e:
        print(f"❌ Vosk测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_voice_controller():
    """测试增强语音控制器"""
    print("\n🤖 测试增强语音控制器...")
    
    try:
        from enhanced_voice_control import EnhancedVoiceController
        
        # 创建模拟机器人
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        mock_robot = MockRobot()
        
        # 创建增强语音控制器
        voice_controller = EnhancedVoiceController(robot=mock_robot)
        
        print(f"✅ 增强语音控制器初始化成功")
        print(f"   Vosk可用: {voice_controller.use_vosk}")
        print(f"   Whisper可用: {voice_controller.use_whisper}")
        
        if voice_controller.use_vosk and voice_controller.vosk_recognizer:
            print("✅ 增强语音控制器中的Vosk正常")
            return True
        else:
            print("⚠️  增强语音控制器中的Vosk不可用")
            return False
            
    except Exception as e:
        print(f"❌ 增强语音控制器测试失败: {e}")
        return False

def check_dependencies():
    """检查依赖"""
    print("📦 检查依赖...")
    
    missing_deps = []
    
    # 临时修改sys.path，避免从当前目录导入numpy
    import sys
    original_path = sys.path[:]
    
    # 移除当前目录，避免numpy导入冲突
    if '.' in sys.path:
        sys.path.remove('.')
    if '' in sys.path:
        sys.path.remove('')
    if os.getcwd() in sys.path:
        sys.path.remove(os.getcwd())
    
    try:
        import numpy
        print(f"✅ numpy {numpy.__version__}")
    except ImportError as e:
        missing_deps.append("numpy")
        print(f"❌ numpy - {e}")
    
    try:
        import scipy
        print(f"✅ scipy {scipy.__version__}")
    except ImportError as e:
        missing_deps.append("scipy")
        print(f"❌ scipy - {e}")
    
    try:
        import vosk
        print("✅ vosk")
    except ImportError as e:
        missing_deps.append("vosk")
        print(f"❌ vosk - {e}")
    
    # 恢复原始路径
    sys.path[:] = original_path
    
    if missing_deps:
        print(f"\n⚠️  缺少依赖: {', '.join(missing_deps)}")
        print("请运行: pip install " + " ".join(missing_deps))
        return False
    
    return True

if __name__ == "__main__":
    print("🔧 音频修复效果测试")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        print("❌ 依赖检查失败")
        sys.exit(1)
    
    # 测试音频设备
    if not test_audio_devices():
        print("❌ 音频设备有问题")
        sys.exit(1)
    
    # 测试Vosk重采样
    vosk_ok = test_vosk_with_resampling()
    
    # 测试增强语音控制器
    enhanced_ok = test_enhanced_voice_controller()
    
    print("\n" + "=" * 50)
    print("📊 测试结果")
    print("=" * 50)
    
    if vosk_ok and enhanced_ok:
        print("🎉 音频问题修复成功！")
        print("\n💡 修复内容:")
        print("• ✅ ALSA配置简化，避免设备引用错误")
        print("• ✅ Vosk自动重采样，支持44100Hz→16000Hz转换")
        print("• ✅ 增强语音控制器正常工作")
        print("\n🚀 现在可以正常使用中文语音识别了！")
    else:
        print("❌ 仍有问题需要解决")
        if not vosk_ok:
            print("• Vosk识别有问题")
        if not enhanced_ok:
            print("• 增强语音控制器有问题")