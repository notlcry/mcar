#!/usr/bin/python3
"""
音频设备检测脚本
"""
import pyaudio

def list_audio_devices():
    p = pyaudio.PyAudio()
    print(f"音频设备数量: {p.get_device_count()}")
    
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        device_type = "输入" if info['maxInputChannels'] > 0 else "输出"
        print(f"{i}: {info['name']} ({device_type}) - 采样率:{info['defaultSampleRate']}")
    
    p.terminate()

if __name__ == "__main__":
    list_audio_devices()