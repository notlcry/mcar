#!/usr/bin/python3
"""
修复版唤醒词检测器 - 针对ReSpeaker 2-Mics兼容性和灵敏度优化
解决音频预处理和DC偏移问题
"""

import pvporcupine
import pyaudio
import struct
import threading
import time
import logging
import os
import numpy as np
from scipy import signal
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class FixedWakeWordDetector:
    """修复版唤醒词检测器"""
    
    def __init__(self, access_key=None, keyword_paths=None, sensitivities=None):
        self.access_key = access_key or os.getenv('PICOVOICE_ACCESS_KEY')
        
        # 中文唤醒词优化配置
        if keyword_paths:
            valid_paths = [path for path in keyword_paths if os.path.exists(path)]
            if valid_paths and self.access_key:
                self.keyword_paths = valid_paths
                self.keywords = None
                # 提高中文唤醒词的灵敏度
                self.sensitivities = sensitivities or [0.8] * len(valid_paths)  # 从0.5提高到0.8
                logger.info(f"使用 {len(valid_paths)} 个自定义唤醒词，灵敏度: {self.sensitivities}")
            else:
                logger.warning("自定义唤醒词文件无效或访问密钥未配置")
                self.keyword_paths = None
                self.keywords = ["computer"]
                self.sensitivities = [0.8]
        else:
            self.keywords = ["computer"]
            self.sensitivities = [0.8]
        
        self.porcupine = None
        self.audio_stream = None
        self.is_listening = False
        self.callback = None
        self.continuous_errors = 0
        self.max_errors = 10
        self.thread = None
        
        # ReSpeaker 2-Mics优化音频配置
        self.respeaker_config = {
            'sample_rate': 48000,  # ReSpeaker原生采样率
            'channels': 2,         # 立体声
            'format': pyaudio.paInt16,
            'chunk_size': 1024,    # 减小缓冲区以提高响应速度
            'device_index': None
        }
        
        # DC偏移校正参数
        self.dc_offset_correction = True
        self.high_pass_cutoff = 80  # Hz，移除低频噪音
        
    def _find_audio_device(self):
        """智能查找音频设备"""
        try:
            pa = pyaudio.PyAudio()
            device_count = pa.get_device_count()
            
            # 优先查找ReSpeaker设备
            for i in range(device_count):
                try:
                    info = pa.get_device_info_by_index(i)
                    name = info['name'].lower()
                    
                    # ReSpeaker设备识别
                    if any(keyword in name for keyword in ['respeaker', 'seeed', 'usb audio']):
                        if info['maxInputChannels'] >= 2:
                            logger.info(f"找到ReSpeaker设备: {info['name']}")
                            pa.terminate()
                            return i, info
                except:
                    continue
            
            # 备选：查找任何可用的双声道输入设备
            for i in range(device_count):
                try:
                    info = pa.get_device_info_by_index(i)
                    if info['maxInputChannels'] >= 2:
                        logger.info(f"使用备选音频设备: {info['name']}")
                        pa.terminate()
                        return i, info
                except:
                    continue
            
            # 最后选择：任何输入设备
            for i in range(device_count):
                try:
                    info = pa.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        logger.warning(f"使用单声道设备: {info['name']}")
                        pa.terminate()
                        return i, info
                except:
                    continue
                    
            pa.terminate()
            
        except Exception as e:
            logger.error(f"音频设备检测失败: {e}")
            
        return None, None
    
    def _apply_dc_offset_correction(self, audio_data):
        """DC偏移校正和高通滤波"""
        if not self.dc_offset_correction:
            return audio_data
            
        try:
            # 移除DC偏移
            audio_data = audio_data - np.mean(audio_data)
            
            # 高通滤波移除低频噪音
            if len(audio_data) > 100:  # 确保有足够的样本
                nyquist = 16000 / 2
                normalized_cutoff = self.high_pass_cutoff / nyquist
                
                if normalized_cutoff < 0.99:  # 确保截止频率有效
                    b, a = signal.butter(2, normalized_cutoff, btype='high')
                    audio_data = signal.filtfilt(b, a, audio_data)
            
            return audio_data.astype(np.int16)
            
        except Exception as e:
            logger.warning(f"音频预处理失败: {e}")
            return audio_data
    
    def _resample_audio(self, audio_data, original_rate, target_rate):
        """智能音频重采样"""
        if original_rate == target_rate:
            return audio_data
            
        try:
            # 计算重采样比例
            num_samples = int(len(audio_data) * target_rate / original_rate)
            
            # 使用scipy高质量重采样
            resampled = signal.resample(audio_data, num_samples)
            
            # 确保数据类型正确
            return resampled.astype(np.int16)
            
        except Exception as e:
            logger.error(f"音频重采样失败: {e}")
            return audio_data
    
    def initialize(self):
        """初始化检测器"""
        try:
            # 查找合适的中文语言模型
            model_path = None
            current_dir = os.path.dirname(os.path.abspath(__file__))
            possible_paths = [
                os.path.join(current_dir, "../wake_words/porcupine_params_zh.pv"),
                os.path.join(current_dir, "wake_words/porcupine_params_zh.pv"),
                "wake_words/porcupine_params_zh.pv"
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    model_path = path
                    logger.info(f"使用中文语言模型: {model_path}")
                    break
            
            # 初始化Porcupine
            if self.keyword_paths and self.access_key:
                self.porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keyword_paths=self.keyword_paths,
                    sensitivities=self.sensitivities,
                    model_path=model_path
                )
                logger.info(f"✅ Porcupine初始化成功，中文唤醒词灵敏度: {self.sensitivities}")
            else:
                self.porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keywords=self.keywords,
                    sensitivities=self.sensitivities,
                    model_path=model_path
                )
                logger.info(f"✅ Porcupine初始化成功，内置唤醒词: {self.keywords}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Porcupine初始化失败: {e}")
            return False
    
    def _audio_callback(self):
        """优化的音频处理回调"""
        device_index, device_info = self._find_audio_device()
        
        if device_index is None:
            logger.error("❌ 未找到可用的音频输入设备")
            return
        
        # 根据设备调整配置
        sample_rate = int(device_info.get('defaultSampleRate', 16000))
        channels = min(device_info['maxInputChannels'], 2)
        
        logger.info(f"🎤 使用设备: {device_info['name']}")
        logger.info(f"📊 音频配置: {sample_rate}Hz, {channels}声道")
        
        try:
            pa = pyaudio.PyAudio()
            
            # 计算合适的缓冲区大小
            frames_per_buffer = int(sample_rate * 0.032)  # 32ms缓冲区
            
            self.audio_stream = pa.open(
                rate=sample_rate,
                channels=channels,
                format=pyaudio.paInt16,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=frames_per_buffer
            )
            
            logger.info("🎯 开始唤醒词监听...")
            
            while self.is_listening:
                try:
                    # 读取音频数据
                    audio_frame = self.audio_stream.read(frames_per_buffer, exception_on_overflow=False)
                    audio_data = np.frombuffer(audio_frame, dtype=np.int16)
                    
                    # 双声道转单声道
                    if channels == 2:
                        audio_data = audio_data[0::2]  # 取左声道
                    
                    # 重采样到16kHz
                    if sample_rate != 16000:
                        audio_data = self._resample_audio(audio_data, sample_rate, 16000)
                    
                    # DC偏移校正和滤波
                    audio_data = self._apply_dc_offset_correction(audio_data)
                    
                    # 确保数据长度正确
                    required_length = self.porcupine.frame_length
                    if len(audio_data) >= required_length:
                        audio_data = audio_data[:required_length]
                        
                        # 唤醒词检测
                        keyword_index = self.porcupine.process(audio_data)
                        
                        if keyword_index >= 0 and self.callback:
                            logger.info(f"🎉 检测到唤醒词! 索引: {keyword_index}")
                            self.callback(keyword_index)
                        
                        # 重置错误计数
                        self.continuous_errors = 0
                    
                except Exception as e:
                    self.continuous_errors += 1
                    if self.continuous_errors <= 3:  # 只记录前几次错误
                        logger.warning(f"音频处理错误 ({self.continuous_errors}): {e}")
                    
                    if self.continuous_errors >= self.max_errors:
                        logger.error("连续音频错误过多，停止监听")
                        break
                    
                    time.sleep(0.01)  # 短暂延迟后继续
        
        except Exception as e:
            logger.error(f"音频流初始化失败: {e}")
        
        finally:
            if hasattr(self, 'audio_stream') and self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            if 'pa' in locals():
                pa.terminate()
    
    def start_listening(self, callback: Callable[[int], None]):
        """开始监听唤醒词"""
        if self.is_listening:
            logger.warning("已经在监听中")
            return False
        
        if not self.porcupine:
            logger.error("检测器未初始化")
            return False
        
        self.callback = callback
        self.is_listening = True
        self.continuous_errors = 0
        
        # 在单独线程中运行音频处理
        self.thread = threading.Thread(target=self._audio_callback, daemon=True)
        self.thread.start()
        
        logger.info("✅ 唤醒词监听已启动")
        return True
    
    def stop_listening(self):
        """停止监听"""
        self.is_listening = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        logger.info("⏹️ 唤醒词监听已停止")
    
    def __del__(self):
        """清理资源"""
        self.stop_listening()
        if self.porcupine:
            self.porcupine.delete()

