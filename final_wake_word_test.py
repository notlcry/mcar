#!/usr/bin/env python3
"""
最终的唤醒词检测测试 - 简化版本，专注于功能验证
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
wake_word_count = 0

def create_porcupine():
    """创建Porcupine实例"""
    try:
        access_key = os.getenv('PICOVOICE_ACCESS_KEY')
        wake_word_file = 'wake_words/kk_zh_raspberry-pi_v3_0_0.ppn'
        model_file = 'models/porcupine/porcupine_params_zh.pv'
        
        porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=[wake_word_file],
            model_path=model_file,
            sensitivities=[0.5]
        )
        print(f"✅ Porcupine初始化成功 (采样率: {porcupine.sample_rate}Hz)")
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
    print("⚠️ 未找到ReSpeaker设备，使用默认设备")
    return None

def detection_worker(porcupine, device_id):
    """检测工作线程"""
    global detector_running, wake_word_count
    
    target_sample_rate = porcupine.sample_rate  # 16000
    device_sample_rate = 48000
    frame_length = porcupine.frame_length  # 512
    device_frame_length = int(frame_length * device_sample_rate / target_sample_rate)  # 1536
    
    print(f"🎤 开始检测: 设备采样率{device_sample_rate}Hz -> Porcupine采样率{target_sample_rate}Hz")
    
    frame_count = 0
    
    try:
        while detector_running:
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
            
            frame_count += 1
            
            if keyword_index >= 0:
                wake_word_count += 1
                print(f"\n🎉 检测到唤醒词 '快快'！(第{wake_word_count}次)")
                print("✨ 请继续说话测试更多检测...")
            
            # 每5秒输出一次状态
            if frame_count % (target_sample_rate // frame_length * 5) == 0:
                print(f"🔄 运行正常，已处理 {frame_count} 帧，检测到 {wake_word_count} 次唤醒词")
                
    except Exception as e:
        print(f"❌ 检测线程错误: {e}")
    
    print(f"🛑 检测结束: 共处理 {frame_count} 帧，检测到 {wake_word_count} 次唤醒词")

def signal_handler(sig, frame):
    global detector_running
    print('\n🛑 停止检测...')
    detector_running = False
    time.sleep(1)
    print(f"📊 最终统计: 检测到 {wake_word_count} 次唤醒词")
    sys.exit(0)

# 主程序
signal.signal(signal.SIGINT, signal_handler)

print("🧪 最终唤醒词检测测试")
print("=" * 40)

# 初始化
porcupine = create_porcupine()
if not porcupine:
    sys.exit(1)

device_id = find_respeaker_device()

# 测试音频录制
try:
    print("🧪 测试音频录制...")
    test_audio = sd.rec(1024, samplerate=48000, channels=1, device=device_id, dtype=np.int16)
    sd.wait()
    print("✅ 音频录制测试成功")
except Exception as e:
    print(f"❌ 音频录制测试失败: {e}")
    sys.exit(1)

# 开始检测
detector_running = True
detection_thread = threading.Thread(target=detection_worker, args=(porcupine, device_id), daemon=True)
detection_thread.start()

print("✅ 唤醒词检测已启动")
print("🗣️ 请清晰地说 '快快' 来测试...")
print("⏱️ 将运行60秒，按Ctrl+C可随时停止")
print("📢 建议: 距离麦克风30cm，音量适中，发音清晰")

try:
    # 运行60秒
    for i in range(60):
        time.sleep(1)
        if not detector_running:
            break
            
    detector_running = False
    print(f"\n⏰ 测试完成!")
    print(f"📊 结果: 共检测到 {wake_word_count} 次唤醒词 '快快'")
    
    if wake_word_count > 0:
        print("🎉 唤醒词检测系统工作正常！")
    else:
        print("⚠️ 未检测到唤醒词，可能原因:")
        print("   - 环境噪音过大")
        print("   - 发音不够清晰")
        print("   - 麦克风音量过低")
        print("   - 需要更靠近麦克风")

except KeyboardInterrupt:
    pass

finally:
    detector_running = False
    if porcupine:
        porcupine.delete()