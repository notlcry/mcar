#!/usr/bin/env python3
"""
测试唤醒词检测功能
"""

import os
import sys
import time
import threading

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

def test_wake_word_detection():
    """测试唤醒词检测"""
    print("🎤 唤醒词检测测试")
    print("=" * 50)
    
    try:
        from wake_word_detector import WakeWordDetector
        
        # 创建唤醒词检测器
        print("🔧 初始化唤醒词检测器...")
        detector = WakeWordDetector()
        
        if not detector.porcupine:
            print("❌ 唤醒词检测器初始化失败")
            return False
        
        print("✅ 唤醒词检测器初始化成功")
        print(f"   Porcupine采样率: {detector.porcupine.sample_rate} Hz")
        print(f"   麦克风采样率: {detector.microphone_sample_rate} Hz")
        print(f"   帧长度: {detector.porcupine.frame_length}")
        
        # 检查使用的唤醒词
        if detector.keyword_paths:
            print(f"   使用自定义唤醒词: {len(detector.keyword_paths)} 个")
            for i, path in enumerate(detector.keyword_paths):
                print(f"     {i}: {os.path.basename(path)}")
        else:
            print(f"   使用内置关键词: {detector.keywords}")
        
        # 定义唤醒回调
        def on_wake_word_detected(keyword_index):
            """唤醒词检测回调"""
            print(f"\n🎉 检测到唤醒词！索引: {keyword_index}")
            
            if detector.keyword_paths:
                keyword_file = os.path.basename(detector.keyword_paths[keyword_index])
                print(f"   唤醒词文件: {keyword_file}")
                if 'kk_zh' in keyword_file:
                    print("   唤醒词: 'kk' (中文)")
            else:
                if keyword_index < len(detector.keywords):
                    print(f"   唤醒词: '{detector.keywords[keyword_index]}'")
            
            # 回应 "你好"
            print("🗣️  回应: 你好！")
            
            # 可以在这里添加语音合成回应
            try:
                import pyttsx3
                tts = pyttsx3.init()
                tts.say("你好")
                tts.runAndWait()
            except:
                print("   (语音合成不可用，仅文字回应)")
        
        # 开始检测
        print("\n🎙️  开始唤醒词检测...")
        print("💡 请说唤醒词来测试:")
        
        if detector.keyword_paths and any('kk_zh' in path for path in detector.keyword_paths):
            print("   • 中文唤醒词: '可可' 或 'kk'")
        
        if detector.keywords:
            for keyword in detector.keywords:
                print(f"   • 英文唤醒词: '{keyword}'")
        
        print("\n按 Ctrl+C 停止测试")
        print("-" * 50)
        
        # 启动检测
        if detector.start_detection(on_wake_word_detected):
            try:
                # 保持运行
                while True:
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n\n🛑 停止测试...")
                detector.stop_detection()
                print("✅ 测试结束")
                return True
        else:
            print("❌ 启动唤醒词检测失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_wake_word_setup():
    """检查唤醒词设置"""
    print("🔍 检查唤醒词设置")
    print("=" * 30)
    
    # 检查访问密钥
    access_key = os.getenv('PICOVOICE_ACCESS_KEY')
    if not access_key:
        print("❌ PICOVOICE_ACCESS_KEY 未设置")
        return False
    elif access_key == 'your_picovoice_access_key_here':
        print("❌ PICOVOICE_ACCESS_KEY 是默认值")
        return False
    else:
        print(f"✅ 访问密钥已设置: {access_key[:20]}...")
    
    # 检查唤醒词文件
    wake_word_dirs = ['wake_words', '../wake_words']
    found_files = []
    
    for dir_path in wake_word_dirs:
        if os.path.exists(dir_path):
            ppn_files = [os.path.join(dir_path, f) for f in os.listdir(dir_path) if f.endswith('.ppn')]
            if ppn_files:
                found_files.extend(ppn_files)
                print(f"✅ 在 {dir_path} 找到 {len(ppn_files)} 个唤醒词文件:")
                for f in ppn_files:
                    print(f"   - {os.path.basename(f)}")
    
    if not found_files:
        print("⚠️  未找到自定义唤醒词文件，将使用内置关键词")
    
    # 检查中文模型
    chinese_model_paths = [
        'models/porcupine/porcupine_params_zh.pv',
        '../models/porcupine/porcupine_params_zh.pv',
        'src/wake_words/porcupine_params_zh.pv',
        'wake_words/porcupine_params_zh.pv'
    ]
    
    chinese_model = None
    for model_path in chinese_model_paths:
        if os.path.exists(model_path):
            chinese_model = model_path
            print(f"✅ 找到中文模型: {model_path}")
            break
    
    if not chinese_model and any('_zh_' in f for f in found_files):
        print("⚠️  有中文唤醒词但未找到中文模型")
        print("💡 运行: ./setup_chinese_wake_word.sh")
    
    return True

def test_audio_devices():
    """测试音频设备"""
    print("\n🔊 检查音频设备")
    print("=" * 30)
    
    try:
        import pyaudio
        
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
                    print(f"  输入设备 {i}: {info['name']}")
                    print(f"    采样率: {info['defaultSampleRate']} Hz")
                    print(f"    通道数: {info['maxInputChannels']}")
            except:
                pass
        
        p.terminate()
        
        if input_devices:
            print(f"✅ 找到 {len(input_devices)} 个输入设备")
            return True
        else:
            print("❌ 没有找到输入设备")
            return False
            
    except Exception as e:
        print(f"❌ 音频设备检查失败: {e}")
        return False

if __name__ == "__main__":
    print("🎤 唤醒词检测完整测试")
    print("=" * 60)
    
    # 检查设置
    if not check_wake_word_setup():
        print("❌ 唤醒词设置有问题")
        sys.exit(1)
    
    # 检查音频设备
    if not test_audio_devices():
        print("❌ 音频设备有问题")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    
    # 开始测试
    if test_wake_word_detection():
        print("\n🎉 唤醒词检测测试完成！")
    else:
        print("\n❌ 唤醒词检测测试失败")
        sys.exit(1)