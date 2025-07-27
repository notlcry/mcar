#!/usr/bin/python3
"""
唤醒词检测模块 - 使用Porcupine进行"喵喵小车"唤醒词检测
支持自定义唤醒词和灵敏度调节
"""

import pvporcupine
import pyaudio
import struct
import threading
import time
import logging
import os
from typing import Callable, Optional

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WakeWordDetector:
    """唤醒词检测器"""
    
    def __init__(self, access_key=None, keyword_paths=None, sensitivities=None):
        """
        初始化唤醒词检测器
        Args:
            access_key: Picovoice访问密钥
            keyword_paths: 自定义唤醒词文件路径列表
            sensitivities: 检测灵敏度列表 (0.0-1.0)
        """
        self.access_key = access_key or os.getenv('PICOVOICE_ACCESS_KEY')
        
        # 检查自定义唤醒词文件
        if keyword_paths:
            # 验证文件存在
            valid_paths = []
            for path in keyword_paths:
                if os.path.exists(path):
                    valid_paths.append(path)
                    logger.info(f"找到自定义唤醒词文件: {path}")
                else:
                    logger.warning(f"唤醒词文件不存在: {path}")
            
            if valid_paths and self.access_key and self.access_key != 'your_picovoice_access_key_here':
                self.keyword_paths = valid_paths
                self.keywords = None
                logger.info(f"将使用 {len(valid_paths)} 个自定义唤醒词")
            else:
                logger.warning("自定义唤醒词配置无效，使用内置关键词")
                self.keyword_paths = None
                self.keywords = ['picovoice']
        else:
            # 尝试自动查找自定义唤醒词
            wake_words_dir = '../wake_words'
            if os.path.exists(wake_words_dir):
                ppn_files = [os.path.join(wake_words_dir, f) for f in os.listdir(wake_words_dir) if f.endswith('.ppn')]
                if ppn_files and self.access_key and self.access_key != 'your_picovoice_access_key_here':
                    self.keyword_paths = ppn_files
                    self.keywords = None
                    logger.info(f"自动发现 {len(ppn_files)} 个自定义唤醒词文件")
                else:
                    self.keyword_paths = None
                    self.keywords = [pvporcupine.KEYWORDS['computer']]
            else:
                # 如果没有访问密钥或自定义文件，使用内置关键词
                logger.warning("未设置PICOVOICE_ACCESS_KEY或未找到自定义唤醒词，将使用内置关键词")
                self.keyword_paths = None
                self.keywords = ['picovoice']
        
        # 设置灵敏度
        if self.keyword_paths:
            self.sensitivities = sensitivities or [0.5] * len(self.keyword_paths)
        else:
            self.sensitivities = sensitivities or [0.5]
        
        # Porcupine实例
        self.porcupine = None
        self.audio_stream = None
        
        # 检测状态
        self.is_listening = False
        self.detection_callback = None
        
        # 线程控制
        self.detection_thread = None
        
        # 初始化Porcupine
        self._initialize_porcupine()
    
    def _initialize_porcupine(self):
        """初始化Porcupine引擎"""
        try:
            if self.access_key and self.keyword_paths:
                # 使用自定义唤醒词
                self.porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keyword_paths=self.keyword_paths,
                    sensitivities=self.sensitivities
                )
                logger.info("Porcupine初始化成功（自定义唤醒词）")
            else:
                # 使用内置关键词
                try:
                    self.porcupine = pvporcupine.create(
                        access_key=self.access_key,
                        keywords=self.keywords,
                        sensitivities=self.sensitivities
                    )
                    logger.info("Porcupine初始化成功（内置关键词: picovoice）")
                except Exception as e:
                    logger.error(f"Porcupine初始化失败: {e}")
                    self.porcupine = None
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Porcupine初始化失败: {e}")
            self.porcupine = None
            return False
    
    def start_detection(self, callback: Callable[[int], None]):
        """
        开始唤醒词检测
        Args:
            callback: 检测到唤醒词时的回调函数，参数为关键词索引
        """
        if not self.porcupine:
            logger.error("Porcupine未初始化，无法开始检测")
            return False
        
        self.detection_callback = callback
        self.is_listening = True
        
        # 初始化音频流
        try:
            pa = pyaudio.PyAudio()
            
            self.audio_stream = pa.open(
                rate=self.porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.porcupine.frame_length
            )
            
            # 启动检测线程
            self.detection_thread = threading.Thread(target=self._detection_worker, daemon=True)
            self.detection_thread.start()
            
            logger.info("唤醒词检测已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动唤醒词检测失败: {e}")
            return False
    
    def stop_detection(self):
        """停止唤醒词检测"""
        self.is_listening = False
        
        if self.audio_stream:
            self.audio_stream.close()
            self.audio_stream = None
        
        logger.info("唤醒词检测已停止")
    
    def _detection_worker(self):
        """检测工作线程"""
        logger.info("唤醒词检测线程启动")
        
        while self.is_listening:
            try:
                # 读取音频数据
                pcm = self.audio_stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                
                # 检测唤醒词
                keyword_index = self.porcupine.process(pcm)
                
                if keyword_index >= 0:
                    logger.info(f"检测到唤醒词，索引: {keyword_index}")
                    
                    # 调用回调函数
                    if self.detection_callback:
                        self.detection_callback(keyword_index)
                
            except Exception as e:
                logger.error(f"唤醒词检测错误: {e}")
                time.sleep(0.1)
        
        logger.info("唤醒词检测线程结束")
    
    def __del__(self):
        """析构函数"""
        try:
            self.stop_detection()
            
            if hasattr(self, 'porcupine') and self.porcupine:
                self.porcupine.delete()
        except:
            pass  # 忽略析构时的错误

