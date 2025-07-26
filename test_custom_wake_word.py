#!/usr/bin/env python3
# 测试自定义唤醒词

import os
import sys
import time
import struct
import pyaudio

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
sys.path.insert(0, 'src')

def test_custom_wake_word():
    print("====================================")
    print("🎤 测试自定义唤醒词 'kk'")
    print("====================================")
    
    try:
        import pvporcupine
        
        access_key = os.getenv('PICOVOICE_ACCESS_KEY')
        if not access_key:
            print("❌ PICOVOICE_ACCESS_KEY未设置")
            return False
        
        # 检查文件是否存在
        model_path = 'src/wake_words/porcupine_params_zh.pv'
        keyword_path = 'src/wake_words/kk_zh_raspberry-pi_v3_0_0.ppn'
        
        if not os.path.exists(model_path):
            print(f"❌ 中文模型文件不存在: {model_path}")
            return False
            
        if not os.path.exists(keyword_path):
            print(f"❌ 唤醒词文件不存在: {keyword_path}")
            return False
        
        print("✅ 文件检查通过")
        print(f"   模型文件: {model_path}")
        print(f"   唤醒词文件: {keyword_path}")
        
        # 初始化Porcupine
        porcupine = pvporcupine.create(
            access_key=access_key,
            model_path=model_path,
            keyword_paths=[keyword_path]
        )
        
        print("✅ Porcupine初始化成功")
        print(f"   采样率: {porcupine.sample_rate}")
        print(f"   帧长度: {porcupine.frame_length}")
        
        # 初始化音频
        pa = pyaudio.PyAudio()
        audio_stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length
        )
        
        print("✅ 音频流初始化成功")
        print()
        print("🎤 请说 'kk' 来测试唤醒词检测...")
        print("   按Ctrl+C停止测试")
        print()
        
        try:
            while True:
                pcm = audio_stream.read(porcupine.frame_length)
                pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                
                keyword_index = porcupine.process(pcm)
                if keyword_index >= 0:
                    print("🎉 检测到唤醒词 'kk'！")
                    print("   系统已唤醒，可以开始对话")
                    break
                    
        except KeyboardInterrupt:
            print("\n测试中断")
        
        # 清理资源
        audio_stream.close()
        pa.terminate()
        porcupine.delete()
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_fallback_wake_word():
    """测试备选的英文唤醒词"""
    print("\n====================================")
    print("🎤 测试备选唤醒词 'picovoice'")
    print("====================================")
    
    try:
        import pvporcupine
        
        access_key = os.getenv('PICOVOICE_ACCESS_KEY')
        
        porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=['picovoice']
        )
        
        print("✅ 备选唤醒词配置成功")
        print("   可以说 'picovoice' 来唤醒系统")
        
        porcupine.delete()
        return True
        
    except Exception as e:
        print(f"❌ 备选唤醒词测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_custom_wake_word()
    
    if not success:
        print("\n⚠️  自定义唤醒词测试失败，尝试备选方案...")
        test_fallback_wake_word()
    
    print("\n📋 使用说明:")
    print("• 如果自定义唤醒词工作正常，说 'kk' 来唤醒")
    print("• 如果不工作，可以说 'picovoice' 作为备选")
    print("• 启动完整系统: cd src && python3 robot_voice_web_control.py")