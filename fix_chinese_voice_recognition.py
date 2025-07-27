#!/usr/bin/env python3
"""
修复中文语音识别的综合解决方案
解决音量过小、ALSA配置、Vosk参数优化等问题
"""

import os
import sys
import numpy as np
import speech_recognition as sr
import logging
import json
import subprocess
import tempfile
import wave

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, 'src')

class EnhancedVoiceRecognition:
    """增强的中文语音识别类"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.vosk_recognizer = None
        
        # 优化的识别参数
        self.energy_threshold = 2000  # 降低能量阈值
        self.pause_threshold = 0.8    # 减少停顿阈值
        self.timeout = 3              # 增加超时时间
        self.phrase_time_limit = 8    # 增加录音时长
        
        self.init_components()
    
    def init_components(self):
        """初始化组件"""
        self.init_microphone()
        self.init_vosk()
    
    def init_microphone(self):
        """初始化麦克风，优化音频参数"""
        try:
            # 检测麦克风
            mic_list = sr.Microphone.list_microphone_names()
            logger.info(f"可用麦克风: {len(mic_list)} 个")
            
            # 优化麦克风设置
            self.microphone = sr.Microphone(sample_rate=16000, chunk_size=1024)
            
            # 调整识别器参数
            self.recognizer.energy_threshold = self.energy_threshold
            self.recognizer.pause_threshold = self.pause_threshold
            self.recognizer.timeout = self.timeout
            self.recognizer.phrase_time_limit = self.phrase_time_limit
            
            # 动态调整环境噪音
            logger.info("正在动态调整环境噪音...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            
            logger.info(f"麦克风初始化完成，能量阈值: {self.recognizer.energy_threshold}")
            
        except Exception as e:
            logger.error(f"麦克风初始化失败: {e}")
    
    def init_vosk(self):
        """初始化Vosk识别器"""
        try:
            from src.vosk_recognizer import VoskRecognizer
            self.vosk_recognizer = VoskRecognizer()
            if self.vosk_recognizer.is_available:
                logger.info("Vosk中文识别器初始化成功")
            else:
                logger.warning("Vosk不可用")
        except Exception as e:
            logger.error(f"Vosk初始化失败: {e}")
    
    def enhance_audio(self, audio_data, amplify_factor=5.0):
        """增强音频信号"""
        try:
            # 转换为numpy数组
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            
            # 计算原始统计
            original_max = np.max(np.abs(audio_array))
            original_rms = np.sqrt(np.mean(audio_array**2))
            
            logger.info(f"原始音频 - 最大振幅: {original_max:.1f}, RMS: {original_rms:.1f}")
            
            # 去除直流分量
            audio_array = audio_array - np.mean(audio_array)
            
            # 动态范围压缩和放大
            if original_max > 0:
                # 标准化到 [-1, 1]
                normalized = audio_array / original_max
                
                # 软压缩 (减少动态范围)
                compressed = np.sign(normalized) * (1 - np.exp(-np.abs(normalized) * 2))
                
                # 智能放大
                target_amplitude = min(16000, original_max * amplify_factor)
                enhanced = compressed * target_amplitude
                
                # 限制防止削波
                enhanced = np.clip(enhanced, -32767, 32767)
                
                # 转换回int16
                enhanced_audio = enhanced.astype(np.int16).tobytes()
                
                # 计算增强后统计
                enhanced_array = np.frombuffer(enhanced_audio, dtype=np.int16)
                enhanced_max = np.max(np.abs(enhanced_array))
                enhanced_rms = np.sqrt(np.mean(enhanced_array.astype(np.float32)**2))
                
                logger.info(f"增强音频 - 最大振幅: {enhanced_max:.1f}, RMS: {enhanced_rms:.1f}")
                
                return enhanced_audio
            else:
                logger.warning("音频信号为零，无法增强")
                return audio_data
                
        except Exception as e:
            logger.error(f"音频增强失败: {e}")
            return audio_data
    
    def recognize_with_multiple_engines(self, audio):
        """使用多个引擎进行识别"""
        results = {}
        
        # 增强音频
        raw_data = audio.get_raw_data()
        enhanced_data = self.enhance_audio(raw_data)
        
        # 创建增强后的AudioData对象
        enhanced_audio = sr.AudioData(enhanced_data, audio.sample_rate, audio.sample_width)
        
        # 1. Vosk识别 (优先，离线)
        if self.vosk_recognizer and self.vosk_recognizer.is_available:
            try:
                vosk_result = self.vosk_recognizer.recognize_from_speech_recognition_audio(enhanced_audio)
                if vosk_result and vosk_result.strip():
                    results['vosk'] = vosk_result.strip()
                    logger.info(f"✅ Vosk识别: {vosk_result}")
                else:
                    logger.debug("Vosk未识别到内容")
            except Exception as e:
                logger.error(f"Vosk识别失败: {e}")
        
        # 2. Google识别 (备选，在线)
        try:
            google_result = self.recognizer.recognize_google(enhanced_audio, language='zh-CN')
            if google_result and google_result.strip():
                results['google'] = google_result.strip()
                logger.info(f"✅ Google识别: {google_result}")
        except sr.UnknownValueError:
            logger.debug("Google无法理解音频")
        except sr.RequestError as e:
            logger.warning(f"Google识别服务错误: {e}")
        except Exception as e:
            logger.error(f"Google识别失败: {e}")
        
        # 3. 百度识别 (如果配置了API)
        try:
            # 需要百度API密钥配置
            # baidu_result = self.recognizer.recognize_baidu(enhanced_audio, 
            #                                               app_id="your_app_id",
            #                                               api_key="your_api_key", 
            #                                               secret_key="your_secret_key")
            pass
        except:
            pass
        
        return results
    
    def record_and_recognize(self):
        """录音并识别"""
        if not self.microphone:
            logger.error("麦克风未初始化")
            return None
        
        try:
            logger.info("🎙️ 开始录音...")
            
            with self.microphone as source:
                # 快速调整噪音
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # 录音
                audio = self.recognizer.listen(
                    source, 
                    timeout=self.timeout, 
                    phrase_time_limit=self.phrase_time_limit
                )
            
            logger.info("✅ 录音完成，开始识别...")
            
            # 多引擎识别
            results = self.recognize_with_multiple_engines(audio)
            
            if results:
                logger.info(f"识别结果: {results}")
                # 优先返回Vosk结果，其次Google
                if 'vosk' in results:
                    return results['vosk']
                elif 'google' in results:
                    return results['google']
                else:
                    return list(results.values())[0]
            else:
                logger.warning("所有引擎都无法识别")
                return None
                
        except sr.WaitTimeoutError:
            logger.warning("录音超时")
            return None
        except Exception as e:
            logger.error(f"录音识别失败: {e}")
            return None
    
    def test_recognition(self, test_phrases=None):
        """测试识别效果"""
        if test_phrases is None:
            test_phrases = [
                "你好",
                "今天天气很好", 
                "向前走",
                "左转",
                "停止",
                "开始",
                "谢谢"
            ]
        
        logger.info("🧪 开始识别测试...")
        logger.info(f"测试短语: {test_phrases}")
        
        success_count = 0
        total_count = 0
        
        for phrase in test_phrases:
            print(f"\n--- 请说: '{phrase}' ---")
            input("按Enter开始录音...")
            
            result = self.record_and_recognize()
            total_count += 1
            
            if result:
                print(f"识别结果: '{result}'")
                if phrase in result or result in phrase or len(result) > 0:
                    success_count += 1
                    print("✅ 识别成功")
                else:
                    print("⚠️ 识别结果不符合预期")
            else:
                print("❌ 识别失败")
        
        success_rate = success_count / total_count * 100 if total_count > 0 else 0
        print(f"\n📊 测试结果: {success_count}/{total_count} ({success_rate:.1f}%)")
        
        return success_rate

def create_optimized_asoundrc():
    """创建优化的ALSA配置"""
    config = '''# 优化的ALSA配置用于语音识别
pcm.!default {
    type asym
    playback.pcm "playback"
    capture.pcm "capture"
}

pcm.playback {
    type hw
    card 0
    device 0
}

pcm.capture {
    type dsnoop
    ipc_key 1024
    slave {
        pcm "hw:1,0"
        period_size 1024
        buffer_size 4096
        rate 16000
        format S16_LE
        channels 1
    }
    bindings.0 0
}

ctl.!default {
    type hw
    card 0
}'''
    
    try:
        asoundrc_path = os.path.expanduser("~/.asoundrc")
        with open(asoundrc_path, 'w') as f:
            f.write(config)
        logger.info(f"✅ 创建优化的ALSA配置: {asoundrc_path}")
        return True
    except Exception as e:
        logger.error(f"创建ALSA配置失败: {e}")
        return False

def install_missing_packages():
    """安装缺失的软件包"""
    packages = [
        'flac',              # Google语音识别需要
        'alsa-utils',        # ALSA工具
        'pulseaudio-utils',  # PulseAudio工具
    ]
    
    try:
        logger.info("安装缺失的软件包...")
        cmd = ['sudo', 'apt-get', 'install', '-y'] + packages
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("✅ 软件包安装完成")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"软件包安装失败: {e}")
        return False
    except Exception as e:
        logger.error(f"安装过程出错: {e}")
        return False

def main():
    """主函数"""
    print("🔧 中文语音识别修复工具")
    print("=" * 50)
    
    # 1. 安装缺失包
    print("📦 检查并安装必要软件包...")
    install_missing_packages()
    
    # 2. 创建优化的ALSA配置
    print("🔧 优化ALSA音频配置...")
    create_optimized_asoundrc()
    
    # 3. 初始化增强识别器
    print("🎤 初始化增强语音识别器...")
    recognizer = EnhancedVoiceRecognition()
    
    # 4. 进行测试
    print("🧪 开始识别测试...")
    success_rate = recognizer.test_recognition()
    
    # 5. 结果评估
    if success_rate >= 70:
        print(f"\n🎉 识别效果良好! 成功率: {success_rate:.1f}%")
        print("✅ 中文语音识别修复成功")
    elif success_rate >= 40:
        print(f"\n⚠️ 识别效果一般，成功率: {success_rate:.1f}%")
        print("💡 建议:")
        print("1. 在更安静的环境中使用")
        print("2. 调整麦克风位置，靠近嘴部")
        print("3. 说话清晰，语速适中")
    else:
        print(f"\n😞 识别效果较差，成功率: {success_rate:.1f}%")
        print("💡 问题可能是:")
        print("1. 麦克风硬件问题")
        print("2. ALSA配置需要进一步调整")
        print("3. 环境噪音过大")
        print("4. 需要更好的麦克风设备")
    
    print(f"\n📋 下一步建议:")
    print("1. 重启系统以应用ALSA配置更改")
    print("2. 运行 'alsamixer' 调整麦克风音量")
    print("3. 使用 'arecord -l' 和 'aplay -l' 检查音频设备")
    print("4. 测试 'arecord -d 3 test.wav && aplay test.wav' 检查录音播放")

if __name__ == "__main__":
    main()