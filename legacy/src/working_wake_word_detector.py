#!/usr/bin/python3
"""
工作版唤醒词检测器 - 基于成功测试的简化版本
用于集成到主语音控制系统
"""

import pvporcupine
import pyaudio
import numpy as np
import time
import os
import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class WorkingWakeWordDetector:
    """基于成功测试的唤醒词检测器"""
    
    def __init__(self, access_key=None, sensitivity=0.9):
        self.access_key = access_key or os.getenv('PICOVOICE_ACCESS_KEY')
        self.sensitivity = sensitivity
        self.porcupine = None
        self.audio_stream = None
        self.pa = None
        self.is_listening = False
        self.callback = None
        self.thread = None
        
        # 查找唤醒词文件
        self.wake_word_file = None
        for path in ["../wake_words/kk_zh_raspberry-pi_v3_0_0.ppn", 
                     "wake_words/kk_zh_raspberry-pi_v3_0_0.ppn",
                     "/home/barry/mcar/wake_words/kk_zh_raspberry-pi_v3_0_0.ppn"]:
            if os.path.exists(path):
                self.wake_word_file = path
                break
        
        # 查找中文模型
        self.model_file = None
        for path in ["../wake_words/porcupine_params_zh.pv", 
                     "wake_words/porcupine_params_zh.pv",
                     "/home/barry/mcar/wake_words/porcupine_params_zh.pv"]:
            if os.path.exists(path):
                self.model_file = path
                break
    
    def initialize(self):
        """初始化检测器"""
        if not self.access_key:
            logger.error("未找到PICOVOICE_ACCESS_KEY")
            return False
        
        if not self.wake_word_file:
            logger.error("未找到唤醒词文件")
            return False
        
        try:
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keyword_paths=[self.wake_word_file],
                sensitivities=[self.sensitivity],
                model_path=self.model_file
            )
            logger.info(f"✅ Porcupine初始化成功，灵敏度: {self.sensitivity}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Porcupine初始化失败: {e}")
            return False
    
    def _find_audio_device(self):
        """查找可用的音频输入设备"""
        try:
            self.pa = pyaudio.PyAudio()
            
            # 先尝试使用设备1（通常是USB音频设备）
            try:
                info = self.pa.get_device_info_by_index(1)
                if info['maxInputChannels'] > 0:
                    logger.info(f"使用设备1: {info['name']}")
                    return 1, info
            except:
                pass
            
            # 使用默认输入设备
            try:
                device_index = self.pa.get_default_input_device_info()['index']
                device_info = self.pa.get_default_input_device_info()
                logger.info(f"使用默认设备: {device_info['name']}")
                return device_index, device_info
            except:
                pass
                
            logger.error("无法找到音频输入设备")
            return None, None
            
        except Exception as e:
            logger.error(f"音频设备查找失败: {e}")
            return None, None
    
    def _audio_callback(self):
        """音频处理回调"""
        device_index, device_info = self._find_audio_device()
        
        if device_index is None:
            logger.error("无法启动音频流")
            return
        
        try:
            # 使用简单的音频配置（基于成功的测试）
            sample_rate = 16000
            channels = 1
            format = pyaudio.paInt16
            frames_per_buffer = self.porcupine.frame_length
            
            self.audio_stream = self.pa.open(
                format=format,
                channels=channels,
                rate=sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=frames_per_buffer,
                start=False
            )
            
            self.audio_stream.start_stream()
            logger.info("✅ 音频流启动成功，开始监听唤醒词...")
            
            frames_processed = 0
            detection_count = 0
            
            while self.is_listening:
                try:
                    # 读取音频数据
                    audio_frame = self.audio_stream.read(frames_per_buffer, exception_on_overflow=False)
                    audio_data = np.frombuffer(audio_frame, dtype=np.int16)
                    
                    # 确保数据长度正确
                    if len(audio_data) >= self.porcupine.frame_length:
                        audio_data = audio_data[:self.porcupine.frame_length]
                        
                        # 唤醒词检测
                        keyword_index = self.porcupine.process(audio_data)
                        
                        if keyword_index >= 0:
                            detection_count += 1
                            logger.info(f"🎉 检测到唤醒词'快快'! (第{detection_count}次)")
                            
                            if self.callback:
                                self.callback(keyword_index)
                    
                    frames_processed += 1
                    
                    # 每1000帧显示一次状态（约32秒）
                    if frames_processed % 1000 == 0:
                        logger.debug(f"已处理 {frames_processed} 帧，检测到 {detection_count} 次唤醒词")
                
                except Exception as e:
                    logger.warning(f"音频处理错误: {e}")
                    time.sleep(0.01)
                    continue
        
        except Exception as e:
            logger.error(f"音频流启动失败: {e}")
        
        finally:
            self._cleanup_audio()
    
    def _cleanup_audio(self):
        """清理音频资源"""
        try:
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
                self.audio_stream = None
            
            if self.pa:
                self.pa.terminate()
                self.pa = None
                
        except Exception as e:
            logger.warning(f"音频资源清理错误: {e}")
    
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
        
        # 在单独线程中运行音频处理
        self.thread = threading.Thread(target=self._audio_callback, daemon=True)
        self.thread.start()
        
        logger.info("✅ 唤醒词监听已启动")
        return True
    
    def stop_listening(self):
        """停止监听"""
        self.is_listening = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)
        
        self._cleanup_audio()
        logger.info("⏹️ 唤醒词监听已停止")
    
    def __del__(self):
        """清理资源"""
        self.stop_listening()
        
        if self.porcupine:
            try:
                self.porcupine.delete()
            except:
                pass

# 测试函数
def test_working_detector():
    """测试工作版检测器"""
    print("🔧 测试工作版唤醒词检测器")
    print("=" * 35)
    
    detector = WorkingWakeWordDetector(sensitivity=0.9)
    
    if not detector.initialize():
        print("❌ 初始化失败")
        return
    
    def on_wake_word(keyword_index):
        print(f"🎉 检测到唤醒词! 时间: {time.strftime('%H:%M:%S')}")
    
    print("🎯 开始监听...")
    print("💡 请说'快快'")
    print("⌨️ 按Ctrl+C停止\n")
    
    try:
        detector.start_listening(on_wake_word)
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ 停止测试")
        detector.stop_listening()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    test_working_detector()