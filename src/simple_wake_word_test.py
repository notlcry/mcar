#!/usr/bin/python3
"""
简化版唤醒词测试 - 直接使用ALSA硬件设备
绕过复杂的音频配置问题
"""

import pvporcupine
import pyaudio
import numpy as np
import time
import os
import logging

# 设置基本日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_simple_wake_word():
    """简化的唤醒词测试"""
    print("🔧 简化版唤醒词测试")
    print("=" * 30)
    
    # 查找唤醒词文件
    wake_word_file = None
    for path in ["../wake_words/kk_zh_raspberry-pi_v3_0_0.ppn", "wake_words/kk_zh_raspberry-pi_v3_0_0.ppn"]:
        if os.path.exists(path):
            wake_word_file = path
            break
    
    if not wake_word_file:
        print("❌ 未找到唤醒词文件")
        return
    
    print(f"✅ 使用唤醒词文件: {wake_word_file}")
    
    # 查找中文模型
    model_file = None
    for path in ["../wake_words/porcupine_params_zh.pv", "wake_words/porcupine_params_zh.pv"]:
        if os.path.exists(path):
            model_file = path
            break
    
    if model_file:
        print(f"✅ 使用中文模型: {model_file}")
    
    # 获取访问密钥
    access_key = os.getenv('PICOVOICE_ACCESS_KEY')
    if not access_key:
        print("❌ 未找到PICOVOICE_ACCESS_KEY")
        return
    
    print(f"✅ 访问密钥: {access_key[:10]}...")
    
    try:
        # 初始化Porcupine（高灵敏度）
        print("\n🔧 初始化Porcupine...")
        porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=[wake_word_file],
            sensitivities=[0.9],  # 非常高的灵敏度
            model_path=model_file
        )
        print("✅ Porcupine初始化成功")
        
        # 简单的音频设备查找
        print("\n🎤 查找音频设备...")
        pa = pyaudio.PyAudio()
        
        device_index = None
        device_info = None
        
        # 直接尝试使用设备1（通常是USB音频设备）
        try:
            info = pa.get_device_info_by_index(1)
            if info['maxInputChannels'] > 0:
                device_index = 1
                device_info = info
                print(f"✅ 使用设备1: {info['name']}")
        except:
            pass
        
        # 如果没找到，使用默认输入设备
        if device_index is None:
            try:
                device_index = pa.get_default_input_device_info()['index']
                device_info = pa.get_default_input_device_info()
                print(f"✅ 使用默认设备: {device_info['name']}")
            except:
                print("❌ 无法找到音频输入设备")
                pa.terminate()
                return
        
        # 音频配置（使用最简单的配置）
        sample_rate = 16000  # 直接使用Porcupine要求的采样率
        channels = 1         # 单声道
        format = pyaudio.paInt16
        frames_per_buffer = porcupine.frame_length  # 使用Porcupine要求的帧长度
        
        print(f"📊 音频配置: {sample_rate}Hz, {channels}声道, 缓冲区:{frames_per_buffer}")
        
        # 打开音频流
        print("\n🎯 开始录音...")
        try:
            stream = pa.open(
                format=format,
                channels=channels,
                rate=sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=frames_per_buffer,
                start=False  # 手动启动
            )
            
            stream.start_stream()
            print("✅ 音频流启动成功")
            
        except Exception as e:
            print(f"❌ 音频流启动失败: {e}")
            
            # 尝试备用配置（48kHz采样率）
            print("🔄 尝试48kHz采样率...")
            try:
                sample_rate = 48000
                frames_per_buffer = int(48000 * 0.032)  # 32ms
                
                stream = pa.open(
                    format=format,
                    channels=2,  # 立体声
                    rate=sample_rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=frames_per_buffer
                )
                
                print("✅ 48kHz音频流启动成功")
                channels = 2
                
            except Exception as e2:
                print(f"❌ 48kHz也失败: {e2}")
                pa.terminate()
                return
        
        print("\n💡 请说'快快'进行测试...")
        print("⌨️ 按Ctrl+C停止\n")
        
        # 检测循环
        try:
            detection_count = 0
            frames_processed = 0
            
            while True:
                try:
                    # 读取音频数据
                    audio_frame = stream.read(frames_per_buffer, exception_on_overflow=False)
                    audio_data = np.frombuffer(audio_frame, dtype=np.int16)
                    
                    # 立体声转单声道
                    if channels == 2:
                        audio_data = audio_data[0::2]
                    
                    # 重采样到16kHz（如果需要）
                    if sample_rate != 16000:
                        # 简单的降采样
                        step = sample_rate // 16000
                        audio_data = audio_data[::step]
                    
                    # 确保长度正确
                    required_length = porcupine.frame_length
                    if len(audio_data) >= required_length:
                        audio_data = audio_data[:required_length]
                        
                        # 唤醒词检测
                        keyword_index = porcupine.process(audio_data)
                        
                        if keyword_index >= 0:
                            detection_count += 1
                            print(f"🎉 检测到唤醒词! (第{detection_count}次)")
                            print(f"📅 时间: {time.strftime('%H:%M:%S')}")
                            print("继续监听...\n")
                    
                    frames_processed += 1
                    
                    # 每100帧显示一次状态
                    if frames_processed % 100 == 0:
                        print(f"📊 已处理 {frames_processed} 帧，检测到 {detection_count} 次唤醒词")
                
                except Exception as e:
                    print(f"⚠️ 处理错误: {e}")
                    time.sleep(0.01)
                    continue
        
        except KeyboardInterrupt:
            print("\n⏹️ 停止测试")
        
        finally:
            # 清理资源
            if 'stream' in locals():
                stream.stop_stream()
                stream.close()
            pa.terminate()
            porcupine.delete()
            
            print(f"\n📊 测试统计:")
            print(f"   - 处理帧数: {frames_processed}")
            print(f"   - 检测次数: {detection_count}")
            print("✅ 测试完成")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_wake_word()