class SimpleWakeWordDetector:
    """简单的唤醒词检测器 - 基于语音识别的备选方案"""
    
    def __init__(self, wake_words=None):
        """
        初始化简单唤醒词检测器
        Args:
            wake_words: 唤醒词列表
        """
        self.wake_words = wake_words or ["喵喵小车", "小车", "机器人"]
        self.is_listening = False
        self.detection_callback = None
        
        # 语音识别组件
        import speech_recognition as sr
        self.recognizer = sr.Recognizer()
        self.microphone = None
        
        # 初始化麦克风
        self._initialize_microphone()
    
    def _initialize_microphone(self):
        """初始化麦克风"""
        try:
            import speech_recognition as sr
            self.microphone = sr.Microphone()
            
            # 调整环境噪音
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            logger.info("简单唤醒词检测器麦克风初始化完成")
            
        except Exception as e:
            logger.error(f"麦克风初始化失败: {e}")
            self.microphone = None
    
    def start_detection(self, callback: Callable[[int], None]):
        """开始检测"""
        if not self.microphone:
            logger.error("麦克风未初始化")
            return False
        
        self.detection_callback = callback
        self.is_listening = True
        
        # 启动检测线程
        detection_thread = threading.Thread(target=self._simple_detection_worker, daemon=True)
        detection_thread.start()
        
        logger.info("简单唤醒词检测已启动")
        return True
    
    def stop_detection(self):
        """停止检测"""
        self.is_listening = False
        logger.info("简单唤醒词检测已停止")
    
    def _simple_detection_worker(self):
        """简单检测工作线程"""
        while self.is_listening:
            try:
                with self.microphone as source:
                    # 监听音频
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                
                # 识别语音
                try:
                    text = self.recognizer.recognize_sphinx(audio, language='zh-cn')
                    text = text.lower().strip()
                    
                    # 检查是否包含唤醒词
                    for i, wake_word in enumerate(self.wake_words):
                        if wake_word in text:
                            logger.info(f"检测到唤醒词: {wake_word}")
                            
                            if self.detection_callback:
                                self.detection_callback(i)
                            break
                
                except Exception:
                    # 识别失败，继续监听
                    pass
                
            except Exception as e:
                if "timeout" not in str(e).lower():
                    logger.error(f"简单唤醒词检测错误: {e}")
                time.sleep(0.1)

# 测试函数
def test_wake_word_detection():
    """测试唤醒词检测功能"""
    print("=== 唤醒词检测测试 ===")
    
    def on_wake_word_detected(keyword_index):
        print(f"检测到唤醒词！索引: {keyword_index}")
        print("可以开始对话了...")
    
    # 首先尝试Porcupine
    detector = WakeWordDetector()
    
    if detector.porcupine:
        print("使用Porcupine检测器")
        print("请说 'computer' 来测试唤醒词检测")
    else:
        print("Porcupine不可用，使用简单检测器")
        detector = SimpleWakeWordDetector()
        print("请说 '喵喵小车' 来测试唤醒词检测")
    
    try:
        if detector.start_detection(on_wake_word_detected):
            print("唤醒词检测已启动，按Ctrl+C停止")
            
            # 保持程序运行
            while True:
                time.sleep(1)
        else:
            print("唤醒词检测启动失败")
            
    except KeyboardInterrupt:
        print("\n正在停止...")
        detector.stop_detection()
        print("测试结束")

if __name__ == "__main__":
    test_wake_word_detection()