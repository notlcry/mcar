#!/usr/bin/env python3
"""
测试完整的语音系统：唤醒词检测 + 语音回复
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

def test_complete_voice_system():
    """测试完整的语音系统"""
    print("🎤 完整语音系统测试")
    print("=" * 50)
    
    try:
        from wake_word_detector import WakeWordDetector
        from audio_player import speak
        
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
            "您好，我是AI桌宠！",
            "快快，我来了！"
        ]
        
        detection_count = 0
        
        def on_wake_word_detected(keyword_index):
            nonlocal detection_count
            detection_count += 1
            
            print(f"\n🎉 检测 #{detection_count}: 唤醒词 '快快' (索引: {keyword_index})")
            
            # 选择回复语句
            response = responses[(detection_count - 1) % len(responses)]
            print(f"🗣️  语音回复: {response}")
            
            # 在新线程中播放语音，避免阻塞检测
            def speak_in_thread():
                try:
                    success = speak(response)
                    if success:
                        print("✅ 语音回复播放成功")
                    else:
                        print("❌ 语音回复播放失败")
                except Exception as e:
                    print(f"❌ 语音回复错误: {e}")
            
            speech_thread = threading.Thread(target=speak_in_thread, daemon=True)
            speech_thread.start()
        
        # 开始检测
        print(f"\n🎙️  开始监听唤醒词 '快快'...")
        print("💡 检测到唤醒词后会语音回复")
        print("💡 使用可靠的subprocess播放方式")
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
                return detection_count > 0
        else:
            print("❌ 启动唤醒词检测失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_audio_player_basic():
    """测试音频播放器基础功能"""
    print("🔊 测试音频播放器基础功能")
    print("=" * 40)
    
    try:
        from audio_player import speak, play_audio
        import numpy as np
        
        # 测试音频播放
        print("🎵 测试音频播放...")
        sample_rate = 44100
        duration = 1.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave_data = np.sin(2 * np.pi * frequency * t) * 0.3
        audio_data = (wave_data * 32767).astype(np.int16)
        
        if play_audio(audio_data.tobytes(), sample_rate, 1):
            print("✅ 音频播放成功")
        else:
            print("❌ 音频播放失败")
            return False
        
        # 测试语音合成
        print("\n🗣️  测试语音合成...")
        test_text = "你好，我是AI桌宠，语音系统测试成功！"
        
        if speak(test_text):
            print("✅ 语音合成成功")
            return True
        else:
            print("❌ 语音合成失败")
            return False
            
    except Exception as e:
        print(f"❌ 音频播放器测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🎤 完整语音系统集成测试")
    print("=" * 60)
    
    # 先测试音频播放器
    if test_audio_player_basic():
        print("\n🎉 音频播放器正常！")
        
        # 测试完整系统
        print("\n" + "=" * 60)
        if test_complete_voice_system():
            print("\n🎉 完整语音系统测试成功！")
            print("\n✅ 系统功能:")
            print("• 唤醒词检测: 说 '快快' 唤醒")
            print("• 语音回复: 自动语音回应")
            print("• 音频播放: 使用可靠的subprocess方式")
            
            print("\n💡 现在可以集成到主系统中:")
            print("• 修改 enhanced_voice_control.py")
            print("• 使用 audio_player.speak() 进行语音回复")
        else:
            print("\n❌ 完整系统测试失败")
    else:
        print("\n❌ 音频播放器有问题，无法进行完整测试")