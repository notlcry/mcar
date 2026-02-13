#!/usr/bin/python3
"""
唤醒词检测模块 - 使用Porcupine进行"快快"唤醒词检测
支持自定义唤醒词和灵敏度调节
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
            wake_words_dirs = ['wake_words', '../wake_words']
            wake_words_dir = None
            
            for dir_path in wake_words_dirs:
                if os.path.exists(dir_path):
                    wake_words_dir = dir_path
                    break
            
            if wake_words_dir:
                ppn_files = [os.path.join(wake_words_dir, f) for f in os.listdir(wake_words_dir) if f.endswith('.ppn')]
                if ppn_files and self.access_key and self.access_key != 'your_picovoice_access_key_here':
                    self.keyword_paths = ppn_files
                    self.keywords = None
                    logger.info(f"自动发现 {len(ppn_files)} 个自定义唤醒词文件")
                else:
                    self.keyword_paths = None
                    # 使用内置关键词列表中的可用关键词
                    available_keywords = list(pvporcupine.KEYWORDS)
                    self.keywords = ['porcupine'] if 'porcupine' in available_keywords else [available_keywords[0]]
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
        
        # 音频参数 - 直接使用Porcupine要求的采样率
        self.target_sample_rate = 16000   # 直接使用16kHz，避免重采样问题
        
        # 初始化Porcupine
        self._initialize_porcupine()
    
    def _initialize_porcupine(self):
        """初始化Porcupine引擎"""
        try:
            if self.access_key and self.keyword_paths:
                # 检查是否是中文唤醒词
                is_chinese = any('_zh_' in path for path in self.keyword_paths)
                
                if is_chinese:
                    # 中文唤醒词需要中文模型
                    logger.info("检测到中文唤醒词，查找中文语言模型...")
                    
                    # 查找中文模型文件
                    chinese_model_paths = [
                        'models/porcupine/porcupine_params_zh.pv',
                        '../models/porcupine/porcupine_params_zh.pv',
                        'src/wake_words/porcupine_params_zh.pv',
                        'wake_words/porcupine_params_zh.pv'
                    ]
                    
                    chinese_model = None
                    for model_path in chinese_model_paths:
                        if os.path.exists(model_path):
                            chinese_model = model_path
                            break
                    
                    if chinese_model:
                        logger.info(f"找到中文模型: {chinese_model}")
                        self.porcupine = pvporcupine.create(
                            access_key=self.access_key,
                            keyword_paths=self.keyword_paths,
                            model_path=chinese_model,
                            sensitivities=self.sensitivities
                        )
                        logger.info("Porcupine初始化成功（中文唤醒词）")
                    else:
                        logger.warning("未找到中文语言模型，使用内置关键词")
                        logger.info("💡 运行 ./setup_chinese_wake_word.sh 下载中文模型")
                        self.keyword_paths = None
                        self.keywords = ['picovoice']
                        
                        self.porcupine = pvporcupine.create(
                            access_key=self.access_key,
                            keywords=self.keywords,
                            sensitivities=self.sensitivities
                        )
                        logger.info("Porcupine初始化成功（内置关键词: picovoice）")
                else:
                    # 英文自定义唤醒词
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
        
        # 尝试多种音频配置
        audio_configs = [
            # 配置1: ReSpeaker 2-Mics (48kHz, 2通道)
            {
                'name': 'ReSpeaker 2-Mics',
                'sample_rate': 48000,
                'channels': 2,
                'frames_per_buffer': 1536,  # 48000 * 512 / 16000
                'device_filter': lambda info: (
                    ('seeed' in info['name'].lower() or 'respeaker' in info['name'].lower() or 'array' in info['name'].lower()) 
                    and info['maxInputChannels'] >= 2
                )
            },
            # 配置2: 任何2通道设备 (48kHz)
            {
                'name': '2通道设备(48kHz)',
                'sample_rate': 48000,
                'channels': 2,
                'frames_per_buffer': 1536,
                'device_filter': lambda info: info['maxInputChannels'] >= 2
            },
            # 配置3: 默认设备 (16kHz, 1通道)
            {
                'name': '默认设备(16kHz)',
                'sample_rate': 16000,
                'channels': 1,
                'frames_per_buffer': 512,
                'device_filter': lambda info: info['maxInputChannels'] >= 1
            },
            # 配置4: 任何可用设备 (44.1kHz)
            {
                'name': '通用设备(44.1kHz)',
                'sample_rate': 44100,
                'channels': 1,
                'frames_per_buffer': 1411,  # 44100 * 512 / 16000
                'device_filter': lambda info: info['maxInputChannels'] >= 1
            }
        ]
        
        # 初始化音频流
        try:
            pa = pyaudio.PyAudio()
            
            # 列出所有音频设备用于调试
            logger.info("可用音频设备:")
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    logger.info(f"  设备 {i}: {info['name']} (输入通道: {info['maxInputChannels']}, 采样率: {info['defaultSampleRate']})")
            
            # 尝试不同的音频配置
            audio_stream_created = False
            for config in audio_configs:
                if audio_stream_created:
                    break
                    
                logger.info(f"尝试音频配置: {config['name']}")
                
                # 查找符合条件的设备
                device_index = None
                for i in range(pa.get_device_count()):
                    info = pa.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0 and config['device_filter'](info):
                        device_index = i
                        logger.info(f"选择设备: {info['name']} (索引: {i})")
                        break
                
                # 尝试创建音频流
                try:
                    self.audio_stream = pa.open(
                        rate=config['sample_rate'],
                        channels=config['channels'],
                        format=pyaudio.paInt16,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=config['frames_per_buffer'],
                        stream_callback=None,
                        start=False
                    )
                    
                    # 测试音频流
                    self.audio_stream.start_stream()
                    test_data = self.audio_stream.read(config['frames_per_buffer'], exception_on_overflow=False)
                    
                    # 如果测试成功，保存配置
                    self.channels = config['channels']
                    self.actual_sample_rate = config['sample_rate']
                    audio_stream_created = True
                    
                    logger.info(f"✅ 音频配置成功: {config['name']} - {config['sample_rate']}Hz, {config['channels']}通道")
                    
                    if config['sample_rate'] != self.target_sample_rate:
                        logger.info(f"将从 {config['sample_rate']}Hz 重采样到 {self.target_sample_rate}Hz")
                    
                except Exception as config_error:
                    logger.warning(f"音频配置 {config['name']} 失败: {config_error}")
                    if hasattr(self, 'audio_stream') and self.audio_stream:
                        try:
                            self.audio_stream.close()
                        except:
                            pass
                        self.audio_stream = None
                    continue
            
            if not audio_stream_created:
                logger.error("所有音频配置都失败了")
                return False
            
            # 启动检测线程
            self.detection_thread = threading.Thread(target=self._detection_worker, daemon=True)
            self.detection_thread.start()
            
            logger.info("🎤 唤醒词检测已启动")
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
    
    def _resample_audio(self, audio_data: bytes, original_rate: int, target_rate: int) -> bytes:
        """
        重采样音频数据
        Args:
            audio_data: 原始音频数据
            original_rate: 原始采样率
            target_rate: 目标采样率
        Returns:
            重采样后的音频数据
        """
        if original_rate == target_rate:
            return audio_data
        
        try:
            # 转换为numpy数组
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # 计算重采样后的样本数
            num_samples = int(len(audio_array) * target_rate / original_rate)
            
            # 使用scipy进行重采样
            resampled_array = signal.resample(audio_array, num_samples)
            
            # 转换回int16并返回bytes
            return resampled_array.astype(np.int16).tobytes()
            
        except Exception as e:
            logger.error(f"音频重采样失败: {e}")
            return audio_data
    
    def _detection_worker(self):
        """检测工作线程 - 使用官方推荐方式"""
        logger.info("唤醒词检测线程启动")
        logger.info(f"使用采样率: {self.target_sample_rate} Hz")
        logger.info(f"帧长度: {self.porcupine.frame_length}")
        logger.info(f"实际设备采样率: {self.actual_sample_rate} Hz")
        logger.info(f"音频通道数: {self.channels}")
        
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while self.is_listening:
            try:
                # 读取音频数据
                frame_length = int(self.porcupine.frame_length * self.actual_sample_rate / self.target_sample_rate)
                
                try:
                    pcm_data = self.audio_stream.read(frame_length, exception_on_overflow=False)
                except Exception as read_error:
                    logger.warning(f"音频读取错误: {read_error}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error("连续音频错误过多，停止检测")
                        break
                    time.sleep(0.1)
                    continue
                
                if not pcm_data:
                    logger.warning("读取到空音频数据")
                    time.sleep(0.01)
                    continue
                
                # 如果是立体声，转换为单声道（取左声道）
                if hasattr(self, 'channels') and self.channels == 2:
                    try:
                        # 将立体声转换为单声道
                        audio_array = np.frombuffer(pcm_data, dtype=np.int16)
                        # 重新整形为 (samples, channels)
                        stereo_array = audio_array.reshape(-1, 2)
                        # 取左声道
                        mono_array = stereo_array[:, 0]
                        pcm_data = mono_array.tobytes()
                    except Exception as stereo_error:
                        logger.warning(f"立体声转换错误: {stereo_error}")
                        continue
                
                # 如果需要重采样（ReSpeaker使用48kHz，Porcupine需要16kHz）
                if self.actual_sample_rate != self.target_sample_rate:
                    try:
                        pcm_data = self._resample_audio(pcm_data, self.actual_sample_rate, self.target_sample_rate)
                    except Exception as resample_error:
                        logger.warning(f"重采样错误: {resample_error}")
                        continue
                
                # 确保数据长度正确
                expected_length = self.porcupine.frame_length * 2  # 16-bit = 2 bytes per sample
                if len(pcm_data) != expected_length:
                    logger.debug(f"音频数据长度不匹配: 期望 {expected_length}, 实际 {len(pcm_data)}")
                    continue
                
                # 使用官方推荐的格式转换
                try:
                    pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm_data)
                except struct.error as struct_error:
                    logger.warning(f"音频数据解包错误: {struct_error}")
                    continue
                
                # 检测唤醒词
                try:
                    keyword_index = self.porcupine.process(pcm)
                    
                    if keyword_index >= 0:
                        logger.info(f"🎉 检测到唤醒词 '快快'，索引: {keyword_index}")
                        
                        # 调用回调函数
                        if self.detection_callback:
                            try:
                                self.detection_callback(keyword_index)
                            except Exception as callback_error:
                                logger.error(f"回调函数执行错误: {callback_error}")
                        
                        # 重置错误计数器
                        consecutive_errors = 0
                    else:
                        # 重置错误计数器（成功处理音频）
                        consecutive_errors = 0
                        
                except Exception as process_error:
                    logger.warning(f"Porcupine处理错误: {process_error}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error("连续处理错误过多，停止检测")
                        break
                    continue
                
            except Exception as e:
                logger.error(f"唤醒词检测线程错误: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("连续错误过多，停止检测线程")
                    break
                time.sleep(0.1)
                
                if not self.is_listening:
                    break
        
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
        self.wake_words = wake_words or ["快快", "小车", "机器人"]
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
                    text = self.recognizer.recognize_sphinx(audio)
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
        print("请说 '快快' 来测试唤醒词检测")
    
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