#!/usr/bin/env python3
"""
测试真正的TTS语音合成
"""

import os
import sys
import time
import subprocess
import threading
import tempfile
import asyncio

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

def real_tts_speak(text):
    """真正的TTS语音合成"""
    try:
        import edge_tts
        
        print(f"🗣️  语音内容: {text}")
        
        async def generate_speech():
            # 使用中文女声
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
            
            # 生成MP3文件
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                mp3_path = tmp_file.name
            
            await communicate.save(mp3_path)
            return mp3_path
        
        # 生成语音文件
        print("🔄 生成语音...")
        mp3_file = asyncio.run(generate_speech())
        
        # 转换为WAV格式
        wav_file = mp3_file.replace('.mp3', '.wav')
        
        print("🔄 转换音频格式...")
        # 使用ffmpeg转换为适合的WAV格式
        convert_cmd = [
            'ffmpeg', '-i', mp3_file,
            '-ar', '44100',  # 采样率44100Hz
            '-ac', '1',      # 单声道
            '-f', 'wav',     # WAV格式
            '-y',            # 覆盖输出文件
            wav_file
        ]
        
        result = subprocess.run(convert_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ 音频转换失败: {result.stderr}")
            os.unlink(mp3_file)
            return False
        
        print("🔊 播放语音...")
        # 播放WAV文件
        play_result = subprocess.run(['/usr/bin/aplay', '-D', 'hw:0,0', wav_file], 
                                   capture_output=True, text=True, timeout=15)
        
        # 清理文件
        os.unlink(mp3_file)
        os.unlink(wav_file)
        
        if play_result.returncode == 0:
            print("✅ 语音播放成功")
            return True
        else:
            print(f"❌ 语音播放失败: {play_result.stderr}")
            return False
        
    except ImportError:
        print("❌ edge-tts未安装")
        print("💡 运行: pip install edge-tts")
        return False
    except FileNotFoundError as e:
        if 'ffmpeg' in str(e):
            print("❌ ffmpeg未安装")
            print("💡 运行: sudo apt install ffmpeg")
        else:
            print(f"❌ 命令未找到: {e}")
        return False
    except Exception as e:
        print(f"❌ TTS失败: {e}")
        return False

def test_tts_basic():
    """基础TTS测试"""
    print("🧪 基础TTS测试")
    print("=" * 30)
    
    test_phrases = [
        "你好！我听到了！",
        "主人，我在这里！",
        "测试语音合成功能"
    ]
    
    for i, phrase in enumerate(test_phrases, 1):
        print(f"\n🧪 测试 {i}: {phrase}")
        if real_tts_speak(phrase):
            print(f"✅ 测试 {i} 成功")
        else:
            print(f"❌ 测试 {i} 失败")
            return False
        
        time.sleep(1)  # 短暂间隔
    
    return True

def test_tts_voice_system():
    """测试TTS语音系统"""
    print("\n🎤 TTS语音系统测试")
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
            "您好，我是AI桌宠！",
            "快快，我来了！"
        ]
        
        detection_count = 0
        
        def on_wake_word_detected(keyword_index):
            nonlocal detection_count
            detection_count += 1
            
            print(f"\n🎉 检测 #{detection_count}: 唤醒词 '快快'")
            
            # 选择回复语句
            response = responses[(detection_count - 1) % len(responses)]
            
            # 在新线程中播放语音
            def speak_in_thread():
                if real_tts_speak(response):
                    print("✅ TTS语音回复成功")
                else:
                    print("❌ TTS语音回复失败")
            
            speech_thread = threading.Thread(target=speak_in_thread, daemon=True)
            speech_thread.start()
        
        # 开始检测
        print(f"\n🎙️  开始监听唤醒词 '快快'...")
        print("💡 检测到后会真正语音回复")
        print("💡 使用edge-tts中文语音合成")
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
    print("🗣️  真正的TTS语音合成测试")
    print("=" * 60)
    
    # 检查依赖
    print("📦 检查依赖...")
    
    try:
        import edge_tts
        print("✅ edge-tts可用")
    except ImportError:
        print("❌ edge-tts未安装")
        print("💡 运行: pip install edge-tts")
        sys.exit(1)
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
        if result.returncode == 0:
            print("✅ ffmpeg可用")
        else:
            print("❌ ffmpeg不可用")
            sys.exit(1)
    except FileNotFoundError:
        print("❌ ffmpeg未安装")
        print("💡 运行: sudo apt install ffmpeg")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    
    # 基础TTS测试
    if test_tts_basic():
        print("\n🎉 基础TTS测试成功！")
        
        # 完整语音系统测试
        print("\n" + "=" * 60)
        if test_tts_voice_system():
            print("\n🎉 完整TTS语音系统测试成功！")
            print("\n✅ 现在你可以听到真正的中文语音回复:")
            print("• 说 '快快' 唤醒")
            print("• 听到 '你好！我听到了！' 等真实语音")
            print("• 完整的中文语音交互体验")
        else:
            print("\n❌ 完整系统测试失败")
    else:
        print("\n❌ 基础TTS测试失败")
        print("💡 请检查依赖安装")