#!/usr/bin/env python3
"""
修复版唤醒词检测 - 添加DC偏移校正和音频预处理
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

def create_porcupine(sensitivity=0.7):
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

def preprocess_audio(audio_data, remove_dc=True, normalize=True, apply_filter=True):
    """音频预处理"""
    processed = audio_data.astype(np.float32)
    
    # 1. 移除DC偏移
    if remove_dc:
        dc_offset = np.mean(processed)
        processed = processed - dc_offset
        if abs(dc_offset) > 1000:
            print(f"🔧 移除DC偏移: {dc_offset:.0f}")
    
    # 2. 高通滤波器 - 移除低频噪音
    if apply_filter:
        # 设计高通滤波器 (截止频率80Hz)
        nyquist = 16000 / 2
        cutoff = 80 / nyquist
        b, a = scipy_signal.butter(2, cutoff, btype='high')
        processed = scipy_signal.filtfilt(b, a, processed)
    
    # 3. 软限幅 - 防止削波
    max_val = np.max(np.abs(processed))
    if max_val > 30000:
        scale_factor = 30000 / max_val
        processed = processed * scale_factor
        print(f"🔧 音频限幅: 缩放因子 {scale_factor:.3f}")
    
    # 4. 归一化（可选）
    if normalize:
        rms = np.sqrt(np.mean(processed ** 2))
        if rms > 0:
            target_rms = 8000  # 目标RMS电平
            processed = processed * (target_rms / rms)
    
    return processed.astype(np.int16)

def detection_worker(porcupine, device_id):
    """检测工作线程"""
    global detector_running, wake_word_count
    
    target_sample_rate = porcupine.sample_rate  # 16000
    device_sample_rate = 48000
    frame_length = porcupine.frame_length  # 512
    device_frame_length = int(frame_length * device_sample_rate / target_sample_rate)  # 1536
    
    print(f"🎤 开始检测: 设备采样率{device_sample_rate}Hz -> Porcupine采样率{target_sample_rate}Hz")
    print("🔧 启用音频预处理: DC偏移校正 + 高通滤波 + 归一化")
    
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
            
            # 音频预处理
            processed_audio = preprocess_audio(resampled_audio)
            
            # 检测唤醒词
            keyword_index = porcupine.process(processed_audio)
            
            frame_count += 1
            
            if keyword_index >= 0:
                wake_word_count += 1
                print(f"\n🎉 检测到唤醒词 '快快'！(第{wake_word_count}次)")
                print("✨ 请继续说话测试更多检测...")
            
            # 每5秒输出一次状态
            if frame_count % (target_sample_rate // frame_length * 5) == 0:
                rms_original = np.sqrt(np.mean(resampled_audio.astype(np.float32) ** 2))
                rms_processed = np.sqrt(np.mean(processed_audio.astype(np.float32) ** 2))
                print(f"🔄 帧{frame_count}: 原始RMS={rms_original:.0f}, 处理后RMS={rms_processed:.0f}, 检测到{wake_word_count}次")
                
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

print("🔧 修复版唤醒词检测测试")
print("=" * 50)
print("🆕 新特性:")
print("   - DC偏移自动校正")
print("   - 高通滤波去除低频噪音")
print("   - 音频归一化")
print("   - 软限幅防削波")
print("   - 提高灵敏度到0.7")

# 初始化
porcupine = create_porcupine(0.7)  # 提高灵敏度
if not porcupine:
    sys.exit(1)

device_id = find_respeaker_device()
if device_id is None:
    print("❌ 未找到ReSpeaker设备")
    sys.exit(1)

# 测试音频录制
try:
    print("🧪 测试音频录制...")
    test_audio = sd.rec(1024, samplerate=48000, channels=1, device=device_id, dtype=np.int16)
    sd.wait()
    
    # 测试预处理
    processed_test = preprocess_audio(test_audio.flatten())
    print(f"✅ 音频录制和预处理测试成功")
    print(f"   原始音频: 平均值={np.mean(test_audio):.1f}, RMS={np.sqrt(np.mean(test_audio.astype(np.float32)**2)):.0f}")
    print(f"   处理后: 平均值={np.mean(processed_test):.1f}, RMS={np.sqrt(np.mean(processed_test.astype(np.float32)**2)):.0f}")
    
except Exception as e:
    print(f"❌ 音频录制测试失败: {e}")
    sys.exit(1)

# 开始检测
detector_running = True
detection_thread = threading.Thread(target=detection_worker, args=(porcupine, device_id), daemon=True)
detection_thread.start()

print("✅ 唤醒词检测已启动")
print("🗣️ 请清晰地说 '快快' 来测试...")
print("⏱️ 将运行45秒，按Ctrl+C可随时停止")
print("📢 建议: 距离麦克风30cm，音量适中，发音清晰")
print("💡 新版本应该能更好地处理ReSpeaker的音频")

try:
    # 运行45秒
    for i in range(45):
        time.sleep(1)
        if not detector_running:
            break
            
    detector_running = False
    print(f"\n⏰ 测试完成!")
    print(f"📊 结果: 共检测到 {wake_word_count} 次唤醒词 '快快'")
    
    if wake_word_count > 0:
        print("🎉 修复成功！唤醒词检测系统现在工作正常！")
        print("💡 成功的关键:")
        print("   - DC偏移校正解决了ReSpeaker的负偏移问题")
        print("   - 高通滤波去除了低频干扰")
        print("   - 音频归一化改善了信号质量")
    else:
        print("⚠️ 仍未检测到唤醒词，可能需要:")
        print("   - 进一步调整预处理参数")
        print("   - 检查唤醒词文件是否正确")
        print("   - 尝试不同的发音方式")

except KeyboardInterrupt:
    pass

finally:
    detector_running = False
    if porcupine:
        porcupine.delete()