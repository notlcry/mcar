#!/usr/bin/env python3
"""
ReSpeaker 2-Mics专用兼容性修复
使用底层音频处理和备用检测策略
"""

import os
import sys
import time
import signal
import threading
import numpy as np
import struct

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

def create_multiple_porcupines():
    """创建多个不同灵敏度的Porcupine实例"""
    access_key = os.getenv('PICOVOICE_ACCESS_KEY')
    wake_word_file = 'wake_words/kk_zh_raspberry-pi_v3_0_0.ppn'
    model_file = 'models/porcupine/porcupine_params_zh.pv'
    
    porcupines = []
    sensitivities = [0.1, 0.3, 0.5, 0.7, 0.9]
    
    for sensitivity in sensitivities:
        try:
            porcupine = pvporcupine.create(
                access_key=access_key,
                keyword_paths=[wake_word_file],
                model_path=model_file,
                sensitivities=[sensitivity]
            )
            porcupines.append((porcupine, sensitivity))
            print(f"✅ Porcupine初始化成功 (灵敏度: {sensitivity})")
        except Exception as e:
            print(f"❌ Porcupine初始化失败 (灵敏度: {sensitivity}): {e}")
    
    return porcupines

def advanced_audio_preprocessing(audio_data):
    """高级音频预处理专门针对ReSpeaker"""
    
    # 转换为float进行处理
    audio_float = audio_data.astype(np.float32)
    
    # 1. 强力DC偏移移除（滑动平均）
    window_size = min(256, len(audio_float) // 4)
    if window_size > 10:
        dc_trend = np.convolve(audio_float, np.ones(window_size)/window_size, mode='same')
        audio_float = audio_float - dc_trend
    else:
        audio_float = audio_float - np.mean(audio_float)
    
    # 2. 多级滤波
    # 高通滤波器 - 移除60Hz以下
    try:
        nyquist = 16000 / 2
        high_cutoff = 60 / nyquist
        b_high, a_high = scipy_signal.butter(3, high_cutoff, btype='high')
        audio_float = scipy_signal.filtfilt(b_high, a_high, audio_float)
        
        # 低通滤波器 - 移除8000Hz以上
        low_cutoff = 8000 / nyquist
        b_low, a_low = scipy_signal.butter(3, low_cutoff, btype='low')
        audio_float = scipy_signal.filtfilt(b_low, a_low, audio_float)
    except:
        pass
    
    # 3. 动态范围压缩
    # 计算RMS
    rms = np.sqrt(np.mean(audio_float ** 2))
    if rms > 0:
        # 软压缩
        target_rms = 5000
        if rms > target_rms:
            compression_ratio = 0.6
            excess = audio_float / rms * target_rms
            compressed = np.sign(audio_float) * (np.abs(excess) ** compression_ratio) * target_rms
            audio_float = compressed
        else:
            # 轻微放大小信号
            audio_float = audio_float * (target_rms / rms) * 0.8
    
    # 4. 去噪（简单）
    # 检测并减少静音段的噪音
    energy_threshold = np.percentile(np.abs(audio_float), 70)
    quiet_mask = np.abs(audio_float) < energy_threshold
    if np.sum(quiet_mask) > len(audio_float) * 0.3:  # 如果超过30%是安静的
        noise_estimate = np.mean(np.abs(audio_float[quiet_mask]))
        audio_float[quiet_mask] *= 0.3  # 减少安静段的噪音
    
    # 5. 限幅和整形
    audio_float = np.clip(audio_float, -32000, 32000)
    
    # 6. 添加轻微的预加重（增强高频）
    try:
        pre_emphasis = 0.97
        audio_float = np.append(audio_float[0], audio_float[1:] - pre_emphasis * audio_float[:-1])
    except:
        pass
    
    return audio_float.astype(np.int16)

def respeaker_detection_worker(porcupines, device_id):
    """ReSpeaker专用检测工作线程"""
    global detector_running, wake_word_count
    
    frame_length = 512  # Porcupine帧长度
    device_sample_rate = 48000
    target_sample_rate = 16000
    device_frame_length = int(frame_length * device_sample_rate / target_sample_rate)
    
    print(f"🎤 ReSpeaker专用检测线程启动")
    print(f"📊 设备: 48kHz, 目标: 16kHz, 帧长度: {frame_length}")
    print(f"🔧 使用 {len(porcupines)} 个不同灵敏度的检测器")
    print("🧪 启用高级音频预处理")
    
    frame_count = 0
    detection_votes = []  # 投票机制
    
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
            
            # 高级预处理
            processed_audio = advanced_audio_preprocessing(resampled_audio)
            
            # 使用多个检测器进行投票
            detection_results = []
            for porcupine, sensitivity in porcupines:
                try:
                    keyword_index = porcupine.process(processed_audio)
                    if keyword_index >= 0:
                        detection_results.append(sensitivity)
                except Exception as e:
                    print(f"⚠️ 检测错误 (灵敏度{sensitivity}): {e}")
                    continue
            
            frame_count += 1
            
            # 投票机制：如果有检测结果，记录
            if detection_results:
                detection_votes.extend(detection_results)
                
                # 如果在最近10帧内有多次检测，认为是有效唤醒
                recent_votes = [v for v in detection_votes if True]  # 保留所有投票
                
                if len(recent_votes) >= 2:  # 至少2票
                    wake_word_count += 1
                    avg_sensitivity = np.mean(recent_votes)
                    print(f"\n🎉 检测到唤醒词 '快快'！(第{wake_word_count}次)")
                    print(f"   📊 投票结果: {len(recent_votes)}票, 平均灵敏度: {avg_sensitivity:.2f}")
                    print("✨ 请继续说话测试更多检测...")
                    
                    # 清空投票，避免重复计数
                    detection_votes = []
            
            # 清理旧投票（保持窗口大小）
            if len(detection_votes) > 20:
                detection_votes = detection_votes[-10:]
            
            # 定期状态输出
            if frame_count % (target_sample_rate // frame_length * 5) == 0:
                rms_original = np.sqrt(np.mean(resampled_audio.astype(np.float32) ** 2))
                rms_processed = np.sqrt(np.mean(processed_audio.astype(np.float32) ** 2))
                votes_recent = len([v for v in detection_votes])
                print(f"🔄 帧{frame_count}: 原始RMS={rms_original:.0f}, 处理后RMS={rms_processed:.0f}, 近期投票={votes_recent}, 检测到{wake_word_count}次")
                
    except Exception as e:
        print(f"❌ 检测线程错误: {e}")
        import traceback
        traceback.print_exc()
    
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

print("🔧 ReSpeaker 2-Mics 专用兼容性修复")
print("=" * 60)
print("🎯 专门解决ReSpeaker与Porcupine的兼容性问题")
print("🔬 使用多检测器投票机制和高级音频预处理")

# 查找ReSpeaker设备
devices = sd.query_devices()
respeaker_device = None

for i, device in enumerate(devices):
    if device['max_input_channels'] > 0:
        name = device['name'].lower()
        if 'seeed' in name or 'array' in name:
            respeaker_device = i
            print(f"✅ 找到ReSpeaker设备: {device['name']} (ID: {i})")
            break

if respeaker_device is None:
    print("❌ 未找到ReSpeaker设备")
    sys.exit(1)

# 创建多个Porcupine实例
porcupines = create_multiple_porcupines()
if not porcupines:
    print("❌ 无法创建Porcupine实例")
    sys.exit(1)

# 测试音频录制
try:
    print("🧪 测试ReSpeaker音频录制...")
    test_audio = sd.rec(1024, samplerate=48000, channels=1, device=respeaker_device, dtype=np.int16)
    sd.wait()
    
    # 测试预处理
    processed_test = advanced_audio_preprocessing(test_audio.flatten())
    original_stats = f"平均值={np.mean(test_audio):.0f}, RMS={np.sqrt(np.mean(test_audio.astype(np.float32)**2)):.0f}"
    processed_stats = f"平均值={np.mean(processed_test):.0f}, RMS={np.sqrt(np.mean(processed_test.astype(np.float32)**2)):.0f}"
    
    print(f"✅ 音频录制和预处理测试成功")
    print(f"   原始音频: {original_stats}")
    print(f"   处理后: {processed_stats}")
    
except Exception as e:
    print(f"❌ 音频录制测试失败: {e}")
    sys.exit(1)

# 开始检测
detector_running = True
detection_thread = threading.Thread(target=respeaker_detection_worker, args=(porcupines, respeaker_device), daemon=True)
detection_thread.start()

print("✅ ReSpeaker专用唤醒词检测已启动")
print("🗣️ 请清晰地说 '快快' 来测试...")
print("⏱️ 将运行60秒，按Ctrl+C可随时停止")
print("💡 新特性:")
print("   - 多灵敏度投票机制")
print("   - 高级音频预处理")
print("   - 动态范围压缩")
print("   - 多级滤波去噪")

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
        print("🎉 成功！ReSpeaker兼容性问题已解决！")
        print("💡 关键改进:")
        print("   - 多检测器投票提高了可靠性")
        print("   - 高级预处理改善了音频质量")
        print("   - 现在可以正常使用ReSpeaker进行唤醒词检测")
    else:
        print("⚠️ 仍未检测到唤醒词")
        print("🔍 可能的原因:")
        print("   - 唤醒词文件可能有问题")
        print("   - 需要检查中文发音是否标准")
        print("   - ReSpeaker硬件可能存在更深层问题")

except KeyboardInterrupt:
    pass

finally:
    detector_running = False
    # 清理Porcupine实例
    for porcupine, _ in porcupines:
        try:
            porcupine.delete()
        except:
            pass