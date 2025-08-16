#!/usr/bin/env python3
"""
调试Vosk中文识别问题
专门用于诊断Vosk识别失败的原因
"""

import os
import sys
import time
import speech_recognition as sr
import logging
import json
import numpy as np
import wave
import tempfile

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.insert(0, 'src')

def test_vosk_model_loading():
    """测试Vosk模型加载"""
    print("🔧 测试Vosk模型加载...")
    
    try:
        import vosk
        print("✅ Vosk库导入成功")
        
        # 设置日志级别
        vosk.SetLogLevel(0)  # 启用详细日志
        
        model_path = "models/vosk-model-small-cn-0.22"
        if os.path.exists(model_path):
            print(f"✅ 找到模型路径: {model_path}")
            
            # 尝试加载模型
            model = vosk.Model(model_path)
            print("✅ Vosk模型加载成功")
            
            # 创建识别器
            recognizer = vosk.KaldiRecognizer(model, 16000)
            recognizer.SetWords(True)
            print("✅ Vosk识别器创建成功")
            
            return model, recognizer
        else:
            print(f"❌ 模型路径不存在: {model_path}")
            return None, None
            
    except Exception as e:
        print(f"❌ Vosk测试失败: {e}")
        return None, None

def test_audio_format_conversion():
    """测试音频格式转换"""
    print("\n🔧 测试音频格式转换...")
    
    # 初始化语音识别
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    print("🎙️ 请说一句中文，测试音频转换...")
    
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        
        # 获取原始音频数据
        raw_data = audio.get_raw_data()
        sample_rate = audio.sample_rate
        sample_width = audio.sample_width
        
        print(f"📊 原始音频信息:")
        print(f"   数据长度: {len(raw_data)} 字节")
        print(f"   采样率: {sample_rate} Hz")
        print(f"   采样宽度: {sample_width} 字节")
        print(f"   声道数: 1 (假设)")
        
        # 转换为numpy数组分析
        audio_array = np.frombuffer(raw_data, dtype=np.int16)
        print(f"   样本数: {len(audio_array)}")
        print(f"   时长: {len(audio_array) / sample_rate:.2f} 秒")
        print(f"   最大振幅: {np.max(np.abs(audio_array))}")
        print(f"   RMS音量: {np.sqrt(np.mean(audio_array**2)):.2f}")
        
        # 检查是否需要重采样
        target_rate = 16000
        if sample_rate != target_rate:
            print(f"🔄 需要重采样: {sample_rate} Hz → {target_rate} Hz")
            
            from scipy import signal
            num_samples = int(len(audio_array) * target_rate / sample_rate)
            resampled_array = signal.resample(audio_array, num_samples)
            resampled_data = resampled_array.astype(np.int16).tobytes()
            
            print(f"   重采样后长度: {len(resampled_data)} 字节")
            print(f"   重采样后样本数: {len(resampled_array)}")
            
            return resampled_data, target_rate
        else:
            return raw_data, sample_rate
            
    except Exception as e:
        print(f"❌ 音频格式转换测试失败: {e}")
        return None, None

def test_vosk_recognition_step_by_step():
    """逐步测试Vosk识别过程"""
    print("\n🔧 逐步测试Vosk识别...")
    
    # 1. 加载模型
    model, recognizer = test_vosk_model_loading()
    if not model or not recognizer:
        return False
    
    # 2. 获取音频数据
    audio_data, sample_rate = test_audio_format_conversion()
    if not audio_data:
        return False
    
    # 3. 测试Vosk识别
    print("\n🎯 开始Vosk识别...")
    
    try:
        # 重置识别器
        recognizer.Reset()
        print("✅ 识别器重置成功")
        
        # 分块处理音频数据
        chunk_size = 4096
        total_chunks = len(audio_data) // chunk_size
        print(f"📦 音频分为 {total_chunks} 个块处理")
        
        final_result = None
        partial_results = []
        
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            
            if recognizer.AcceptWaveform(chunk):
                result = recognizer.Result()
                result_dict = json.loads(result)
                print(f"📄 块 {i//chunk_size + 1} 完整结果: {result}")
                
                if result_dict.get('text'):
                    final_result = result_dict['text']
                    break
            else:
                partial = recognizer.PartialResult()
                partial_dict = json.loads(partial)
                if partial_dict.get('partial'):
                    partial_results.append(partial_dict['partial'])
                    print(f"🔄 块 {i//chunk_size + 1} 部分结果: {partial_dict['partial']}")
        
        # 获取最终结果
        if not final_result:
            final_result_json = recognizer.FinalResult()
            final_result_dict = json.loads(final_result_json)
            final_result = final_result_dict.get('text')
            print(f"📋 最终结果: {final_result_json}")
        
        if final_result and final_result.strip():
            print(f"🎉 Vosk识别成功: '{final_result}'")
            return True
        elif partial_results:
            print(f"⚠️ 只有部分结果: {partial_results}")
            return False
        else:
            print("❌ Vosk未识别到任何内容")
            
            # 额外诊断
            print("\n🔍 诊断信息:")
            print("可能原因:")
            print("1. 音频质量不够好（噪音太大、音量太小）")
            print("2. 说话内容不在模型词汇表中")
            print("3. 音频格式转换有问题")
            print("4. 语速过快或过慢")
            print("5. 方言或口音问题")
            
            return False
            
    except Exception as e:
        print(f"❌ Vosk识别过程失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def save_audio_for_analysis(audio_data, sample_rate, filename="debug_audio.wav"):
    """保存音频文件用于分析"""
    try:
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)  # 单声道
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)
        
        print(f"💾 音频已保存: {filename}")
        print(f"   可以用音频播放器检查音频质量")
        return filename
    except Exception as e:
        print(f"❌ 保存音频失败: {e}")
        return None

