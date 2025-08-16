#!/usr/bin/env python3
"""
直接在Python中指定音频设备，绕过ALSA配置问题
"""

import os
import sys
import time
import tempfile
import wave
import numpy as np

def test_pygame_with_device():
    """测试pygame指定设备播放"""
    print("🎮 测试pygame指定设备播放")
    print("=" * 40)
    
    try:
        import pygame
        
        # 设置SDL使用ALSA并指定设备
        os.environ['SDL_AUDIODRIVER'] = 'alsa'
        os.environ['ALSA_PCM_DEVICE'] = '0'
        os.environ['ALSA_PCM_CARD'] = '0'
        
        print("🔧 设置环境变量:")
        print(f"   SDL_AUDIODRIVER = {os.environ.get('SDL_AUDIODRIVER')}")
        print(f"   ALSA_PCM_CARD = {os.environ.get('ALSA_PCM_CARD')}")
        print(f"   ALSA_PCM_DEVICE = {os.environ.get('ALSA_PCM_DEVICE')}")
        
        # 初始化pygame
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
        pygame.mixer.init()
        
        print("✅ pygame初始化成功")
        
        # 创建测试音频
        sample_rate = 44100
        duration = 2.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave_data = np.sin(2 * np.pi * frequency * t) * 0.3
        
        # 转换为立体声
        stereo_data = np.column_stack((wave_data, wave_data))
        audio_data = (stereo_data * 32767).astype(np.int16)
        
        # 创建临时文件
        test_file = os.path.expanduser("~/pygame_test.wav")
        
        with wave.open(test_file, 'w') as wav_file:
            wav_file.setnchannels(2)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        print("🎵 播放测试音频...")
        
        # 播放音频
        pygame.mixer.music.load(test_file)
        pygame.mixer.music.play()
        
        # 等待播放完成
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        pygame.mixer.quit()
        os.unlink(test_file)
        
        print("✅ pygame播放成功")
        return True
        
    except Exception as e:
        print(f"❌ pygame播放失败: {e}")
        return False

def test_pyaudio_with_device():
    """测试PyAudio指定设备播放"""
    print("\n🎤 测试PyAudio指定设备播放")
    print("=" * 40)
    
    try:
        import pyaudio
        
        # 查找Card 0的输出设备
        pa = pyaudio.PyAudio()
        
        target_device = None
        for i in range(pa.get_device_count()):
            try:
                info = pa.get_device_info_by_index(i)
                if (info['maxOutputChannels'] > 0 and 
                    'bcm2835' in info['name'].lower() and
                    info['hostApi'] == 0):  # ALSA host API
                    target_device = i
                    print(f"✅ 找到目标设备 {i}: {info['name']}")
                    print(f"   采样率: {info['defaultSampleRate']}")
                    print(f"   输出通道: {info['maxOutputChannels']}")
                    break
            except:
                continue
        
        if target_device is None:
            print("❌ 未找到合适的输出设备")
            pa.terminate()
            return False
        
        # 生成测试音频
        sample_rate = int(pa.get_device_info_by_index(target_device)['defaultSampleRate'])
        duration = 2.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave_data = np.sin(2 * np.pi * frequency * t) * 0.3
        audio_data = (wave_data * 32767).astype(np.int16)
        
        print(f"🎵 使用设备 {target_device} 播放测试音频...")
        
        # 创建音频流
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            output=True,
            output_device_index=target_device,
            frames_per_buffer=1024
        )
        
        # 播放音频
        chunk_size = 1024
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            if len(chunk) < chunk_size:
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)), 'constant')
            stream.write(chunk.tobytes())
        
        stream.close()
        pa.terminate()
        
        print("✅ PyAudio播放成功")
        return True
        
    except Exception as e:
        print(f"❌ PyAudio播放失败: {e}")
        return False

def test_subprocess_direct():
    """测试subprocess直接调用aplay"""
    print("\n🔧 测试subprocess直接调用aplay")
    print("=" * 40)
    
    try:
        import subprocess
        
        # 创建测试文件
        test_file = os.path.expanduser("~/subprocess_test.wav")
        
        sample_rate = 44100
        duration = 2.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave_data = np.sin(2 * np.pi * frequency * t) * 0.3
        audio_data = (wave_data * 32767).astype(np.int16)
        
        with wave.open(test_file, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        print("🎵 使用 aplay -D hw:0,0 播放...")
        
        # 直接调用aplay指定设备
        result = subprocess.run(['aplay', '-D', 'hw:0,0', test_file], 
                              capture_output=True, text=True, timeout=5)
        
        os.unlink(test_file)
        
        if result.returncode == 0:
            print("✅ subprocess播放成功")
            return True
        else:
            print(f"❌ subprocess播放失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ subprocess测试失败: {e}")
        return False

def create_python_audio_wrapper():
    """创建Python音频播放包装器"""
    print("\n📝 创建Python音频播放包装器")
    print("=" * 40)
    
    wrapper_code = '''#!/usr/bin/env python3
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
            result = subprocess.run(['aplay', '-D', self.device, wav_file], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
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
        except:
            return False
    
    def speak_text(self, text):
        """语音合成播放文本"""
        try:
            # 使用edge-tts生成语音
            import edge_tts
            import asyncio
            
            async def generate_speech():
                communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
                
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                
                await communicate.save(tmp_path)
                return tmp_path
            
            # 生成语音文件
            audio_file = asyncio.run(generate_speech())
            
            # 转换为WAV格式（如果需要）
            wav_file = audio_file.replace('.mp3', '.wav')
            
            # 使用ffmpeg转换（如果可用）
            try:
                subprocess.run(['ffmpeg', '-i', audio_file, '-y', wav_file], 
                             capture_output=True, check=True)
                success = self.play_wav_file(wav_file)
                os.unlink(wav_file)
            except:
                # 直接播放MP3（如果aplay支持）
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
'''
    
    try:
        with open('audio_player.py', 'w') as f:
            f.write(wrapper_code)
        print("✅ 创建了 audio_player.py")
        print("💡 使用方法:")
        print("   from audio_player import speak")
        print("   speak('你好，我是AI桌宠')")
        return True
    except Exception as e:
        print(f"❌ 创建包装器失败: {e}")
        return False

if __name__ == "__main__":
    print("🔊 Python音频直接设备测试")
    print("=" * 50)
    
    results = []
    
    # 测试不同的播放方法
    results.append(("subprocess", test_subprocess_direct()))
    results.append(("PyAudio", test_pyaudio_with_device()))
    results.append(("pygame", test_pygame_with_device()))
    
    print("\n" + "=" * 50)
    print("📊 测试结果:")
    
    success_count = 0
    for name, success in results:
        if success:
            print(f"✅ {name}: 成功")
            success_count += 1
        else:
            print(f"❌ {name}: 失败")
    
    print(f"\n📈 成功率: {success_count}/{len(results)}")
    
    if success_count > 0:
        print("\n🎉 至少有一种方法可以播放音频！")
        
        # 创建包装器
        if create_python_audio_wrapper():
            print("\n💡 现在可以使用包装器进行语音合成:")
            print("   python3 audio_player.py  # 测试")
            print("   from audio_player import speak; speak('测试')")
    else:
        print("\n❌ 所有Python播放方法都失败")
        print("💡 但 aplay -D hw:0,0 是可以工作的")