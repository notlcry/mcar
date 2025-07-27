#!/usr/bin/env python3
"""
测试不同灵敏度的唤醒词检测
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

def test_sensitivity(sensitivity_value):
    """测试特定灵敏度值"""
    print(f"\n🧪 测试灵敏度: {sensitivity_value}")
    print("=" * 40)
    
    try:
        import pvporcupine
        from scipy import signal
        
        access_key = os.getenv('PICOVOICE_ACCESS_KEY')
        chinese_model = 'models/porcupine/porcupine_params_zh.pv'
        keyword_path = 'wake_words/kk_zh_raspberry-pi_v3_0_0.ppn'
        
        # 创建Porcupine实例（使用指定灵敏度）
        porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=[keyword_path],
            model_path=chinese_model,
            sensitivities=[sensitivity_value]
        )
        
        print(f"✅ Porcupine初始化成功 (灵敏度: {sensitivity_value})")
        
        # 找到音频设备
        pa = pyaudio.PyAudio()
        device_index = None
        sample_rate = None
        
        for i in range(pa.get_device_count()):
            try:
                info = pa.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0 and 'default' in info['name'].lower():
                    device_index = i
                    sample_rate = int(info['defaultSampleRate'])
                    break
            except:
                continue
        
        if device_index is None:
            print("❌ 未找到音频设备")
            return False
        
        # 创建音频流
        porcupine_rate = porcupine.sample_rate
        mic_frame_length = int(porcupine.frame_length * sample_rate / porcupine_rate)
        
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=mic_frame_length
        )
        
        print(f"🎙️  请说 'kk' 或 '可可' (测试10秒)")
        
        start_time = time.time()
        detections = 0
        
        while time.time() - start_time < 10:  # 测试10秒
            try:
                # 读取音频数据
                data = stream.read(mic_frame_length, exception_on_overflow=False)
                audio_array = np.frombuffer(data, dtype=np.int16)
                
                # 重采样
                if sample_rate != porcupine_rate:
                    num_samples = int(len(audio_array) * porcupine_rate / sample_rate)
                    resampled = signal.resample(audio_array, num_samples).astype(np.int16)
                else:
                    resampled = audio_array
                
                # 检测唤醒词
                if len(resampled) >= porcupine.frame_length:
                    frame = resampled[:porcupine.frame_length]
                    keyword_index = porcupine.process(frame)
                    
                    if keyword_index >= 0:
                        detections += 1
                        print(f"  🎉 检测 #{detections} (灵敏度: {sensitivity_value})")
                        time.sleep(0.5)  # 避免重复检测
                        
            except Exception as e:
                print(f"  ❌ 错误: {e}")
                break
        
        stream.close()
        pa.terminate()
        porcupine.delete()
        
        print(f"  📊 结果: {detections} 次检测")
        return detections > 0
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    print("🎤 唤醒词灵敏度测试")
    print("=" * 50)
    
    # 测试不同的灵敏度值
    sensitivities = [0.3, 0.5, 0.7, 0.9]
    
    print("💡 说明:")
    print("• 灵敏度越高(接近1.0)，越容易触发，但误报率也越高")
    print("• 灵敏度越低(接近0.0)，越难触发，但准确率更高")
    print("• 默认值是0.5")
    
    results = {}
    
    for sensitivity in sensitivities:
        success = test_sensitivity(sensitivity)
        results[sensitivity] = success
        
        if success:
            print(f"✅ 灵敏度 {sensitivity}: 检测成功")
        else:
            print(f"❌ 灵敏度 {sensitivity}: 未检测到")
        
        time.sleep(1)  # 短暂休息
    
    print("\n" + "=" * 50)
    print("📊 测试结果总结:")
    
    working_sensitivities = [s for s, success in results.items() if success]
    
    if working_sensitivities:
        print("✅ 可用的灵敏度值:")
        for s in working_sensitivities:
            print(f"   • {s}")
        
        recommended = working_sensitivities[len(working_sensitivities)//2]  # 选择中间值
        print(f"\n💡 推荐灵敏度: {recommended}")
        
        # 创建配置建议
        print(f"\n🔧 配置建议:")
        print(f"在唤醒词检测器中使用: sensitivities=[{recommended}]")
        
    else:
        print("❌ 所有灵敏度值都无法检测到唤醒词")
        print("💡 可能的原因:")
        print("• 发音不准确 - 尝试说 '可可' 而不是 'kk'")
        print("• 麦克风音量太低")
        print("• 环境噪音太大")
        print("• 唤醒词文件与你的发音不匹配")

if __name__ == "__main__":
    main()