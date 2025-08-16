#!/usr/bin/env python3
"""
测试唤醒词检测 + 语音回复
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

class TTSManager:
    """语音合成管理器"""
    
    def __init__(self):
        self.tts_available = False
        self.tts_engine = None
        self._initialize_tts()
    
    def _initialize_tts(self):
        """初始化语音合成"""
        print("🔊 初始化语音合成...")
        
        # 尝试使用edge-tts (推荐)
        try:
            import edge_tts
            import asyncio
            import pygame
            self.tts_type = "edge_tts"
            self.tts_available = True
            print("✅ 使用 edge-tts 语音合成")
            return
        except ImportError:
            print("⚠️  edge-tts 不可用")
        
        # 尝试使用pyttsx3
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            
            # 设置中文语音
            voices = self.tts_engine.getProperty('voices')
            for voice in voices:
                if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            
            # 设置语速和音量
            self.tts_engine.setProperty('rate', 150)
            self.tts_engine.setProperty('volume', 0.8)
            
            self.tts_type = "pyttsx3"
            self.tts_available = True
            print("✅ 使用 pyttsx3 语音合成")
            return
        except ImportError:
            print("⚠️  pyttsx3 不可用")
        
        # 尝试使用espeak (Linux系统)
        try:
            import subprocess
            result = subprocess.run(['espeak', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                self.tts_type = "espeak"
                self.tts_available = True
                print("✅ 使用 espeak 语音合成")
                return
        except:
            print("⚠️  espeak 不可用")
        
        print("❌ 没有可用的语音合成引擎")
        print("💡 建议安装: pip install edge-tts 或 pip install pyttsx3")
    
    def speak(self, text):
        """语音播放文本"""
        if not self.tts_available:
            print(f"🔇 语音合成不可用，文字回应: {text}")
            return
        
        try:
            if self.tts_type == "edge_tts":
                self._speak_edge_tts(text)
            elif self.tts_type == "pyttsx3":
                self._speak_pyttsx3(text)
            elif self.tts_type == "espeak":
                self._speak_espeak(text)
        except Exception as e:
            print(f"❌ 语音合成错误: {e}")
            print(f"🔇 文字回应: {text}")
    
    def _speak_edge_tts(self, text):
        """使用edge-tts语音合成"""
        import edge_tts
        import asyncio
        import pygame
        import tempfile
        import os
        
        async def generate_speech():
            # 使用中文语音
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
            
            # 生成临时音频文件
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            await communicate.save(tmp_path)
            return tmp_path
        
        # 生成语音文件
        audio_file = asyncio.run(generate_speech())
        
        # 播放音频
        pygame.mixer.init()
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
        
        # 等待播放完成
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        # 清理临时文件
        os.unlink(audio_file)
        pygame.mixer.quit()
    
    def _speak_pyttsx3(self, text):
        """使用pyttsx3语音合成"""
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()
    
    def _speak_espeak(self, text):
        """使用espeak语音合成"""
        import subprocess
        subprocess.run(['espeak', '-v', 'zh', text], check=True)

def test_wake_word_with_voice_response():
    """测试唤醒词检测 + 语音回复"""
    print("🎤 唤醒词检测 + 语音回复测试")
    print("=" * 50)
    
    # 初始化语音合成
    tts = TTSManager()
    
    try:
        from wake_word_detector import WakeWordDetector
        
        # 创建唤醒词检测器
        print("\n🔧 初始化唤醒词检测器...")
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
            response = responses[detection_count % len(responses)]
            print(f"🗣️  语音回复: {response}")
            
            # 在新线程中播放语音，避免阻塞检测
            def speak_in_thread():
                tts.speak(response)
            
            speech_thread = threading.Thread(target=speak_in_thread, daemon=True)
            speech_thread.start()
        
        # 开始检测
        print(f"\n🎙️  开始监听唤醒词 '快快'...")
        print("💡 检测到唤醒词后会语音回复")
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

if __name__ == "__main__":
    print("🎤 唤醒词检测 + 语音回复完整测试")
    print("=" * 60)
    
    if test_wake_word_with_voice_response():
        print("\n🎉 测试成功！唤醒词检测和语音回复都正常工作！")
        print("💡 现在可以集成到主系统中")
    else:
        print("\n❌ 测试失败，需要进一步调试")