#!/usr/bin/env python3
"""
USB麦克风解决方案 - 绕过ReSpeaker兼容性问题
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
    print("✅ 所有模块导入成功")
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    sys.exit(1)

# 全局变量
detector_running = False
wake_word_count = 0

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

def find_best_audio_device():
    """找到最佳音频设备（避开ReSpeaker）"""
    devices = sd.query_devices()
    
    print("📊 可用音频设备:")
    input_devices = []
    
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            name = device['name']
            print(f"  设备 {i}: {name} (通道: {device['max_input_channels']})")
            input_devices.append((i, name))
    
    # 优先级排序：USB设备 > 默认设备 > 其他 > ReSpeaker(最后)
    device_priorities = []
    
    for device_id, device_name in input_devices:
        name_lower = device_name.lower()
        
        if 'usb' in name_lower or 'microphone' in name_lower:
            priority = 1  # USB麦克风优先
            device_type = "USB麦克风"
        elif 'default' in name_lower:
            priority = 2  # 默认设备
            device_type = "默认设备"
        elif not ('seeed' in name_lower or 'array' in name_lower or 'respeaker' in name_lower):
            priority = 3  # 其他设备
            device_type = "其他设备"
        else:
            priority = 4  # ReSpeaker最后
            device_type = "ReSpeaker"
        
        device_priorities.append((priority, device_id, device_name, device_type))
    
    # 按优先级排序
    device_priorities.sort()
    
    print("\n🎯 设备优先级:")
    for priority, device_id, device_name, device_type in device_priorities:
        print(f"  {priority}. [{device_type}] {device_name} (ID: {device_id})")
    
    # 返回最高优先级设备
    if device_priorities:
        _, device_id, device_name, device_type = device_priorities[0]
        print(f"\n✅ 选择设备: [{device_type}] {device_name} (ID: {device_id})")
        return device_id, device_name, device_type
    
    return None, None, None

def test_device_compatibility(device_id, device_name, device_type):
    """测试设备兼容性"""
    print(f"\n🧪 测试设备兼容性: {device_name}")
    
    # 创建Porcupine实例进行测试
    porcupine = create_porcupine(0.5)
    if not porcupine:
        return False
    
    frame_length = porcupine.frame_length
    sample_rate = porcupine.sample_rate
    
    try:
        # 测试不同采样率
        test_rates = [16000, 44100, 48000]
        best_rate = None
        
        for test_rate in test_rates:
            try:
                print(f"  🔧 测试采样率: {test_rate}Hz")
                
                # 录制测试音频
                test_audio = sd.rec(
                    frame_length if test_rate == 16000 else int(frame_length * test_rate / 16000),
                    samplerate=test_rate,
                    channels=1,
                    device=device_id,
                    dtype=np.int16
                )
                sd.wait()
                
                # 重采样到16kHz（如果需要）
                if test_rate != 16000:
                    from scipy import signal as scipy_signal
                    resampled = scipy_signal.resample(test_audio.flatten(), frame_length).astype(np.int16)
                else:
                    resampled = test_audio.flatten()
                
                # 测试Porcupine处理
                porcupine.process(resampled)
                
                # 检查音频质量
                rms = np.sqrt(np.mean(resampled.astype(np.float32) ** 2))
                dc_offset = np.mean(resampled)
                
                print(f"    ✅ 采样率 {test_rate}Hz 成功 - RMS: {rms:.0f}, DC偏移: {dc_offset:.0f}")
                
                if best_rate is None:
                    best_rate = test_rate
                
                # 如果是16kHz且质量好，优先选择
                if test_rate == 16000 and abs(dc_offset) < 1000 and rms > 100:
                    best_rate = test_rate
                    break
                    
            except Exception as e:
                print(f"    ❌ 采样率 {test_rate}Hz 失败: {e}")
                continue
        
        porcupine.delete()
        
        if best_rate:
            print(f"  ✅ 设备兼容，推荐采样率: {best_rate}Hz")
            return best_rate
        else:
            print(f"  ❌ 设备不兼容")
            return False
            
    except Exception as e:
        print(f"  ❌ 兼容性测试失败: {e}")
        porcupine.delete()
        return False

def detection_worker(porcupine, device_id, device_name, sample_rate):
    """检测工作线程"""
    global detector_running, wake_word_count
    
    frame_length = porcupine.frame_length
    target_sample_rate = porcupine.sample_rate
    
    if sample_rate == target_sample_rate:
        device_frame_length = frame_length
        need_resample = False
        print(f"🎤 直接使用 {sample_rate}Hz 采样率，无需重采样")
    else:
        device_frame_length = int(frame_length * sample_rate / target_sample_rate)
        need_resample = True
        print(f"🎤 使用 {sample_rate}Hz 采样率，重采样到 {target_sample_rate}Hz")
    
    frame_count = 0
    
    try:
        from scipy import signal as scipy_signal
        
        while detector_running:
            # 录制音频
            audio_chunk = sd.rec(
                device_frame_length,
                samplerate=sample_rate,
                channels=1,
                device=device_id,
                dtype=np.int16
            )
            sd.wait()
            
            audio_data = audio_chunk.flatten()
            
            # 重采样（如果需要）
            if need_resample:
                processed_audio = scipy_signal.resample(audio_data, frame_length).astype(np.int16)
            else:
                processed_audio = audio_data
            
            # 检测唤醒词
            keyword_index = porcupine.process(processed_audio)
            
            frame_count += 1
            
            if keyword_index >= 0:
                wake_word_count += 1
                print(f"\n🎉 检测到唤醒词 '快快'！(第{wake_word_count}次)")
                print("✨ 请继续说话测试更多检测...")
            
            # 每5秒输出一次状态
            if frame_count % (target_sample_rate // frame_length * 5) == 0:
                rms = np.sqrt(np.mean(processed_audio.astype(np.float32) ** 2))
                print(f"🔄 帧{frame_count}: RMS={rms:.0f}, 检测到{wake_word_count}次唤醒词")
                
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

print("🎯 智能音频设备选择和唤醒词检测")
print("=" * 50)
print("💡 自动避开ReSpeaker兼容性问题")
print("🔍 优先使用USB麦克风或其他兼容设备")

# 查找最佳设备
device_id, device_name, device_type = find_best_audio_device()
if device_id is None:
    print("❌ 未找到可用的音频设备")
    sys.exit(1)

# 测试设备兼容性
best_sample_rate = test_device_compatibility(device_id, device_name, device_type)
if not best_sample_rate:
    print("❌ 选定设备不兼容")
    sys.exit(1)

# 初始化Porcupine
porcupine = create_porcupine(0.5)
if not porcupine:
    sys.exit(1)

# 开始检测
detector_running = True
detection_thread = threading.Thread(target=detection_worker, args=(porcupine, device_id, device_name, best_sample_rate), daemon=True)
detection_thread.start()

print(f"\n✅ 唤醒词检测已启动")
print(f"🎤 使用设备: [{device_type}] {device_name}")
print(f"📊 采样率: {best_sample_rate}Hz")
print("🗣️ 请清晰地说 '快快' 来测试...")
print("⏱️ 将运行60秒，按Ctrl+C可随时停止")

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
        print("🎉 成功！找到了兼容的音频设备！")
        print("💡 建议:")
        print(f"   - 使用 [{device_type}] {device_name} 作为主要麦克风")
        print(f"   - 采样率设置为 {best_sample_rate}Hz")
        print("   - 可以考虑购买专用的USB麦克风以获得更好的效果")
    else:
        print("⚠️ 仍未检测到唤醒词")
        print("💡 建议:")
        print("   - 尝试连接USB麦克风")
        print("   - 检查发音是否标准")
        print("   - 确认唤醒词文件是否正确")

except KeyboardInterrupt:
    pass

finally:
    detector_running = False
    if porcupine:
        porcupine.delete()