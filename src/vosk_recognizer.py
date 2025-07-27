#!/usr/bin/python3
"""
Vosk语音识别模块 - 支持中文离线语音识别
"""

import json
import logging
import os
import wave
import pyaudio
from typing import Optional, Dict, Any
import threading
import time

logger = logging.getLogger(__name__)

class VoskRecognizer:
    """Vosk语音识别器"""
    
    def __init__(self, model_path: str = None, sample_rate: int = 16000):
        """
        初始化Vosk识别器
        Args:
            model_path: Vosk模型路径
            sample_rate: 采样率
        """
        self.sample_rate = sample_rate
        self.model = None
        self.recognizer = None
        self.is_available = False
        
        # 尝试导入Vosk
        try:
            import vosk
            self.vosk = vosk
            logger.info("Vosk库导入成功")
        except ImportError:
            logger.warning("Vosk库未安装，请运行: pip install vosk")
            return
        
        # 设置模型路径
        if model_path is None:
            model_path = self._find_chinese_model()
        
        if model_path and os.path.exists(model_path):
            self._initialize_model(model_path)
        else:
            logger.warning("未找到Vosk中文模型，请下载模型文件")
            self._show_model_download_instructions()
    
    def _find_chinese_model(self) -> Optional[str]:
        """查找中文模型"""
        possible_paths = [
            "models/vosk-model-small-cn-0.22",
            "models/vosk-model-cn-0.22", 
            "../models/vosk-model-small-cn-0.22",
            "../models/vosk-model-cn-0.22",
            "/opt/vosk-models/vosk-model-small-cn-0.22",
            "/opt/vosk-models/vosk-model-cn-0.22",
            os.path.expanduser("~/vosk-models/vosk-model-small-cn-0.22"),
            os.path.expanduser("~/vosk-models/vosk-model-cn-0.22")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"找到Vosk中文模型: {path}")
                return path
        
        return None
    
    def _initialize_model(self, model_path: str):
        """初始化模型"""
        try:
            # 设置日志级别（减少Vosk的输出）
            self.vosk.SetLogLevel(-1)
            
            # 加载模型
            self.model = self.vosk.Model(model_path)
            self.recognizer = self.vosk.KaldiRecognizer(self.model, self.sample_rate)
            
            # 设置识别器配置
            self.recognizer.SetWords(True)
            self.recognizer.SetPartialWords(True)
            
            self.is_available = True
            logger.info(f"Vosk模型初始化成功: {model_path}")
            
        except Exception as e:
            logger.error(f"Vosk模型初始化失败: {e}")
            self.is_available = False
    
    def _show_model_download_instructions(self):
        """显示模型下载说明"""
        logger.info("=" * 50)
        logger.info("Vosk中文模型下载说明:")
        logger.info("1. 创建模型目录: mkdir -p models")
        logger.info("2. 下载小型中文模型 (约40MB):")
        logger.info("   wget https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip")
        logger.info("3. 解压模型:")
        logger.info("   unzip vosk-model-small-cn-0.22.zip -d models/")
        logger.info("4. 或者下载完整中文模型 (约1.2GB):")
        logger.info("   wget https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip")
        logger.info("=" * 50)
    
    def recognize_from_audio_data(self, audio_data: bytes) -> Optional[str]:
        """
        从音频数据识别语音
        Args:
            audio_data: 音频数据 (16-bit PCM)
        Returns:
            识别结果文本
        """
        if not self.is_available:
            return None
        
        try:
            # 重置识别器
            self.recognizer.Reset()
            
            # 处理音频数据
            if self.recognizer.AcceptWaveform(audio_data):
                result = json.loads(self.recognizer.Result())
                text = result.get('text', '').strip()
                if text:
                    logger.info(f"Vosk识别结果: {text}")
                    return text
            
            # 获取部分结果
            partial_result = json.loads(self.recognizer.PartialResult())
            partial_text = partial_result.get('partial', '').strip()
            if partial_text:
                logger.debug(f"Vosk部分识别: {partial_text}")
                return partial_text
            
            return None
            
        except Exception as e:
            logger.error(f"Vosk识别失败: {e}")
            return None
    
    def recognize_from_speech_recognition_audio(self, sr_audio) -> Optional[str]:
        """
        从SpeechRecognition的AudioData对象识别
        Args:
            sr_audio: speech_recognition.AudioData对象
        Returns:
            识别结果文本
        """
        if not self.is_available:
            logger.debug("Vosk不可用，跳过识别")
            return None
        
        try:
            logger.debug("🎤 Vosk开始处理音频数据...")
            
            # 获取音频数据
            audio_data = sr_audio.get_raw_data()
            logger.debug(f"音频数据长度: {len(audio_data)} 字节")
            
            # 确保采样率匹配
            if sr_audio.sample_rate != self.sample_rate:
                logger.warning(f"采样率不匹配: {sr_audio.sample_rate} != {self.sample_rate}")
            
            result = self.recognize_from_audio_data(audio_data)
            if result:
                logger.debug(f"🎯 Vosk识别原始结果: '{result}'")
            else:
                logger.debug("🔇 Vosk未识别到内容")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Vosk从SpeechRecognition音频识别失败: {e}")
            return None
    
    def create_stream_recognizer(self):
        """创建流式识别器"""
        if not self.is_available:
            return None
        
        return VoskStreamRecognizer(self.model, self.sample_rate)

