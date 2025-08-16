#!/usr/bin/env python3
"""
音频播放包装器 - 绕过ALSA配置问题
"""

import os
import subprocess
import tempfile
import wave

class AudioPlayer:
    """音频播放器 - 使用可靠的播放方法"""
    
    def __init__(self):
        self.device = "hw:0,0"  # 已知可工作的设备
    
    def play_wav_file(self, wav_file):
        """播放WAV文件"""
        try:
            # 使用完整路径避免PATH问题
            result = subprocess.run(['/usr/bin/aplay', '-D', self.device, wav_file], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            print(f"播放失败: {e}")
            return False
    
    def play_audio_data(self, audio_data, sample_rate=44100, channels=1):
        """播放音频数据"""
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # 写入WAV文件
            with wave.open(tmp_path, 'w') as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data)
            
            # 播放文件
            success = self.play_wav_file(tmp_path)
            
            # 清理
            os.unlink(tmp_path)
            
            return success
        except Exception as e:
            print(f"播放音频数据失败: {e}")
            return False
    
    def speak_text(self, text):
        """语音合成播放文本"""
        try:
            # 使用edge-tts生成语音
            import edge_tts
            import asyncio
            
            async def generate_speech():
                communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
                
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                
                await communicate.save(tmp_path)
                return tmp_path
            
            # 生成语音文件
            audio_file = asyncio.run(generate_speech())
            
            # 播放文件
            success = self.play_wav_file(audio_file)
            
            # 清理
            os.unlink(audio_file)
            
            return success
            
        except ImportError:
            print("edge-tts未安装，无法进行语音合成")
            return False
        except Exception as e:
            print(f"语音合成失败: {e}")
            return False

# 全局实例
audio_player = AudioPlayer()

def play_audio(audio_data, sample_rate=44100, channels=1):
    """播放音频数据的便捷函数"""
    return audio_player.play_audio_data(audio_data, sample_rate, channels)

def speak(text):
    """语音合成的便捷函数"""
    return audio_player.speak_text(text)

if __name__ == "__main__":
    # 测试
    import numpy as np
    
    # 生成测试音频
    sample_rate = 44100
    duration = 1.0
    frequency = 440.0
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave_data = np.sin(2 * np.pi * frequency * t) * 0.3
    audio_data = (wave_data * 32767).astype(np.int16)
    
    print("测试音频播放...")
    if play_audio(audio_data.tobytes(), sample_rate, 1):
        print("✅ 音频播放成功")
    else:
        print("❌ 音频播放失败")
    
    print("\n测试语音合成...")
    if speak("你好，我是AI桌宠"):
        print("✅ 语音合成成功")
    else:
        print("❌ 语音合成失败")