def test_different_phrases():
    """测试不同的中文短语"""
    print("\n🗣️ 测试不同中文短语的识别效果...")
    
    test_phrases = [
        "你好",
        "今天天气很好", 
        "我想要一杯水",
        "请打开电视",
        "现在几点了",
        "谢谢你",
        "再见"
    ]
    
    print("建议测试的短语:")
    for i, phrase in enumerate(test_phrases, 1):
        print(f"  {i}. {phrase}")
    
    model, recognizer = test_vosk_model_loading()
    if not model or not recognizer:
        return
    
    # 初始化语音识别
    sr_recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    success_count = 0
    total_count = 0
    
    for phrase in test_phrases:
        print(f"\n--- 测试短语: {phrase} ---")
        input(f"准备说 '{phrase}'，按Enter开始录音...")
        
        try:
            with microphone as source:
                sr_recognizer.adjust_for_ambient_noise(source, duration=0.5)
                print("🎙️ 正在录音...")
                audio = sr_recognizer.listen(source, timeout=3, phrase_time_limit=5)
            
            # 转换音频格式
            raw_data = audio.get_raw_data()
            if audio.sample_rate != 16000:
                from scipy import signal
                audio_array = np.frombuffer(raw_data, dtype=np.int16)
                num_samples = int(len(audio_array) * 16000 / audio.sample_rate)
                resampled_array = signal.resample(audio_array, num_samples)
                audio_data = resampled_array.astype(np.int16).tobytes()
            else:
                audio_data = raw_data
            
            # Vosk识别
            recognizer.Reset()
            if recognizer.AcceptWaveform(audio_data):
                result = json.loads(recognizer.Result())
                text = result.get('text', '').strip()
            else:
                final_result = json.loads(recognizer.FinalResult())
                text = final_result.get('text', '').strip()
            
            total_count += 1
            if text:
                print(f"✅ 识别结果: '{text}'")
                if phrase in text or text in phrase:
                    print("🎯 识别正确！")
                    success_count += 1
                else:
                    print("⚠️ 识别结果与预期不符")
            else:
                print("❌ 未识别到内容")
                
        except Exception as e:
            print(f"❌ 录音或识别失败: {e}")
            total_count += 1
    
    print(f"\n📊 测试总结:")
    print(f"   成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)" if total_count > 0 else "无有效测试")

if __name__ == "__main__":
    print("🔍 Vosk中文识别调试工具")
    print("=" * 60)
    
    # 检查依赖
    try:
        import vosk
        import scipy
        print("✅ 依赖库检查通过")
    except ImportError as e:
        print(f"❌ 缺少依赖库: {e}")
        print("请安装: pip install vosk scipy")
        sys.exit(1)
    
    # 逐步测试
    print("\n🧪 开始逐步测试...")
    
    # 测试1: 单次识别
    if test_vosk_recognition_step_by_step():
        print("\n🎉 基础识别测试通过！")
        
        # 测试2: 多短语测试
        choice = input("\n是否进行多短语测试？(y/n): ").strip().lower()
        if choice == 'y':
            test_different_phrases()
    else:
        print("\n😞 基础识别测试失败")
        print("💡 建议:")
        print("1. 确保在安静环境中测试")
        print("2. 靠近麦克风说话")
        print("3. 使用标准普通话发音")
        print("4. 语速适中，清晰发音")
        print("5. 检查麦克风音量设置")