#!/usr/bin/env python3
"""
修复音频采样率和ALSA配置问题
"""

import os
import sys
import json
import pyaudio
import speech_recognition as sr
import numpy as np
from scipy import signal

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

def find_working_microphone():
    """找到可用的麦克风设备"""
    print("🔍 扫描可用的音频设备...")
    
    p = pyaudio.PyAudio()
    working_devices = []
    
    for i in range(p.get_device_count()):
        try:
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:  # 输入设备
                print(f"设备 {i}: {info['name']}")
                print(f"  - 最大输入通道: {info['maxInputChannels']}")
                print(f"  - 默认采样率: {info['defaultSampleRate']}")
                
                # 测试设备是否可用
                try:
                    # 尝试打开设备进行录音
                    stream = p.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=int(info['defaultSampleRate']),
                        input=True,
                        input_device_index=i,
                        frames_per_buffer=1024
                    )
                    stream.close()
                    working_devices.append({
                        'index': i,
                        'name': info['name'],
                        'sample_rate': int(info['defaultSampleRate']),
                        'channels': info['maxInputChannels']
                    })
                    print(f"  ✅ 设备可用")
                except Exception as e:
                    print(f"  ❌ 设备不可用: {e}")
                
                print()
        except Exception as e:
            print(f"设备 {i}: 无法获取信息 - {e}")
    
    p.terminate()
    return working_devices

def resample_audio(audio_data, original_rate, target_rate):
    """重采样音频数据"""
    if original_rate == target_rate:
        return audio_data
    
    # 计算重采样比例
    num_samples = int(len(audio_data) * target_rate / original_rate)
    
    # 使用scipy进行重采样
    resampled = signal.resample(audio_data, num_samples)
    
    return resampled.astype(np.int16)

class FixedSampleRateRecognizer:
    """修复采样率的语音识别器"""
    
    def __init__(self, target_sample_rate=16000):
        self.target_sample_rate = target_sample_rate
        self.recognizer = sr.Recognizer()
        
        # 找到可用的麦克风
        devices = find_working_microphone()
        if not devices:
            raise Exception("没有找到可用的麦克风设备")
        
        # 选择第一个可用设备
        self.device = devices[0]
        print(f"🎤 使用设备: {self.device['name']}")
        print(f"📊 原始采样率: {self.device['sample_rate']} Hz")
        print(f"🎯 目标采样率: {self.target_sample_rate} Hz")
        
        # 创建麦克风对象
        self.microphone = sr.Microphone(device_index=self.device['index'])
        
    def listen_and_resample(self, timeout=5, phrase_time_limit=3):
        """监听并重采样音频"""
        print("🎙️  开始录音...")
        
        with self.microphone as source:
            # 调整环境噪音
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # 录音
            audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        
        # 获取原始音频数据
        raw_data = audio.get_raw_data()
        
        # 转换为numpy数组
        audio_array = np.frombuffer(raw_data, dtype=np.int16)
        
        print(f"📊 原始音频: {len(audio_array)} 样本, {self.device['sample_rate']} Hz")
        
        # 重采样到目标采样率
        if self.device['sample_rate'] != self.target_sample_rate:
            resampled_array = resample_audio(
                audio_array, 
                self.device['sample_rate'], 
                self.target_sample_rate
            )
            print(f"🔄 重采样后: {len(resampled_array)} 样本, {self.target_sample_rate} Hz")
        else:
            resampled_array = audio_array
        
        # 创建新的AudioData对象
        resampled_audio = sr.AudioData(
            resampled_array.tobytes(),
            self.target_sample_rate,
            2  # 16-bit samples
        )
        
        return resampled_audio

def test_vosk_with_resampling():
    """测试Vosk与重采样"""
    print("🧪 测试Vosk中文识别 + 采样率修复")
    print("=" * 50)
    
    try:
        from vosk_recognizer import VoskRecognizer
        
        # 创建Vosk识别器
        vosk_rec = VoskRecognizer()
        
        if not vosk_rec.is_available:
            print("❌ Vosk不可用")
            return False
        
        print("✅ Vosk识别器初始化成功")
        
        # 创建修复采样率的识别器
        fixed_recognizer = FixedSampleRateRecognizer(target_sample_rate=16000)
        
        print("\n🎙️  请说中文，按Ctrl+C停止...")
        print("💡 现在会自动处理采样率转换")
        
        while True:
            try:
                # 录音并重采样
                audio = fixed_recognizer.listen_and_resample(timeout=2, phrase_time_limit=5)
                
                print("🔄 正在识别...")
                
                # 使用Vosk识别
                result = vosk_rec.recognize_from_speech_recognition_audio(audio)
                
                if result:
                    print(f"✅ 识别结果: '{result}'")
                else:
                    print("⚪ 未识别到内容")
                
            except sr.WaitTimeoutError:
                # 超时是正常的，继续监听
                pass
            except KeyboardInterrupt:
                print("\n👋 测试结束")
                break
            except Exception as e:
                print(f"❌ 识别错误: {e}")
                import traceback
                traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_fixed_asoundrc():
    """创建修复的ALSA配置"""
    print("🔧 创建修复的ALSA配置...")
    
    # 找到可用设备
    devices = find_working_microphone()
    if not devices:
        print("❌ 没有找到可用的麦克风设备")
        return False
    
    # 选择第一个可用设备
    device = devices[0]
    device_index = device['index']
    
    # 创建简化的.asoundrc配置
    asoundrc_content = f"""# 简化的ALSA配置 - 修复采样率问题
pcm.!default {{
    type plug
    slave {{
        pcm "hw:{device_index},0"
        rate 16000
        channels 1
        format S16_LE
    }}
}}

ctl.!default {{
    type hw
    card {device_index}
}}

# 录音设备配置
pcm.mic {{
    type plug
    slave {{
        pcm "hw:{device_index},0"
        rate 16000
        channels 1
        format S16_LE
    }}
}}
"""
    
    try:
        with open('.asoundrc', 'w') as f:
            f.write(asoundrc_content)
        
        print(f"✅ 创建.asoundrc配置，使用设备 {device_index}: {device['name']}")
        print("💡 配置强制使用16kHz采样率")
        return True
        
    except Exception as e:
        print(f"❌ 创建配置失败: {e}")
        return False

if __name__ == "__main__":
    print("🔧 音频采样率和ALSA配置修复工具")
    print("=" * 60)
    
    # 安装必要的依赖
    print("📦 检查依赖...")
    try:
        import scipy
        print("✅ scipy已安装")
    except ImportError:
        print("❌ 需要安装scipy: pip install scipy")
        sys.exit(1)
    
    # 创建修复的ALSA配置
    if create_fixed_asoundrc():
        print("✅ ALSA配置已修复")
    else:
        print("❌ ALSA配置修复失败")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    
    # 测试修复后的语音识别
    if test_vosk_with_resampling():
        print("\n🎉 音频采样率问题已修复！")
        print("💡 现在Vosk应该可以正常识别中文了")
    else:
        print("\n❌ 仍有问题需要解决")