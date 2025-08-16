#!/usr/bin/env python3
"""
使用官方推荐方式的唤醒词测试
"""

import os
import sys
import struct
import pyaudio
import pvporcupine

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

def test_official_way():
    """使用官方推荐的方式测试"""
    print("🎤 官方方式唤醒词测试")
    print("=" * 40)
    
    try:
        access_key = os.getenv('PICOVOICE_ACCESS_KEY')
        chinese_model = 'models/porcupine/porcupine_params_zh.pv'
        keyword_path = 'wake_words/kk_zh_raspberry-pi_v3_0_0.ppn'
        
        # 创建Porcupine实例
        porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=[keyword_path],
            model_path=chinese_model,
            sensitivities=[0.7]  # 提高灵敏度
        )
        
        print(f"✅ Porcupine初始化成功")
        print(f"   采样率: {porcupine.sample_rate} Hz")
        print(f"   帧长度: {porcupine.frame_length}")
        
        # 创建PyAudio实例
        pa = pyaudio.PyAudio()
        
        # 直接使用Porcupine要求的采样率
        audio_stream = pa.open(
            rate=porcupine.sample_rate,  # 直接使用16000Hz
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length
        )
        
        print(f"\n🎙️  开始监听唤醒词 '快快'...")
        print(f"💡 使用Porcupine原生采样率: {porcupine.sample_rate} Hz")
        print("按 Ctrl+C 停止")
        print("-" * 40)
        
        frame_count = 0
        
        try:
            while True:
                # 读取音频数据
                pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
                
                # 转换为Porcupine需要的格式
                pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                
                # 检测唤醒词
                keyword_index = porcupine.process(pcm)
                
                if keyword_index >= 0:
                    print(f"\n🎉 检测到唤醒词 '快快'！索引: {keyword_index}")
                    print(f"🗣️  回应: 你好！我听到了！")
                    print("继续监听...")
                
                frame_count += 1
                if frame_count % 100 == 0:
                    print(".", end="", flush=True)
                if frame_count % 5000 == 0:
                    print(f" [{frame_count} 帧]")
                
        except KeyboardInterrupt:
            print("\n\n🛑 停止测试...")
        
        finally:
            audio_stream.close()
            pa.terminate()
            porcupine.delete()
            print("✅ 测试结束")
            
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_device_selection():
    """测试时手动选择音频设备"""
    print("\n🔍 音频设备选择测试")
    print("=" * 40)
    
    try:
        pa = pyaudio.PyAudio()
        
        print("可用的输入设备:")
        input_devices = []
        
        for i in range(pa.get_device_count()):
            try:
                info = pa.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    input_devices.append((i, info))
                    print(f"  {len(input_devices)}: 设备 {i} - {info['name']}")
                    print(f"     采样率: {info['defaultSampleRate']} Hz")
                    print(f"     通道数: {info['maxInputChannels']}")
            except:
                pass
        
        pa.terminate()
        
        if not input_devices:
            print("❌ 没有找到输入设备")
            return False
        
        # 自动选择第一个设备
        selected_device = input_devices[0][0]
        device_info = input_devices[0][1]
        
        print(f"\n✅ 自动选择设备 {selected_device}: {device_info['name']}")
        
        # 使用选定设备测试
        return test_with_specific_device(selected_device)
        
    except Exception as e:
        print(f"❌ 设备选择失败: {e}")
        return False

def test_with_specific_device(device_index):
    """使用指定设备测试"""
    print(f"\n🎤 使用设备 {device_index} 测试")
    print("=" * 30)
    
    try:
        access_key = os.getenv('PICOVOICE_ACCESS_KEY')
        chinese_model = 'models/porcupine/porcupine_params_zh.pv'
        keyword_path = 'wake_words/kk_zh_raspberry-pi_v3_0_0.ppn'
        
        # 创建Porcupine实例
        porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=[keyword_path],
            model_path=chinese_model,
            sensitivities=[0.8]  # 更高的灵敏度
        )
        
        # 创建音频流，指定设备
        pa = pyaudio.PyAudio()
        
        audio_stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=porcupine.frame_length
        )
        
        print(f"🎙️  使用设备 {device_index} 监听 '快快' (灵敏度: 0.8)")
        print("测试15秒...")
        
        import time
        start_time = time.time()
        detections = 0
        
        while time.time() - start_time < 15:
            try:
                pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                
                keyword_index = porcupine.process(pcm)
                
                if keyword_index >= 0:
                    detections += 1
                    print(f"🎉 检测 #{detections}: '快快' (设备 {device_index})")
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"读取错误: {e}")
                break
        
        audio_stream.close()
        pa.terminate()
        porcupine.delete()
        
        print(f"📊 15秒内检测到 {detections} 次")
        return detections > 0
        
    except Exception as e:
        print(f"❌ 设备测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🎤 官方方式唤醒词检测测试")
    print("=" * 50)
    
    print("💡 这个测试使用Porcupine原生采样率(16kHz)，避免重采样问题")
    print("💡 如果这个版本能工作，说明问题在于重采样")
    
    # 先测试官方方式
    if test_official_way():
        print("\n🎉 官方方式测试成功！")
    else:
        print("\n❌ 官方方式也失败，尝试设备选择...")
        
        # 如果官方方式失败，尝试设备选择
        if test_with_device_selection():
            print("\n🎉 设备选择测试成功！")
        else:
            print("\n❌ 所有测试都失败")
            print("\n🔧 可能的解决方案:")
            print("• 检查麦克风是否正常工作")
            print("• 尝试在安静环境中测试")
            print("• 确认唤醒词发音准确")
            print("• 检查ALSA配置是否正确")