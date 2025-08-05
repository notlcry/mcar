#!/usr/bin/env python3
"""
音频调试工具 - 检查音频输入级别和唤醒词检测灵敏度
"""

import os
import sys
import time
import signal
import threading
import numpy as np

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

# 全局变量
detector_running = False
audio_levels = []

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
        print(f"✅ Porcupine初始化成功 (灵敏度: {sensitivity})")
        return porcupine
    except Exception as e:
        print(f"❌ Porcupine初始化失败: {e}")
        return None

def find_respeaker_device():
    """查找ReSpeaker设备"""
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            name = device['name'].lower()
            if 'seeed' in name or 'array' in name:
                print(f"✅ 找到ReSpeaker设备: {device['name']} (ID: {i})")
                return i
    return None

def audio_level_monitor(device_id, duration=10):
    """监控音频输入级别"""
    global detector_running, audio_levels
    
    print(f"🎤 开始监控音频级别 ({duration}秒)...")
    print("📢 请在麦克风附近说话，观察音频级别")
    
    device_sample_rate = 48000
    chunk_size = 1024
    
    detector_running = True
    audio_levels = []
    
    start_time = time.time()
    
    try:
        while detector_running and (time.time() - start_time) < duration:
            # 录制音频块
            audio_chunk = sd.rec(
                chunk_size,
                samplerate=device_sample_rate,
                channels=1,
                device=device_id,
                dtype=np.int16
            )
            sd.wait()
            
            # 计算音频级别
            audio_data = audio_chunk.flatten()
            rms_level = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
            max_level = np.max(np.abs(audio_data))
            
            audio_levels.append((rms_level, max_level))
            
            # 实时显示音频级别
            level_bar = "█" * int(rms_level / 1000) + "░" * (20 - int(rms_level / 1000))
            print(f"\r🔊 RMS: {rms_level:6.0f} | MAX: {max_level:5d} | [{level_bar}]", end="", flush=True)
            
    except KeyboardInterrupt:
        pass
    
    detector_running = False
    print(f"\n📊 音频级别监控完成")
    
    if audio_levels:
        rms_levels = [level[0] for level in audio_levels]
        max_levels = [level[1] for level in audio_levels]
        
        avg_rms = np.mean(rms_levels)
        avg_max = np.mean(max_levels)
        peak_rms = np.max(rms_levels)
        peak_max = np.max(max_levels)
        
        print(f"📈 音频统计:")
        print(f"   平均RMS级别: {avg_rms:.0f}")
        print(f"   平均最大值: {avg_max:.0f}")
        print(f"   峰值RMS: {peak_rms:.0f}")
        print(f"   峰值最大值: {peak_max:.0f}")
        
        if peak_rms < 500:
            print("⚠️ 音频级别过低，建议:")
            print("   - 增大说话音量")
            print("   - 靠近麦克风")
            print("   - 检查麦克风增益设置")
        elif peak_rms > 10000:
            print("⚠️ 音频级别过高，可能会导致失真")
        else:
            print("✅ 音频级别正常")

def sensitivity_test(device_id):
    """测试不同灵敏度设置"""
    print("\n🧪 测试不同灵敏度设置...")
    
    sensitivities = [0.1, 0.3, 0.5, 0.7, 0.9]
    device_sample_rate = 48000
    
    for sensitivity in sensitivities:
        print(f"\n🔧 测试灵敏度: {sensitivity}")
        
        # 创建Porcupine实例
        porcupine = create_porcupine(sensitivity)
        if not porcupine:
            continue
        
        frame_length = porcupine.frame_length
        device_frame_length = int(frame_length * device_sample_rate / 16000)
        
        print(f"🗣️ 请说 '快快' (10秒测试)")
        
        detection_count = 0
        test_frames = 0
        start_time = time.time()
        
        try:
            while time.time() - start_time < 10:
                # 录制音频
                audio_chunk = sd.rec(
                    device_frame_length,
                    samplerate=device_sample_rate,
                    channels=1,
                    device=device_id,
                    dtype=np.int16
                )
                sd.wait()
                
                # 重采样
                audio_data = audio_chunk.flatten()
                resampled_audio = scipy_signal.resample(audio_data, frame_length).astype(np.int16)
                
                # 检测唤醒词
                keyword_index = porcupine.process(resampled_audio)
                test_frames += 1
                
                if keyword_index >= 0:
                    detection_count += 1
                    print(f"🎉 检测到唤醒词! (第{detection_count}次)")
                    
        except KeyboardInterrupt:
            print("⏹️ 测试中断")
        
        porcupine.delete()
        print(f"📊 灵敏度 {sensitivity}: 检测到 {detection_count} 次 (共{test_frames}帧)")

def signal_handler(sig, frame):
    global detector_running
    detector_running = False
    print('\n🛑 停止测试...')
    sys.exit(0)

# 主程序
signal.signal(signal.SIGINT, signal_handler)

print("🔧 音频调试和灵敏度测试工具")
print("=" * 50)

# 查找设备
device_id = find_respeaker_device()
if device_id is None:
    print("❌ 未找到ReSpeaker设备")
    sys.exit(1)

# 测试音频录制
try:
    print("🧪 测试音频录制...")
    test_audio = sd.rec(1024, samplerate=48000, channels=1, device=device_id, dtype=np.int16)
    sd.wait()
    print("✅ 音频录制测试成功")
except Exception as e:
    print(f"❌ 音频录制测试失败: {e}")
    sys.exit(1)

print("\n" + "="*50)
print("第一步: 音频级别监控")
print("="*50)

# 1. 音频级别监控
audio_level_monitor(device_id, 15)

print("\n" + "="*50)
print("第二步: 灵敏度测试")
print("="*50)

# 2. 灵敏度测试
try:
    sensitivity_test(device_id)
except KeyboardInterrupt:
    pass

print("\n📊 测试完成!")
print("💡 建议:")
print("   - 如果音频级别过低，增大音量或靠近麦克风")
print("   - 如果低灵敏度都有误检，降低环境噪音")
print("   - 如果高灵敏度都检测不到，检查发音是否标准")
print("   - 推荐灵敏度范围: 0.3-0.7")