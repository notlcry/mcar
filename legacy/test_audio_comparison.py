#!/usr/bin/env python3
"""
音频兼容性测试 - 比较ReSpeaker和默认设备的音频数据
"""

import os
import sys
import time
import numpy as np
import wave

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 加载环境变量
env_file = ".ai_pet_env"
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                if line.startswith('export '):
                    line = line[7:]
                key, value = line.split('=', 1)
                value = value.strip('"\'')
                os.environ[key] = value

try:
    import sounddevice as sd
    import pvporcupine
    from scipy import signal as scipy_signal
    print("✅ 所有模块导入成功")
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    sys.exit(1)

def save_audio_sample(audio_data, filename, sample_rate=16000):
    """保存音频样本到WAV文件"""
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())

def create_porcupine(sensitivity=0.5):
    """创建Porcupine实例"""
    try:
        access_key = os.getenv('PICOVOICE_ACCESS_KEY')
        wake_word_file = 'wake_words/kk_zh_raspberry-pi_v3_0_0.ppn'
        model_file = 'models/porcupine/porcupine_params_zh.pv'
        
        porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=[wake_word_file],
            model_path=model_file,
            sensitivities=[sensitivity]
        )
        return porcupine
    except Exception as e:
        print(f"❌ Porcupine初始化失败: {e}")
        return None

def test_device_audio(device_id, device_name, duration=5):
    """测试特定设备的音频"""
    print(f"\n🎤 测试设备: {device_name}")
    
    # 创建Porcupine
    porcupine = create_porcupine(0.5)
    if not porcupine:
        return
    
    frame_length = porcupine.frame_length
    target_sample_rate = porcupine.sample_rate
    
    # 确定设备采样率
    if 'array' in device_name.lower() or 'respeaker' in device_name.lower():
        device_sample_rate = 48000
        device_frame_length = int(frame_length * device_sample_rate / target_sample_rate)
        print(f"  📊 使用设备采样率: {device_sample_rate}Hz (重采样)")
    else:
        device_sample_rate = target_sample_rate
        device_frame_length = frame_length
        print(f"  📊 使用设备采样率: {device_sample_rate}Hz (直接)")
    
    detection_count = 0
    frames_processed = 0
    audio_samples = []
    
    print(f"  🗣️ 请说 '快快' ({duration}秒测试)")
    
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration:
            # 录制音频
            audio_chunk = sd.rec(
                device_frame_length,
                samplerate=device_sample_rate,
                channels=1,
                device=device_id,
                dtype=np.int16
            )
            sd.wait()
            
            audio_data = audio_chunk.flatten()
            
            # 重采样（如果需要）
            if device_sample_rate != target_sample_rate:
                resampled_audio = scipy_signal.resample(audio_data, frame_length).astype(np.int16)
            else:
                resampled_audio = audio_data
            
            # 保存前几帧用于分析
            if frames_processed < 10:
                audio_samples.append(resampled_audio.copy())
            
            # 检测唤醒词
            keyword_index = porcupine.process(resampled_audio)
            frames_processed += 1
            
            if keyword_index >= 0:
                detection_count += 1
                print(f"    🎉 检测到唤醒词! (第{detection_count}次)")
                
                # 保存检测到的音频
                filename = f"detected_{device_name.replace(' ', '_').lower()}_{detection_count}.wav"
                save_audio_sample(resampled_audio, filename)
                print(f"    💾 音频已保存: {filename}")
            
            # 计算音频统计
            rms = np.sqrt(np.mean(resampled_audio.astype(np.float32) ** 2))
            if frames_processed % 20 == 0:
                print(f"    🔊 音频级别: RMS={rms:.0f}, 已处理{frames_processed}帧")
                
    except Exception as e:
        print(f"    ❌ 测试错误: {e}")
    
    porcupine.delete()
    
    # 分析音频样本
    if audio_samples:
        print(f"  📊 音频分析:")
        all_samples = np.concatenate(audio_samples)
        print(f"    平均值: {np.mean(all_samples):.2f}")
        print(f"    标准差: {np.std(all_samples):.2f}")
        print(f"    最小值: {np.min(all_samples)}")
        print(f"    最大值: {np.max(all_samples)}")
        print(f"    数据类型: {all_samples.dtype}")
        
        # 保存样本音频用于分析
        sample_filename = f"sample_{device_name.replace(' ', '_').lower()}.wav"
        save_audio_sample(all_samples[:target_sample_rate*2], sample_filename)  # 保存前2秒
        print(f"    💾 样本已保存: {sample_filename}")
    
    print(f"  📊 结果: 检测到 {detection_count} 次，共处理 {frames_processed} 帧")
    return detection_count

def main():
    print("🔍 音频设备兼容性测试")
    print("=" * 50)
    
    # 列出所有音频设备
    devices = sd.query_devices()
    input_devices = []
    
    print("📊 可用输入设备:")
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"  设备 {i}: {device['name']} (通道: {device['max_input_channels']})")
            input_devices.append((i, device['name']))
    
    # 找到ReSpeaker设备
    respeaker_device = None
    default_device = None
    
    for device_id, device_name in input_devices:
        name_lower = device_name.lower()
        if 'seeed' in name_lower or 'array' in name_lower or 'respeaker' in name_lower:
            respeaker_device = (device_id, device_name)
        elif 'default' in name_lower:
            default_device = (device_id, device_name)
    
    # 测试设备
    results = {}
    
    if respeaker_device:
        print(f"\n{'='*20} ReSpeaker设备测试 {'='*20}")
        results['respeaker'] = test_device_audio(respeaker_device[0], respeaker_device[1], 10)
    
    if default_device:
        print(f"\n{'='*20} 默认设备测试 {'='*20}")
        results['default'] = test_device_audio(default_device[0], default_device[1], 10)
    
    # 如果有多个设备，测试第一个非ReSpeaker设备
    other_device = None
    for device_id, device_name in input_devices:
        name_lower = device_name.lower()
        if not ('seeed' in name_lower or 'array' in name_lower or 'respeaker' in name_lower or 'default' in name_lower):
            other_device = (device_id, device_name)
            break
    
    if other_device:
        print(f"\n{'='*20} 其他设备测试 {'='*20}")
        results['other'] = test_device_audio(other_device[0], other_device[1], 10)
    
    # 总结结果
    print(f"\n{'='*20} 测试总结 {'='*20}")
    for device_type, detection_count in results.items():
        print(f"{device_type}: 检测到 {detection_count} 次唤醒词")
    
    if 'respeaker' in results and 'default' in results:
        if results['respeaker'] == 0 and results['default'] > 0:
            print("\n❌ ReSpeaker兼容性问题确认!")
            print("   ReSpeaker设备无法检测唤醒词，但其他设备可以")
            print("   建议检查:")
            print("   - ReSpeaker驱动程序")
            print("   - 音频格式转换")
            print("   - 采样率处理")
        elif results['respeaker'] > 0:
            print("\n✅ ReSpeaker工作正常")
        else:
            print("\n⚠️ 所有设备都无法检测唤醒词，可能是:")
            print("   - 唤醒词文件问题")
            print("   - 发音问题")
            print("   - 环境噪音")

if __name__ == "__main__":
    main()