# 测试函数
def test_fixed_wake_word():
    """测试修复版唤醒词检测"""
    import os
    
    print("🔧 修复版唤醒词检测测试")
    print("=" * 40)
    
    # 查找唤醒词文件
    wake_word_files = []
    for root in ["../wake_words", "wake_words", "."]:
        if os.path.exists(root):
            for file in os.listdir(root):
                if file.endswith('.ppn'):
                    wake_word_files.append(os.path.join(root, file))
    
    if not wake_word_files:
        print("❌ 未找到唤醒词文件")
        return
    
    print(f"✅ 找到唤醒词文件: {len(wake_word_files)}个")
    for file in wake_word_files:
        print(f"   - {file}")
    
    # 初始化检测器
    detector = FixedWakeWordDetector(
        keyword_paths=wake_word_files,
        sensitivities=[0.8] * len(wake_word_files)  # 高灵敏度
    )
    
    if not detector.initialize():
        print("❌ 检测器初始化失败")
        return
    
    # 开始检测
    def on_detection(keyword_index):
        print(f"🎉 检测到唤醒词! 文件: {wake_word_files[keyword_index]}")
        print(f"📅 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n🎯 开始监听唤醒词...")
    print("💡 请说出'快快'来测试")
    print("⌨️ 按Ctrl+C停止测试\n")
    
    try:
        detector.start_listening(on_detection)
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ 停止测试")
        detector.stop_listening()

if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    test_fixed_wake_word()