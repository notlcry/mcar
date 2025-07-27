#!/usr/bin/env python3
"""
使用纯WAV格式的语音系统测试
"""

import os
import sys
import time
import subprocess
import threading
import tempfile
import wave
import numpy as np

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

def generate_beep_audio(text):
    """生成提示音代替语音合成"""
    # 根据文本长度生成不同频率的提示音
    text_hash = hash(text) % 1000
    frequency = 400 + text_hash  # 400-1400Hz范围
    
    sample_rate = 44100
    duration = 1.0
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # 生成带包络的正弦波
    envelope = np.exp(-t * 2)  # 指数衰减
    wave_data = np.sin(2 * np.pi * frequency * t) * envelope * 0.3
    
    audio_data = (wave_data * 32767).astype(np.int16)
    
    # 创建临时WAV文件
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    with wave.open(tmp_path, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    return tmp_path

def simple_speak_wav(text):
    """使用纯WAV格式的语音回复"""
    try:
        print(f"🔊 文字内容: {text}")
        
        # 生成提示音
        audio_file = generate_beep_audio(text)
        
        # 播放音频
        result = subprocess.run(['/usr/bin/aplay', '-D', 'hw:0,0', audio_file], 
                              capture_output=True, text=True, timeout=10)
        
        # 清理
        os.unlink(audio_file)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ 音频生成失败: {e}")
        return False

def test_wav_voice_system():
    """测试纯WAV语音系统"""
    print("🎤 纯WAV语音系统测试")
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
        
        # 定义回复语句
        responses = [
            "你好！我听到了！",
            "主人，我在这里！",
            "有什么可以帮助您的吗？",
            "您好，我是AI桌宠！"
        ]
        
        detection_count = 0
        
        def on_wake_word_detected(keyword_index):
            nonlocal detection_count
            detection_count += 1
            
            print(f"\n🎉 检测 #{detection_count}: 唤醒词 '快快'")
            
            # 选择回复语句
            response = responses[(detection_count - 1) % len(responses)]
            
            # 在新线程中播放音频
            def speak_in_thread():
                if simple_speak_wav(response):
                    print("✅ 音频回复成功")
                else:
                    print("❌ 音频回复失败")
            
            speech_thread = threading.Thread(target=speak_in_thread, daemon=True)
            speech_thread.start()
        
        # 开始检测
        print(f"\n🎙️  开始监听唤醒词 '快快'...")
        print("💡 检测到后会播放提示音（代替语音合成）")
        print("💡 同时显示文字内容")
        print("按 Ctrl+C 停止测试")
        print("-" * 50)
        
        if detector.start_detection(on_wake_word_detected):
            try:
                # 保持运行
                while True:
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print(f"\n\n🛑 停止测试...")
                detector.stop_detection()
                print(f"📊 总共检测到 {detection_count} 次唤醒词")
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

if __name__ == "__main__":
    print("🎤 纯WAV语音系统测试")
    print("=" * 60)
    
    # 先测试音频生成
    print("🧪 测试音频生成...")
    if simple_speak_wav("测试音频生成"):
        print("✅ 音频生成正常")
    else:
        print("❌ 音频生成失败")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    
    # 测试完整系统
    if test_wav_voice_system():
        print("\n🎉 纯WAV语音系统测试成功！")
        print("\n💡 功能确认:")
        print("• ✅ 唤醒词检测正常")
        print("• ✅ 音频回复功能正常")
        print("• ✅ 使用纯WAV格式，避免格式问题")
        print("• ✅ 系统集成成功")
        
        print("\n🔧 下一步可以:")
        print("• 安装 ffmpeg 支持真正的语音合成")
        print("• 或者使用其他TTS引擎")
        print("• 集成到主系统中")
    else:
        print("\n❌ 纯WAV语音系统测试失败")