class VoskStreamRecognizer:
    """Vosk流式识别器 - 用于实时语音识别"""
    
    def __init__(self, model, sample_rate: int = 16000):
        """
        初始化流式识别器
        Args:
            model: Vosk模型
            sample_rate: 采样率
        """
        import vosk
        self.model = model
        self.sample_rate = sample_rate
        self.recognizer = vosk.KaldiRecognizer(model, sample_rate)
        self.recognizer.SetWords(True)
        
        self.is_listening = False
        self.audio_stream = None
        self.recognition_callback = None
        self.partial_callback = None
        
    def start_stream_recognition(self, 
                               recognition_callback=None, 
                               partial_callback=None):
        """
        开始流式识别
        Args:
            recognition_callback: 完整识别结果回调
            partial_callback: 部分识别结果回调
        """
        self.recognition_callback = recognition_callback
        self.partial_callback = partial_callback
        self.is_listening = True
        
        try:
            # 初始化音频流
            pa = pyaudio.PyAudio()
            self.audio_stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=4096
            )
            
            # 启动识别线程
            recognition_thread = threading.Thread(
                target=self._stream_recognition_worker, 
                daemon=True
            )
            recognition_thread.start()
            
            logger.info("Vosk流式识别已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动流式识别失败: {e}")
            return False
    
    def stop_stream_recognition(self):
        """停止流式识别"""
        self.is_listening = False
        
        if self.audio_stream:
            self.audio_stream.close()
            self.audio_stream = None
        
        logger.info("Vosk流式识别已停止")
    
    def _stream_recognition_worker(self):
        """流式识别工作线程"""
        logger.info("Vosk流式识别线程启动")
        
        while self.is_listening and self.audio_stream:
            try:
                # 读取音频数据
                data = self.audio_stream.read(4096, exception_on_overflow=False)
                
                # 处理音频
                if self.recognizer.AcceptWaveform(data):
                    # 完整识别结果
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').strip()
                    
                    if text and self.recognition_callback:
                        self.recognition_callback(text)
                else:
                    # 部分识别结果
                    partial_result = json.loads(self.recognizer.PartialResult())
                    partial_text = partial_result.get('partial', '').strip()
                    
                    if partial_text and self.partial_callback:
                        self.partial_callback(partial_text)
                
            except Exception as e:
                logger.error(f"流式识别错误: {e}")
                time.sleep(0.1)
        
        logger.info("Vosk流式识别线程结束")

# 测试函数
def test_vosk_recognizer():
    """测试Vosk识别器"""
    print("=== Vosk语音识别测试 ===")
    
    recognizer = VoskRecognizer()
    
    if not recognizer.is_available:
        print("❌ Vosk不可用")
        return False
    
    print("✅ Vosk初始化成功")
    
    # 测试流式识别
    stream_recognizer = recognizer.create_stream_recognizer()
    
    if stream_recognizer:
        print("✅ 流式识别器创建成功")
        
        def on_recognition(text):
            print(f"🎤 识别结果: {text}")
        
        def on_partial(text):
            print(f"🔄 部分结果: {text}")
        
        try:
            if stream_recognizer.start_stream_recognition(on_recognition, on_partial):
                print("🎙️ 开始说话测试，按Ctrl+C停止...")
                
                # 保持运行
                while True:
                    time.sleep(1)
            else:
                print("❌ 流式识别启动失败")
                
        except KeyboardInterrupt:
            print("\n正在停止...")
            stream_recognizer.stop_stream_recognition()
            print("测试结束")
    
    return True

if __name__ == "__main__":
    test_vosk_recognizer()