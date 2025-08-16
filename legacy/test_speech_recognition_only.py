#!/usr/bin/env python3
"""
专门测试语音识别功能
不涉及AI对话，只测试语音识别的准确性
"""

import os
import sys
import time
import speech_recognition as sr
import logging

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        logger.info("✅ 环境变量加载成功")
    except Exception as e:
        logger.warning(f"⚠️  环境变量加载失败: {e}")

load_env()
sys.path.insert(0, 'src')

def test_basic_speech_recognition():
    """测试基础语音识别功能"""
    print("🎤 基础语音识别测试")
    print("=" * 50)
    
    # 初始化识别器和麦克风
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    print("🔧 初始化音频设备...")
    
    # 检查麦克风
    try:
        mic_list = sr.Microphone.list_microphone_names()
        print(f"📱 可用麦克风: {len(mic_list)} 个")
        for i, name in enumerate(mic_list):
            print(f"   {i}: {name}")
    except Exception as e:
        print(f"❌ 麦克风检查失败: {e}")
        return False
    
    # 调整环境噪音
    print("\n🔧 调整环境噪音...")
    try:
        with microphone as source:
            print("请保持安静，正在调整环境噪音...")
            recognizer.adjust_for_ambient_noise(source, duration=3)
            print(f"✅ 环境噪音调整完成")
            print(f"   能量阈值: {recognizer.energy_threshold}")
    except Exception as e:
        print(f"❌ 环境噪音调整失败: {e}")
        return False
    
    # 优化识别器参数
    recognizer.energy_threshold = 4000
    recognizer.pause_threshold = 1.0
    recognizer.timeout = 2
    recognizer.phrase_time_limit = 10
    
    print(f"🔧 识别器参数:")
    print(f"   能量阈值: {recognizer.energy_threshold}")
    print(f"   停顿阈值: {recognizer.pause_threshold}")
    print(f"   超时时间: {recognizer.timeout}")
    print(f"   最大录音时长: {recognizer.phrase_time_limit}")
    
    # 开始测试
    print("\n🎙️  语音识别测试开始")
    print("💡 建议测试短语:")
    print("   - '你好'")
    print("   - '今天天气怎么样'")
    print("   - '我想和你聊天'")
    print("   - '你是谁'")
    
    test_count = 1
    success_count = 0
    
    while True:
        print(f"\n--- 测试 {test_count} ---")
        user_input = input("按Enter开始录音，输入'q'退出: ").strip()
        
        if user_input.lower() == 'q':
            break
        
        print("🎙️  请说话（清晰地说一句中文）...")
        
        try:
            # 录音
            with microphone as source:
                # 短暂调整噪音
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                logger.debug("开始录音...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
                logger.debug("录音完成")
            
            print("🔍 正在识别...")
            
            # 测试Google识别（最准确）
            google_success = False
            try:
                logger.debug("尝试Google识别...")
                google_result = recognizer.recognize_google(audio, language='zh-CN')
                if google_result and google_result.strip():
                    print(f"✅ Google识别: '{google_result}'")
                    google_success = True
                else:
                    print("❌ Google: 返回空结果")
            except sr.UnknownValueError:
                print("❌ Google: 无法理解音频")
                logger.debug("Google无法理解音频")
            except sr.RequestError as e:
                print(f"❌ Google: 网络错误 ({e})")
                logger.error(f"Google网络错误: {e}")
            except Exception as e:
                print(f"❌ Google: 其他错误 ({e})")
                logger.error(f"Google其他错误: {e}")
            
            # 测试Vosk识别（中文离线）
            vosk_success = False
            try:
                logger.debug("尝试Vosk识别...")
                from vosk_recognizer import VoskRecognizer
                vosk_recognizer = VoskRecognizer()
                if vosk_recognizer.is_available:
                    vosk_result = vosk_recognizer.recognize_from_speech_recognition_audio(audio)
                    if vosk_result and vosk_result.strip():
                        print(f"✅ Vosk识别: '{vosk_result}'")
                        vosk_success = True
                    else:
                        print("❌ Vosk: 返回空结果")
                else:
                    print("❌ Vosk: 不可用")
            except Exception as e:
                print(f"❌ Vosk: 错误 ({e})")
                logger.error(f"Vosk错误: {e}")
            
            # 测试PocketSphinx识别（英文离线）
            sphinx_success = False
            try:
                logger.debug("尝试PocketSphinx识别...")
                sphinx_result = recognizer.recognize_sphinx(audio)
                if sphinx_result and sphinx_result.strip():
                    print(f"✅ Sphinx识别: '{sphinx_result}'")
                    sphinx_success = True
                else:
                    print("❌ Sphinx: 返回空结果")
            except Exception as e:
                print(f"❌ Sphinx: 错误 ({e})")
                logger.error(f"Sphinx错误: {e}")
            
            # 统计成功率
            if google_success or vosk_success or sphinx_success:
                success_count += 1
                print(f"🎉 本次测试成功！")
            else:
                print(f"😞 本次测试失败，所有引擎都无法识别")
            
            print(f"📊 成功率: {success_count}/{test_count} ({success_count/test_count*100:.1f}%)")
            
            test_count += 1
            
        except sr.WaitTimeoutError:
            print("⏰ 录音超时，请重试")
            logger.warning("录音超时")
        except Exception as e:
            print(f"❌ 录音失败: {e}")
            logger.error(f"录音失败: {e}")
    
    print(f"\n📊 测试总结:")
    print(f"   总测试次数: {test_count - 1}")
    print(f"   成功次数: {success_count}")
    print(f"   成功率: {success_count/(test_count-1)*100:.1f}%" if test_count > 1 else "无有效测试")
    
    return success_count > 0

def test_audio_quality():
    """测试音频质量"""
    print("\n🔊 音频质量测试")
    print("=" * 50)
    
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    print("🎙️  请说话，我们来检查音频质量...")
    
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=2)
            print(f"🔧 环境噪音级别: {recognizer.energy_threshold}")
            
            print("现在请说话...")
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            
            # 获取音频数据
            wav_data = audio.get_wav_data()
            print(f"📊 音频数据大小: {len(wav_data)} 字节")
            print(f"📊 采样率: {audio.sample_rate} Hz")
            print(f"📊 采样宽度: {audio.sample_width} 字节")
            
            # 简单的音量检测
            import struct
            import numpy as np
            
            # 转换为numpy数组进行分析
            audio_data = np.frombuffer(wav_data, dtype=np.int16)
            
            # 计算音频统计
            max_amplitude = np.max(np.abs(audio_data))
            rms = np.sqrt(np.mean(audio_data**2))
            
            print(f"📊 最大振幅: {max_amplitude}")
            print(f"📊 RMS音量: {rms:.2f}")
            
            # 音质评估
            if max_amplitude < 1000:
                print("⚠️  音量可能太小")
            elif max_amplitude > 30000:
                print("⚠️  音量可能太大，可能有削波")
            else:
                print("✅ 音量适中")
            
            if rms < 500:
                print("⚠️  信号强度较弱")
            else:
                print("✅ 信号强度良好")
            
    except Exception as e:
        print(f"❌ 音频质量测试失败: {e}")
        logger.error(f"音频质量测试失败: {e}")

