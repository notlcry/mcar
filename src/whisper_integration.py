#!/usr/bin/python3
"""
Whisper语音识别集成模块
提供本地语音识别功能，支持中文识别
"""

import whisper
import tempfile
import wave
import struct
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

class WhisperRecognizer:
    def __init__(self, model_size="base"):
        """
        初始化Whisper识别器
        Args:
            model_size: 模型大小 ("tiny", "base", "small", "medium", "large")
        """
        self.model_size = model_size
        self.model = None
        self.load_model()
    
    def load_model(self):
        """加载Whisper模型"""
        try:
            logger.info(f"正在加载Whisper {self.model_size} 模型...")
            self.model = whisper.load_model(self.model_size)
            logger.info("Whisper模型加载成功")
        except Exception as e:
            logger.error(f"Whisper模型加载失败: {e}")
            self.model = None
    
    def recognize_audio_data(self, audio_data, sample_rate=16000):
        """
        识别音频数据
        Args:
            audio_data: 音频数据列表
            sample_rate: 采样率
        Returns:
            识别的文本，失败返回None
        """
        if not self.model:
            logger.error("Whisper模型未加载")
            return None
        
        try:
            # 创建临时WAV文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                # 写入WAV文件
                with wave.open(temp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # 单声道
                    wav_file.setsampwidth(2)  # 16位
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(struct.pack('<' + 'h' * len(audio_data), *audio_data))
                
                # 使用Whisper识别
                result = self.model.transcribe(
                    temp_file.name,
                    language='zh',  # 指定中文
                    task='transcribe'
                )
                
                # 清理临时文件
                os.unlink(temp_file.name)
                
                # 返回识别结果
                text = result['text'].strip()
                if text:
                    logger.info(f"Whisper识别结果: {text}")
                    return text
                else:
                    logger.debug("Whisper未识别到有效文本")
                    return None
                    
        except Exception as e:
            logger.error(f"Whisper语音识别失败: {e}")
            return None
    
    def recognize_audio_file(self, audio_file_path):
        """
        识别音频文件
        Args:
            audio_file_path: 音频文件路径
        Returns:
            识别的文本，失败返回None
        """
        if not self.model:
            logger.error("Whisper模型未加载")
            return None
        
        try:
            result = self.model.transcribe(
                audio_file_path,
                language='zh',
                task='transcribe'
            )
            
            text = result['text'].strip()
            if text:
                logger.info(f"Whisper识别结果: {text}")
                return text
            else:
                logger.debug("Whisper未识别到有效文本")
                return None
                
        except Exception as e:
            logger.error(f"Whisper文件识别失败: {e}")
            return None


# 全局Whisper实例
_whisper_recognizer = None

def get_whisper_recognizer(model_size="base"):
    """获取全局Whisper识别器实例"""
    global _whisper_recognizer
    if _whisper_recognizer is None:
        _whisper_recognizer = WhisperRecognizer(model_size)
    return _whisper_recognizer


def test_whisper():
    """测试Whisper识别功能"""
    print("====== Whisper语音识别测试 ======")
    
    recognizer = get_whisper_recognizer("tiny")  # 使用最小模型进行测试
    
    if recognizer.model:
        print("Whisper模型加载成功！")
        print("可以开始语音识别了")
    else:
        print("Whisper模型加载失败")
    
    print("=" * 40)


if __name__ == "__main__":
    test_whisper()