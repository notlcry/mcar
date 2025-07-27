#!/usr/bin/env python3
"""
简化的唤醒词测试 - 专注于基本功能
"""

import os
import sys
import time
import pyaudio
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

def find_working_audio_device():
    """找到可用的音频设备"""
    print("🔍 查找可用的音频设备...")
    
    pa = pyaudio.PyAudio()
    
    for i in range(pa.get_device_count()):
        try:
            info = pa.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"  设备 {i}: {info['name']}")
                print(f"    采样率: {info['defaultSampleRate']} Hz")
                print(f"    通道数: {info['maxInputChannels']}")
                
                # 测试设备
                try:
                    test_stream = pa.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=int(info['defaultSampleRate']),
                        input=True,
                        input_device_index=i,
                        frames_per_buffer=1024
                    )
                    
                    # 尝试读取一些数据
                    data = test_stream.read(1024, exception_on_overflow=False)
                    test_stream.close()
                    
                    print(f"    ✅ 设备可用")
                    pa.terminate()
                    return i, int(info['defaultSampleRate'])
                    
                except Exception as e:
                    print(f"    ❌ 设备不可用: {e}")
        except:
            pass
    
    pa.terminate()
    return None, None

def test_porcupine_basic():
    """基本Porcupine测试"""
    print("\n🧪 基本Porcupine测试")
    print("=" * 30)
    
    try:
        import pvporcupine
        
        access_key = os.getenv('PICOVOICE_ACCESS_KEY')
        if not access_key:
            print("❌ PICOVOICE_ACCESS_KEY 未设置")
            return False
        
        # 查找中文模型和唤醒词
        chinese_model = 'models/porcupine/porcupine_params_zh.pv'
        keyword_path = 'wake_words/kk_zh_raspberry-pi_v3_0_0.ppn'
        
        if not os.path.exists(chinese_model):
            print(f"❌ 中文模型不存在: {chinese_model}")
            return False
            
        if not os.path.exists(keyword_path):
            print(f"❌ 唤醒词文件不存在: {keyword_path}")
            return False
        
        print(f"✅ 中文模型: {chinese_model}")
        print(f"✅ 唤醒词文件: {keyword_path}")
        
        # 创建Porcupine实例
        porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=[keyword_path],
            model_path=chinese_model
        )
        
        print(f"✅ Porcupine初始化成功")
        print(f"   采样率: {porcupine.sample_rate} Hz")
        print(f"   帧长度: {porcupine.frame_length}")
        
        porcupine.delete()
        return True
        
    except Exception as e:
        print(f"❌ Porcupine测试失败: {e}")
        return False

def test_simple_wake_word():
    """简化的唤醒词测试"""
    print("\n🎤 简化唤醒词测试")
    print("=" * 30)
    
    # 找到可用设备
    device_index, sample_rate = find_working_audio_device()
    if device_index is None:
        print("❌ 没有找到可用的音频设备")
        return False
    
    print(f"✅ 使用设备 {device_index}, 采样率: {sample_rate} Hz")
    
    try:
        import pvporcupine
        from scipy import signal
        
        access_key = os.getenv('PICOVOICE_ACCESS_KEY')
        chinese_model = 'models/porcupine/porcupine_params_zh.pv'
        keyword_path = 'wake_words/kk_zh_raspberry-pi_v3_0_0.ppn'
        
        # 创建Porcupine实例
        porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=[keyword_path],
            model_path=chinese_model
        )
        
        print(f"✅ Porcupine初始化成功")
        
        # 创建音频流
        pa = pyaudio.PyAudio()
        
        # 计算需要读取的帧数
        porcupine_rate = porcupine.sample_rate  # 16000
        mic_frame_length = int(porcupine.frame_length * sample_rate / porcupine_rate)
        
        print(f"   麦克风帧长度: {mic_frame_length}")
        print(f"   Porcupine帧长度: {porcupine.frame_length}")
        
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=mic_frame_length
        )
        
        print("\n🎙️  开始监听唤醒词 'kk'...")
        print("按 Ctrl+C 停止")
        
        try:
            while True:
                # 读取音频数据
                data = stream.read(mic_frame_length, exception_on_overflow=False)
                audio_array = np.frombuffer(data, dtype=np.int16)
                
                # 重采样
                if sample_rate != porcupine_rate:
                    num_samples = int(len(audio_array) * porcupine_rate / sample_rate)
                    resampled = signal.resample(audio_array, num_samples).astype(np.int16)
                else:
                    resampled = audio_array
                
                # 确保长度正确
                if len(resampled) >= porcupine.frame_length:
                    frame = resampled[:porcupine.frame_length]
                    
                    # 检测唤醒词
                    keyword_index = porcupine.process(frame)
                    
                    if keyword_index >= 0:
                        print(f"\n🎉 检测到唤醒词！")
                        print(f"🗣️  回应: 你好！")
                        time.sleep(1)  # 避免重复检测
                
        except KeyboardInterrupt:
            print("\n\n🛑 停止测试...")
        
        finally:
            stream.close()
            pa.terminate()
            porcupine.delete()
            print("✅ 测试结束")
            
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🎤 简化唤醒词测试")
    print("=" * 40)
    
    # 基本Porcupine测试
    if not test_porcupine_basic():
        print("❌ 基本测试失败")
        sys.exit(1)
    
    # 唤醒词测试
    if test_simple_wake_word():
        print("\n🎉 唤醒词测试完成！")
    else:
        print("\n❌ 唤醒词测试失败")
        sys.exit(1)