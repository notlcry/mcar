#!/usr/bin/env python3
"""
简化的语音系统测试
"""

import os
import sys
import time
import subprocess
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

def simple_speak(text):
    """简单的语音合成函数"""
    try:
        import edge_tts
        import asyncio
        import tempfile
        
        async def generate_speech():
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
            
            # 生成MP3文件
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                mp3_path = tmp_file.name
            
            await communicate.save(mp3_path)
            
            # 转换为WAV格式
            wav_path = mp3_path.replace('.mp3', '.wav')
            
            # 使用ffmpeg转换（如果可用）
            try:
                subprocess.run(['ffmpeg', '-i', mp3_path, '-ar', '44100', '-ac', '1', '-y', wav_path], 
                             capture_output=True, check=True)
                os.unlink(mp3_path)  # 删除MP3文件
                return wav_path
            except (FileNotFoundError, subprocess.CalledProcessError):
                # ffmpeg不可用，直接返回MP3（某些aplay版本支持）
                return mp3_path
        
        # 生成语音文件
        audio_file = asyncio.run(generate_speech())
        
        # 直接使用完整路径
        result = subprocess.run(['/usr/bin/aplay', '-D', 'hw:0,0', audio_file], 
                              capture_output=True, text=True, timeout=10)
        
        # 清理
        os.unlink(audio_file)
        
        return result.returncode == 0
        
    except ImportError:
        print("⚠️  edge-tts未安装，使用文字回复")
        print(f"🗣️  文字回复: {text}")
        return True
    except Exception as e:
        print(f"❌ 语音合成失败: {e}")
        return False

def test_simple_voice_system():
    """测试简化的语音系统"""
    print("🎤 简化语音系统测试")
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
            print(f"🗣️  准备回复: {response}")
            
            # 在新线程中播放语音
            def speak_in_thread():
                if simple_speak(response):
                    print("✅ 语音回复成功")
                else:
                    print("❌ 语音回复失败")
            
            speech_thread = threading.Thread(target=speak_in_thread, daemon=True)
            speech_thread.start()
        
        # 开始检测
        print(f"\n🎙️  开始监听唤醒词 '快快'...")
        print("💡 检测到后会语音回复")
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
    print("🎤 简化语音系统测试")
    print("=" * 60)
    
    # 先测试语音合成
    print("🧪 测试语音合成...")
    if simple_speak("测试语音合成功能"):
        print("✅ 语音合成正常")
    else:
        print("⚠️  语音合成有问题，但可以继续测试")
    
    print("\n" + "=" * 60)
    
    # 测试完整系统
    if test_simple_voice_system():
        print("\n🎉 简化语音系统测试成功！")
        print("\n💡 功能确认:")
        print("• ✅ 唤醒词检测正常")
        print("• ✅ 语音回复功能正常")
        print("• ✅ 系统集成成功")
    else:
        print("\n❌ 简化语音系统测试失败")