def diagnose_recognition_issues():
    """诊断识别问题"""
    print("\n🔍 识别问题诊断")
    print("=" * 50)
    
    # 检查依赖
    print("📦 检查依赖包...")
    
    try:
        import speech_recognition
        print(f"✅ speech_recognition: {speech_recognition.__version__}")
    except Exception as e:
        print(f"❌ speech_recognition: {e}")
    
    try:
        import pyaudio
        print(f"✅ pyaudio: 已安装")
    except Exception as e:
        print(f"❌ pyaudio: {e}")
    
    try:
        from vosk_recognizer import VoskRecognizer
        vosk = VoskRecognizer()
        if vosk.is_available:
            print(f"✅ Vosk: 可用")
        else:
            print(f"❌ Vosk: 不可用")
    except Exception as e:
        print(f"❌ Vosk: {e}")
    
    # 检查网络连接（Google识别需要）
    print("\n🌐 检查网络连接...")
    try:
        import urllib.request
        urllib.request.urlopen('https://www.google.com', timeout=5)
        print("✅ 网络连接正常")
    except Exception as e:
        print(f"❌ 网络连接问题: {e}")
    
    # 检查麦克风权限
    print("\n🎤 检查麦克风权限...")
    try:
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
        print("✅ 麦克风权限正常")
    except Exception as e:
        print(f"❌ 麦克风权限问题: {e}")

if __name__ == "__main__":
    print("🎤 语音识别专项测试")
    print("=" * 60)
    
    # 先进行诊断
    diagnose_recognition_issues()
    
    # 音频质量测试
    test_audio_quality()
    
    # 基础识别测试
    if test_basic_speech_recognition():
        print("\n🎉 语音识别基本功能正常！")
        print("💡 如果在AI对话中仍有问题，可能是:")
        print("   1. AI对话管理器的问题")
        print("   2. 语音识别参数需要进一步调优")
        print("   3. 网络连接不稳定影响Google识别")
    else:
        print("\n😞 语音识别存在问题")
        print("💡 建议:")
        print("   1. 检查麦克风是否正常工作")
        print("   2. 确保网络连接稳定")
        print("   3. 尝试在安静环境中测试")
        print("   4. 说话时保持适中音量和清晰发音")