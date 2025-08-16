#!/usr/bin/python3
"""
增强语音控制器 - 集成唤醒词检测、Whisper语音识别和edge-tts语音合成
支持AI对话模式和传统命令控制模式
"""

import speech_recognition as sr
import pyaudio
import threading
import time
import queue
import logging
import subprocess
import tempfile
import os
import wave
import json
import struct
from voice_control import VoiceController
from ai_conversation import AIConversationManager
from wake_word_detector import WakeWordDetector, SimpleWakeWordDetector
# 导入修复版唤醒词检测器
from simple_wake_word_test import test_simple_wake_word
import simple_wake_word_test
from whisper_integration import get_whisper_recognizer
from vosk_recognizer import VoskRecognizer
import asyncio
import edge_tts
import pygame
import re
from azure_tts import AzureTTS

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedVoiceController(VoiceController):
    """增强的语音控制器，支持AI对话和唤醒词检测"""
    
    def __init__(self, robot=None, ai_conversation_manager=None, expression_controller=None, safety_manager=None, test_mode=False):
        """
        初始化增强语音控制器
        Args:
            robot: LOBOROBOT实例
            ai_conversation_manager: AI对话管理器实例
            expression_controller: 表情控制器实例
            safety_manager: 安全管理器实例
            test_mode: 测试模式，禁用音频流以避免段错误
        """
        super().__init__(robot)
        
        # 测试模式标志
        self.test_mode = test_mode
        
        self.ai_conversation_manager = ai_conversation_manager or AIConversationManager(robot, expression_controller, safety_manager)
        self.expression_controller = expression_controller
        self.safety_manager = safety_manager
        
        # 显示控制器 - 集成OLED显示器
        self.display_controller = None
        self._initialize_display_controller()
        
        # 对话模式状态
        self.conversation_mode = False
        self.wake_word_detected = False
        self.wake_word_active = False
        self.conversation_timeout = 30.0  # 对话超时时间（秒）
        self.last_interaction_time = time.time()
        
        # 音频流控制（防回音）
        self.is_playing_audio = False
        self.audio_lock = threading.Lock()
        self.recording_paused = False
        
        # 语音合成设置
        self.tts_voice = "zh-CN-XiaoxiaoNeural"  # 中文女声
        self.tts_rate = "+0%"
        self.tts_volume = "+0%"
        
        # Azure TTS备选方案
        self.azure_tts = None
        self._initialize_azure_tts()
        
        # 唤醒词检测器
        self.wake_word_detector = None
        self.use_porcupine = self._initialize_wake_word_detection()
        
        # Whisper语音识别
        self.whisper_recognizer = None
        self.use_whisper = self._initialize_whisper()
        
        # Vosk语音识别（中文离线）
        self.vosk_recognizer = None
        self.use_vosk = self._initialize_vosk()
        
        # 音频处理队列
        self.audio_queue = queue.Queue()
        self.tts_queue = queue.Queue()
        
        # 线程控制
        self.tts_thread = None
        self.conversation_thread = None
        self.timeout_thread = None
        
        # 音频播放初始化
        self._initialize_audio_playback()
        
        # 显示语音识别引擎状态总结
        logger.info("🎤 增强语音控制器初始化完成")
        logger.info("=" * 50)
        logger.info("📊 语音识别引擎状态:")
        logger.info(f"   🇨🇳 Vosk (中文离线):     {'✅ 可用' if self.use_vosk else '❌ 不可用'}")
        logger.info(f"   🌍 Whisper (多语言):     {'✅ 可用' if self.use_whisper else '❌ 不可用'}")
        logger.info(f"   🌐 Google (在线):        ✅ 可用")
        logger.info(f"   🇺🇸 PocketSphinx (英文): ✅ 可用")
        logger.info(f"   🖥️ OLED显示器:         {'✅ 可用' if self.display_controller and self.display_controller.is_available() else '❌ 不可用'}")
        logger.info("=" * 50)
    
    def _initialize_wake_word_detection(self):
        """初始化唤醒词检测"""
        try:
            # 首先尝试使用Porcupine
            self.wake_word_detector = WakeWordDetector()
            if self.wake_word_detector.porcupine:
                logger.info("使用Porcupine进行唤醒词检测")
                return True
            else:
                # 备选：使用简单检测器
                self.wake_word_detector = SimpleWakeWordDetector(["快快", "小车", "机器人"])
                logger.info("使用简单检测器进行唤醒词检测")
                return False
        except Exception as e:
            logger.error(f"唤醒词检测初始化失败: {e}")
            self.wake_word_detector = None
            return False
    
    def _initialize_whisper(self):
        """初始化Whisper语音识别"""
        try:
            self.whisper_recognizer = get_whisper_recognizer("base")
            if self.whisper_recognizer.model:
                logger.info("Whisper语音识别初始化成功")
                return True
            else:
                logger.warning("Whisper初始化失败，将使用其他识别方式")
                return False
        except Exception as e:
            logger.warning(f"Whisper不可用，跳过模型加载")
            return False
    
    def _initialize_vosk(self):
        """初始化Vosk中文语音识别"""
        logger.info("🎤 正在初始化Vosk中文语音识别...")
        try:
            self.vosk_recognizer = VoskRecognizer()
            if self.vosk_recognizer.is_available:
                logger.info("🎉 Vosk中文语音识别初始化成功！")
                logger.info("📋 语音识别优先级: Vosk(中文) > Whisper > Google > PocketSphinx")
                return True
            else:
                logger.warning("❌ Vosk初始化失败，将使用其他识别方式")
                return False
        except Exception as e:
            logger.warning(f"❌ Vosk不可用: {e}")
            return False
    
    def _initialize_display_controller(self):
        """初始化显示控制器"""
        try:
            from display_controller import DisplayController
            self.display_controller = DisplayController()
            
            if self.display_controller.is_available():
                self.display_controller.start()
                logger.info("🖥️ OLED显示器初始化成功")
                
                # 如果有表情控制器，关联显示器
                if self.expression_controller:
                    self.expression_controller.set_display_controller(self.display_controller)
            else:
                logger.info("⚠️ OLED显示器不可用，继续运行")
                self.display_controller = None
                
        except ImportError:
            logger.info("⚠️ 显示控制器模块不可用")
            self.display_controller = None
        except Exception as e:
            logger.warning(f"显示控制器初始化失败: {e}")
            self.display_controller = None
    
    def _initialize_azure_tts(self):
        """初始化Azure TTS备选方案"""
        try:
            # 从环境变量获取Azure配置
            azure_endpoint = os.getenv("AZURE_TTS_ENDPOINT")
            azure_api_key = os.getenv("AZURE_TTS_API_KEY") 
            azure_region = os.getenv("AZURE_TTS_REGION", "eastus")
            
            if not azure_endpoint or not azure_api_key:
                logger.info("Azure TTS配置未设置，跳过初始化")
                self.azure_tts = None
                return False
            
            # Azure Speech配置
            azure_config = {
                "endpoint": azure_endpoint,
                "api_key": azure_api_key,
                "region": azure_region,
                "voice": "zh-CN-YunyangNeural",
                "rate": "medium",
                "output_format": "audio-24khz-48kbitrate-mono-mp3"
            }
            
            self.azure_tts = AzureTTS(**azure_config)
            logger.info("🎤 Azure TTS主要方案初始化成功")
            return True
            
        except Exception as e:
            logger.warning(f"Azure TTS初始化失败: {e}")
            self.azure_tts = None
            return False
    
    def _initialize_audio_playback(self):
        """初始化音频播放系统"""
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            logger.info("音频播放系统初始化成功")
        except Exception as e:
            logger.error(f"音频播放系统初始化失败: {e}")
    
    def start_conversation_mode(self):
        """启动AI对话模式"""
        if not self.ai_conversation_manager:
            logger.error("AI对话管理器未初始化")
            return False
            
        if not self.ai_conversation_manager.start_conversation_mode():
            logger.error("AI对话管理器启动失败")
            return False
        
        self.conversation_mode = True
        self.last_interaction_time = time.time()
        
        # 启动唤醒词检测（测试模式下跳过）
        if not self.test_mode and self.wake_word_detector and not self.wake_word_active:
            if self.wake_word_detector.start_detection(self._on_wake_word_detected):
                self.wake_word_active = True
                logger.info("唤醒词检测已启动")
            else:
                logger.warning("唤醒词检测启动失败")
        elif self.test_mode:
            logger.info("测试模式：跳过唤醒词检测启动")
        
        # 启动TTS处理线程
        if not self.tts_thread or not self.tts_thread.is_alive():
            self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
            self.tts_thread.start()
        
        # 启动状态机线程（测试模式下使用安全版本）
        if not self.conversation_thread or not self.conversation_thread.is_alive():
            if self.test_mode:
                self.conversation_thread = threading.Thread(target=self._safe_state_machine_worker, daemon=True)
                logger.info("测试模式：使用安全状态机")
            else:
                self.conversation_thread = threading.Thread(target=self._state_machine_worker, daemon=True)
            self.conversation_thread.start()
        
        # 启动超时检查线程
        if not self.timeout_thread or not self.timeout_thread.is_alive():
            self.timeout_thread = threading.Thread(target=self._timeout_worker, daemon=True)
            self.timeout_thread.start()
        
        logger.info("AI对话模式已启动")
        
        # 显示启动状态 - 用表情代替文字
        if self.display_controller:
            self.display_controller.show_emotion("happy", 30.0)
        
        # 播放启动提示音并提供即时音频确认
        self.speak_text("你好！我是快快，说'快快'来唤醒我吧~")
        
        return True
    
    def stop_conversation_mode(self):
        """停止AI对话模式"""
        self.conversation_mode = False
        self.wake_word_detected = False
        
        # 停止唤醒词检测
        if self.wake_word_detector and self.wake_word_active:
            self.wake_word_detector.stop_detection()
            self.wake_word_active = False
        
        if self.ai_conversation_manager:
            self.ai_conversation_manager.stop_conversation_mode()
        
        # 清空队列
        self.clear_queues()
        
        logger.info("AI对话模式已停止")
        
        # 显示停止状态 - 用表情代替文字
        if self.display_controller:
            self.display_controller.show_emotion("sleeping", 30.0)
        
        # 播放停止提示音
        self.speak_text("对话模式已关闭，再见~")
        
        # 停止显示控制器
        if self.display_controller:
            self.display_controller.stop()
    
    def _on_wake_word_detected(self, keyword_index):
        """唤醒词检测回调 - 修复版本"""
        if not self.conversation_mode:
            return
            
        logger.info(f"🎤 检测到唤醒词！索引: {keyword_index}")
        logger.info("🤖 AI桌宠已唤醒，停止唤醒词检测，开始对话...")
        
        # 关键修复：停止唤醒词检测，避免音频流冲突
        if self.wake_word_detector and self.wake_word_active:
            self.wake_word_detector.stop_detection()
            self.wake_word_active = False
            logger.info("🔇 已停止唤醒词检测")
        
        self.wake_word_detected = True
        self.last_interaction_time = time.time()
        
        # 显示唤醒状态 - 用表情代替文字  
        if self.display_controller:
            self.display_controller.show_emotion("excited", 30.0)
        
        # 提供即时音频确认
        self.speak_text("我在听，请说~", priority=True)
        
        # 如果有表情控制器，显示聆听状态
        if self.expression_controller:
            self.expression_controller.show_listening_animation()
    
    def _timeout_worker(self):
        """超时检查工作线程"""
        while self.conversation_mode:
            try:
                current_time = time.time()
                if (self.wake_word_detected and 
                    current_time - self.last_interaction_time > self.conversation_timeout):
                    
                    logger.info("对话超时，返回待机模式")
                    self.wake_word_detected = False
                    
                    # 重启唤醒词检测（关键修复）
                    if self.wake_word_detector and not self.wake_word_active:
                        if self.wake_word_detector.start_detection(self._on_wake_word_detected):
                            self.wake_word_active = True
                            logger.info("🔔 已重启唤醒词检测")
                        else:
                            logger.warning("重启唤醒词检测失败")
                    
                    # 如果有表情控制器，显示空闲状态
                    if self.expression_controller:
                        self.expression_controller.show_idle_animation()
                
                time.sleep(5)  # 每5秒检查一次
                
            except Exception as e:
                logger.error(f"超时检查错误: {e}")
                time.sleep(5)

    def _state_machine_worker(self):
        """状态机工作线程 - 修复音频流冲突"""
        logger.info("状态机线程启动")
        
        while self.conversation_mode:
            try:
                if self.wake_word_detected:
                    # 处于对话状态，进行语音识别
                    self._handle_conversation_round()
                else:
                    # 等待唤醒，短暂休眠
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"状态机错误: {e}")
                time.sleep(1)
        
        logger.info("状态机线程结束")
    
    def _safe_state_machine_worker(self):
        """安全状态机工作线程 - 测试模式，不使用音频流"""
        logger.info("安全状态机线程启动（测试模式）")
        
        while self.conversation_mode:
            try:
                # 测试模式下只做状态管理，不进行实际音频操作
                if self.wake_word_detected:
                    logger.info("🎙️ 模拟对话状态（测试模式）")
                    # 模拟处理时间
                    time.sleep(2)
                    # 可以在这里添加模拟的AI对话处理
                else:
                    # 等待状态
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"安全状态机错误: {e}")
                time.sleep(1)
        
        logger.info("安全状态机线程结束")
    
    def _handle_conversation_round(self):
        """处理一轮对话"""
        try:
            # 检查是否正在播放音频，避免录制回音
            if self.is_playing_audio or self.recording_paused:
                logger.debug("🔇 跳过录音（正在播放或已暂停）")
                time.sleep(0.5)  # 短暂等待
                return
            
            logger.info("🎙️ 等待用户说话...")
            
            # 录音（此时唤醒词检测已停止，只有这一个音频流）
            recognizer = sr.Recognizer()
            microphone = sr.Microphone()
            
            with microphone as source:
                # 再次检查播放状态（防止录音过程中开始播放）
                if self.is_playing_audio or self.recording_paused:
                    logger.debug("🔇 录音过程中检测到播放，跳过")
                    return
                
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=10)
            
            # 最后检查：避免处理可能的回音音频
            if self.is_playing_audio or self.recording_paused:
                logger.debug("🔇 跳过可能的回音音频处理")
                return
            
            # 语音识别
            text = self._recognize_speech_enhanced(audio)
            if not text or not text.strip():
                logger.info("未识别到有效语音")
                return
            
            logger.info(f"📝 用户说: {text}")
            self.last_interaction_time = time.time()
            
            # 显示用户语音状态 - 用表情代替文字
            if self.display_controller:
                self.display_controller.show_emotion("thinking", 30.0)
            
            # AI处理
            self._process_conversation_text(text)
            
        except sr.WaitTimeoutError:
            logger.info("录音超时，继续等待")
        except Exception as e:
            logger.error(f"对话轮次错误: {e}")
    
    def _recognize_speech_enhanced(self, audio):
        """增强的语音识别（带回音检测）"""
        # 检查是否正在播放，避免识别回音
        if self.is_playing_audio or self.recording_paused:
            logger.debug("🔇 跳过语音识别（正在播放音频）")
            return ""
        
        # 1. 优先使用修复后的Vosk中文识别
        if self.use_vosk and self.vosk_recognizer:
            try:
                result = self.vosk_recognizer.recognize_from_speech_recognition_audio(audio)
                if result and result.strip():
                    logger.info(f"✅ Vosk识别成功: {result}")
                    return result
            except Exception as e:
                logger.error(f"Vosk识别失败: {e}")
        
        # 2. 备选：Google在线识别
        try:
            recognizer = sr.Recognizer()
            result = recognizer.recognize_google(audio, language='zh-CN')
            if result and result.strip():
                logger.info(f"✅ Google识别成功: {result}")
                return result
        except Exception as e:
            logger.error(f"Google识别失败: {e}")
        
        return None
    
    def _process_conversation_text(self, text):
        """处理对话文本"""
        try:
            # 显示思考状态 - 用表情代替文字
            if self.display_controller:
                self.display_controller.show_emotion("thinking", 30.0)
            if self.expression_controller:
                self.expression_controller.show_thinking_animation()
            
            # AI处理
            context = self.ai_conversation_manager.process_user_input(text)
            
            if context and context.ai_response:
                logger.info(f"🤖 AI回复: {context.ai_response}")
                
                # 显示情感表情 - 只显示表情，不显示文字
                if context.emotion_detected:
                    logger.info(f"😊 检测情感: {context.emotion_detected}")
                    if self.display_controller:
                        self.display_controller.show_emotion(context.emotion_detected, 30.0)
                else:
                    # 如果没有检测到情感，显示开心表情
                    if self.display_controller:
                        self.display_controller.show_emotion("happy", 30.0)
                
                # 语音输出
                self.speak_text(context.ai_response)
                
                # 更新交互时间
                self.last_interaction_time = time.time()
            else:
                logger.warning("AI处理失败")
                if self.display_controller:
                    self.display_controller.show_emotion("confused", 30.0)
                self.speak_text("抱歉，我没听清楚，能再说一遍吗？")
                
        except Exception as e:
            logger.error(f"对话处理错误: {e}")

    def listen_continuously(self):
        """持续监听语音命令和对话"""
        if not self.microphone:
            logger.error("麦克风未初始化，无法开始语音识别")
            return
            
        self.is_listening = True
        logger.info("开始语音识别监听...")
        
        # 优化识别器参数以提高准确性
        self.recognizer.energy_threshold = 4000  # 提高能量阈值，减少噪音干扰
        self.recognizer.pause_threshold = 1.0    # 增加停顿时间，确保完整句子
        self.recognizer.timeout = 2              # 增加超时时间
        self.recognizer.phrase_time_limit = 10   # 允许更长的语音输入
        
        while self.is_listening:
            try:
                # 只有在唤醒状态下才进行语音识别
                if self.conversation_mode and self.wake_word_detected:
                    # 检查是否正在播放音频，避免录制回音
                    if self.is_playing_audio or self.recording_paused:
                        logger.debug("🔇 跳过录音（正在播放或已暂停）")
                        time.sleep(0.5)  # 短暂等待
                        continue
                    
                    with self.microphone as source:
                        logger.debug("正在监听对话...")
                        # 再次检查播放状态（防止录音过程中开始播放）
                        if self.is_playing_audio or self.recording_paused:
                            logger.debug("🔇 录音过程中检测到播放，跳过")
                            continue
                        
                        # 对话模式下优化音频捕获
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=10)
                    
                    # 最后检查：避免处理可能的回音音频
                    if self.is_playing_audio or self.recording_paused:
                        logger.debug("🔇 跳过可能的回音音频处理")
                        continue
                    
                    # 将音频放入处理队列
                    self.audio_queue.put(audio)
                else:
                    # 非对话模式或未唤醒时，短暂休眠
                    time.sleep(0.1)
                
            except sr.WaitTimeoutError:
                # 超时是正常的，继续监听
                pass
            except Exception as e:
                logger.error(f"监听错误: {e}")
                time.sleep(1)
    
    def _conversation_worker(self):
        """对话处理工作线程"""
        while self.conversation_mode:
            try:
                # 从队列获取音频
                audio = self.audio_queue.get(timeout=1)
                
                # 处理音频
                if self.conversation_mode and self.wake_word_detected:
                    self._process_conversation_audio(audio)
                elif not self.conversation_mode:
                    # 传统命令模式
                    self._process_audio(audio)
                
                self.audio_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"对话处理错误: {e}")
    
    def _process_conversation_audio(self, audio):
        """处理对话模式下的音频"""
        try:
            logger.info("🎙️ 开始处理录音音频...")
            # 显示思考状态
            if self.expression_controller:
                self.expression_controller.show_thinking_animation()
            
            # 语音识别 - 优化顺序：Google(在线) > Vosk(中文) > Whisper > PocketSphinx(英文)
            text = None
            logger.info("🔍 开始语音识别，尝试顺序: Google → Vosk → Whisper → PocketSphinx")
            
            # 1. 优先使用Google在线识别（准确性最高）
            try:
                logger.info("🎯 尝试使用Google在线识别...")
                text = self.recognizer.recognize_google(audio, language='zh-CN')
                if text and text.strip():
                    logger.info(f"✅ Google识别成功: '{text}' (中文在线)")
                else:
                    logger.info("⚠️  Google返回空结果")
                    text = None
            except sr.UnknownValueError:
                logger.info("⚠️  Google无法理解音频")
                text = None
            except sr.RequestError as e:
                logger.warning(f"❌ Google服务错误: {e}")
                text = None
            except Exception as e:
                logger.warning(f"❌ Google识别失败: {e}")
                text = None
            
            # 2. 备选：使用Vosk进行中文识别
            if not text and self.use_vosk and self.vosk_recognizer:
                logger.info("🎯 尝试使用Vosk进行中文识别...")
                try:
                    text = self.vosk_recognizer.recognize_from_speech_recognition_audio(audio)
                    if text and text.strip():
                        logger.info(f"✅ Vosk识别成功: '{text}' (中文离线)")
                    else:
                        logger.info("⚠️  Vosk返回空结果")
                        text = None
                except Exception as e:
                    logger.warning(f"❌ Vosk识别失败: {e}")
                    text = None
            
            # 3. 备选：使用Whisper
            if not text and self.use_whisper and self.whisper_recognizer:
                logger.info("🎯 尝试使用Whisper识别...")
                try:
                    text = self._whisper_recognize_from_audio(audio)
                    if text and text.strip():
                        logger.info(f"✅ Whisper识别成功: '{text}' (多语言离线)")
                    else:
                        logger.info("⚠️  Whisper返回空结果")
                        text = None
                except Exception as e:
                    logger.warning(f"❌ Whisper识别失败: {e}")
                    text = None
            
            # 4. 最后备选：使用PocketSphinx（英文）
            if not text:
                logger.info("🎯 尝试使用PocketSphinx识别...")
                try:
                    sphinx_text = self.recognizer.recognize_sphinx(audio)
                    if sphinx_text and sphinx_text.strip():
                        text = sphinx_text
                        logger.info(f"✅ PocketSphinx识别成功: '{text}' (英文离线)")
                    else:
                        logger.info("⚠️  PocketSphinx返回空结果")
                except Exception as e:
                    logger.warning(f"❌ PocketSphinx识别失败: {e}")
            
            if not text or not text.strip():
                logger.warning("❌ 所有语音识别引擎都未能识别到有效内容")
                logger.info("💡 建议: 1)说话声音大一些 2)靠近麦克风 3)在安静环境中说话")
                
                # 播放识别失败提示
                self.speak_text("抱歉，我没有听清楚，请再说一遍~")
                return
                
            text = text.strip()
            logger.info(f"🎯 最终识别结果: '{text}'")
            
            # 更新交互时间
            self.last_interaction_time = time.time()
            
            # 显示识别成功的反馈
            if self.expression_controller:
                self.expression_controller.show_processing_animation()
            
            # 检查是否是结束对话的命令
            if any(word in text for word in ['再见', '结束对话', '停止', '退出', '睡觉']):
                self.wake_word_detected = False
                self.speak_text("好的，有需要再叫我~")
                
                if self.expression_controller:
                    self.expression_controller.show_idle_animation()
                return
            
            # 发送到AI对话管理器
            context = self.ai_conversation_manager.process_user_input(text)
            
            if context and context.ai_response:
                # 播放AI回复
                self.speak_text(context.ai_response)
                
                # 根据情感执行相应动作
                self._execute_emotional_action(context.emotion_detected)
            else:
                # 处理失败时的反馈
                self.speak_text("抱歉，我没有理解，请再说一遍~")
            
        except sr.UnknownValueError:
            logger.debug("无法理解音频")
        except sr.RequestError as e:
            logger.error(f"语音识别服务错误: {e}")
            self.speak_text("语音识别出现问题，请稍后再试~")
        except Exception as e:
            logger.error(f"对话音频处理错误: {e}")
            self.speak_text("处理出现问题，请稍后再试~")
    
    def _whisper_recognize_from_audio(self, audio):
        """使用Whisper进行语音识别"""
        try:
            if not self.whisper_recognizer:
                return None
                
            # 将SpeechRecognition的AudioData转换为音频数据
            wav_data = audio.get_wav_data()
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(wav_data)
                temp_file_path = temp_file.name
            
            try:
                # 使用Whisper识别
                text = self.whisper_recognizer.recognize_audio_file(temp_file_path)
                return text
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            
        except Exception as e:
            logger.error(f"Whisper识别失败: {e}")
            return None
    
    def _execute_emotional_action(self, emotion):
        """根据情感执行相应的机器人动作"""
        if not self.robot:
            return
            
        try:
            if emotion == 'happy':
                # 开心时转个圈
                self.robot.turnRight(30, 0.5)
                self.robot.turnLeft(30, 0.5)
                
            elif emotion == 'excited':
                # 兴奋时快速左右摆动
                self.robot.turnLeft(40, 0.2)
                self.robot.turnRight(40, 0.2)
                self.robot.turnLeft(40, 0.2)
                
            elif emotion == 'sad':
                # 悲伤时缓慢后退
                self.robot.t_down(20, 0.5)
                
            elif emotion == 'confused':
                # 困惑时左右摇头
                self.robot.turnLeft(25, 0.3)
                self.robot.turnRight(25, 0.3)
                
            elif emotion == 'thinking':
                # 思考时轻微摆动
                self.robot.moveLeft(15, 0.2)
                self.robot.moveRight(15, 0.2)
                
        except Exception as e:
            logger.error(f"执行情感动作失败: {e}")
    
    def _filter_tts_text(self, text):
        """过滤TTS文本，移除括号中的表情和动作描述"""
        if not text:
            return text
        
        # 移除各种类型的括号内容
        # 匹配圆括号内容：(表情描述)
        text = re.sub(r'\([^)]*\)', '', text)
        # 匹配方括号内容：[动作描述]
        text = re.sub(r'\[[^\]]*\]', '', text)
        # 匹配中文圆括号：（表情）
        text = re.sub(r'（[^）]*）', '', text)
        # 匹配中文方括号：【动作】
        text = re.sub(r'【[^】]*】', '', text)
        
        # 清理多余的空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def speak_text(self, text, priority=False):
        """将文本转换为语音并播放"""
        if text:
            # 过滤掉括号中的表情和动作描述
            filtered_text = self._filter_tts_text(text)
            
            if filtered_text:  # 确保过滤后还有内容
                if priority:
                    # 优先级高的消息插入队列前端
                    temp_queue = queue.Queue()
                    temp_queue.put(filtered_text)
                    while not self.tts_queue.empty():
                        temp_queue.put(self.tts_queue.get())
                    self.tts_queue = temp_queue
                else:
                    self.tts_queue.put(filtered_text)
    
    def _tts_worker(self):
        """TTS处理工作线程"""
        while self.conversation_mode or not self.tts_queue.empty():
            try:
                # 从队列获取文本
                text = self.tts_queue.get(timeout=1)
                
                # 显示说话动画
                if self.expression_controller:
                    # 估算说话时长
                    estimated_duration = len(text) * 0.15  # 大约每个字0.15秒
                    threading.Thread(
                        target=self.expression_controller.animate_speaking,
                        args=(estimated_duration,),
                        daemon=True
                    ).start()
                
                # 使用edge-tts生成语音
                self._generate_and_play_speech(text)
                
                self.tts_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"TTS处理错误: {e}")
    
    def _pause_recording(self):
        """暂停录音以防回音"""
        with self.audio_lock:
            if not self.recording_paused:
                logger.debug("🔇 暂停录音（防回音）")
                self.recording_paused = True
                # 如果有活跃的识别流，暂停它们
                if hasattr(self, 'vosk_recognizer') and self.vosk_recognizer:
                    # Vosk识别器不需要特殊暂停，它是基于数据流的
                    pass
    
    def _resume_recording(self):
        """恢复录音"""
        with self.audio_lock:
            if self.recording_paused:
                logger.debug("🎤 恢复录音")
                self.recording_paused = False
                # 恢复识别流
                if hasattr(self, 'vosk_recognizer') and self.vosk_recognizer:
                    pass
    
    def _generate_and_play_speech(self, text):
        """生成并播放语音（带回音防护）"""
        try:
            # 检查是否在离线模式
            if self.safety_manager and self.safety_manager.safety_state.offline_mode_active:
                logger.info(f"离线模式TTS: {text}")
                return
            
            # 设置播放状态并暂停录音
            with self.audio_lock:
                self.is_playing_audio = True
            self._pause_recording()
            
            try:
                # 创建临时MP3文件
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                    mp3_file_path = temp_file.name
                
                # 使用edge-tts生成MP3语音
                asyncio.run(self._async_generate_speech(text, mp3_file_path))
                
                # 播放音频文件
                self._play_audio_file_pygame(mp3_file_path)
                
                # 播放完成后等待一小段时间
                time.sleep(0.5)  # 等待音频完全播放完成
                
                # 清理临时文件
                if os.path.exists(mp3_file_path):
                    os.unlink(mp3_file_path)
                    
            finally:
                # 恢复录音状态
                with self.audio_lock:
                    self.is_playing_audio = False
                self._resume_recording()
                logger.debug("🔊 音频播放完成，已恢复录音")
            
        except Exception as e:
            logger.error(f"语音生成播放失败: {e}")
            
            # 确保在异常情况下也恢复录音
            with self.audio_lock:
                self.is_playing_audio = False
            self._resume_recording()
            
            # 记录TTS失败
            if self.safety_manager:
                self.safety_manager.handle_api_failure("tts_error", 0)
    
    async def _async_generate_speech(self, text, output_path):
        """异步生成语音 - Azure TTS为主，edge-tts为备选"""
        # 优先使用Azure TTS
        if self.azure_tts:
            try:
                logger.debug("尝试使用Azure TTS生成语音")
                success = self.azure_tts.synthesize_to_file(text, output_path)
                if success:
                    logger.debug("Azure TTS生成成功")
                    return True
                else:
                    logger.warning("Azure TTS生成失败")
            except Exception as azure_e:
                logger.warning(f"Azure TTS异常: {azure_e}")
        else:
            logger.debug("Azure TTS未配置")
        
        # 备选方案：使用edge-tts
        try:
            logger.info("尝试使用edge-tts备选方案")
            communicate = edge_tts.Communicate(text, self.tts_voice)
            await communicate.save(output_path)
            logger.info("edge-tts生成成功")
            return True
        except Exception as e:
            logger.error(f"edge-tts语音生成失败: {e}")
            
            # 两种TTS都失败
            logger.error("所有TTS方案都失败")
            raise Exception(f"TTS生成失败: Azure TTS不可用或失败, edge-tts错误={e}")
    
    def _play_audio_file_pygame(self, file_path):
        """使用可靠的音频播放方式"""
        try:
            # 优先使用我们修复的可靠播放方式
            self._play_audio_file_reliable(file_path)
        except Exception as e:
            logger.error(f"可靠播放失败: {e}")
            # 备选方案
            self._play_audio_file_system(file_path)
    
    def _play_audio_file_reliable(self, file_path):
        """使用修复后的可靠播放方式"""
        try:
            # 如果是MP3文件，需要转换为WAV
            if file_path.endswith('.mp3'):
                wav_path = file_path.replace('.mp3', '.wav')
                
                # 使用ffmpeg转换（完整路径）
                convert_cmd = [
                    '/usr/bin/ffmpeg', '-i', file_path,
                    '-ar', '44100',  # 采样率44100Hz
                    '-ac', '1',      # 单声道
                    '-f', 'wav',     # WAV格式
                    '-y',            # 覆盖输出文件
                    wav_path
                ]
                
                result = subprocess.run(convert_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    file_path = wav_path
                else:
                    logger.warning(f"音频转换失败，尝试直接播放: {result.stderr}")
            
            # 使用修复后的可靠播放命令
            result = subprocess.run(['/usr/bin/aplay', '-D', 'hw:0,0', file_path], 
                                  capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.debug("音频播放成功")
                # 清理转换的WAV文件
                if file_path.endswith('.wav') and file_path != file_path.replace('.mp3', '.wav'):
                    try:
                        os.unlink(file_path)
                    except:
                        pass
                return
            else:
                logger.error(f"音频播放失败: {result.stderr}")
                raise Exception(f"aplay failed: {result.stderr}")
                
        except Exception as e:
            logger.error(f"可靠播放方式失败: {e}")
            raise
    
    def _play_audio_file_system(self, file_path):
        """使用系统命令播放音频文件（备选方案）"""
        try:
            # 备选：使用mpg123
            subprocess.run(['mpg123', file_path], 
                         check=True, 
                         capture_output=True,
                         timeout=10)
        except:
            try:
                # 备选：使用ffplay
                subprocess.run(['ffplay', '-nodisp', '-autoexit', file_path], 
                             check=True, 
                             capture_output=True,
                             timeout=10)
            except:
                logger.error("无法播放音频文件，请安装aplay、mpg123或ffplay")
    
    def get_conversation_status(self):
        """获取对话状态"""
        # 确定当前状态
        if not self.conversation_mode:
            current_state = "stopped"
        elif self.wake_word_detected:
            current_state = "conversation"
        else:
            current_state = "waiting"
            
        return {
            'conversation_mode': self.conversation_mode,
            'state': current_state,
            'wake_word_detected': self.wake_word_detected,
            'wake_word_active': self.wake_word_active,
            'ai_manager_active': self.ai_conversation_manager.is_active() if self.ai_conversation_manager else False,
            'tts_queue_size': self.tts_queue.qsize(),
            'audio_queue_size': self.audio_queue.qsize(),
            'use_whisper': self.use_whisper,
            'use_porcupine': self.use_porcupine,
            'last_interaction': self.last_interaction_time
        }
    
    def set_tts_voice(self, voice_name):
        """设置TTS语音"""
        available_voices = [
            "zh-CN-XiaoxiaoNeural",  # 女声
            "zh-CN-YunxiNeural",     # 男声
            "zh-CN-YunyangNeural",   # 男声
            "zh-CN-XiaoyiNeural",    # 女声
            "zh-CN-YunjianNeural"    # 男声
        ]
        
        if voice_name in available_voices:
            self.tts_voice = voice_name
            logger.info(f"TTS语音设置为: {voice_name}")
        else:
            logger.warning(f"不支持的语音: {voice_name}，可用语音: {available_voices}")
    
    def set_tts_parameters(self, rate=None, volume=None):
        """设置TTS参数"""
        if rate is not None:
            self.tts_rate = rate
            logger.info(f"TTS语速设置为: {rate}")
        
        if volume is not None:
            self.tts_volume = volume
            logger.info(f"TTS音量设置为: {volume}")
    
    def clear_queues(self):
        """清空所有队列"""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
                
        while not self.tts_queue.empty():
            try:
                self.tts_queue.get_nowait()
            except queue.Empty:
                break
        
        logger.info("音频和TTS队列已清空")
    
    def force_wake_up(self):
        """强制唤醒（用于测试或手动激活）"""
        if self.conversation_mode:
            self.wake_word_detected = True
            self.last_interaction_time = time.time()
            self.speak_text("我被唤醒了，请说~", priority=True)
            
            if self.expression_controller:
                self.expression_controller.show_listening_animation()
            
            logger.info("强制唤醒成功")
            return True
        else:
            logger.warning("对话模式未启动，无法强制唤醒")
            return False
    
    def get_available_voices(self):
        """获取可用的TTS语音列表"""
        return [
            {"name": "zh-CN-XiaoxiaoNeural", "description": "晓晓 - 女声"},
            {"name": "zh-CN-YunxiNeural", "description": "云希 - 男声"},
            {"name": "zh-CN-YunyangNeural", "description": "云扬 - 男声"},
            {"name": "zh-CN-XiaoyiNeural", "description": "晓伊 - 女声"},
            {"name": "zh-CN-YunjianNeural", "description": "云健 - 男声"}
        ]

# 测试和演示函数
def test_enhanced_voice_control():
    """测试增强语音控制功能"""
    print("=== 增强语音控制器测试 ===")
    
    # 创建增强语音控制器
    enhanced_voice = EnhancedVoiceController()
    
    try:
        # 显示系统状态
        status = enhanced_voice.get_conversation_status()
        print(f"系统状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
        
        # 显示可用语音
        voices = enhanced_voice.get_available_voices()
        print("\n可用语音:")
        for voice in voices:
            print(f"  - {voice['name']}: {voice['description']}")
        
        # 启动对话模式
        if enhanced_voice.start_conversation_mode():
            print("\n对话模式启动成功")
            print("功能说明:")
            print("- 说'快快'来唤醒机器人")
            print("- 唤醒后可以进行自然对话")
            print("- 说'再见'来结束对话")
            print("- 30秒无交互会自动返回待机")
            print("- 按Ctrl+C退出测试")
            
            # 启动监听
            listen_thread = threading.Thread(target=enhanced_voice.listen_continuously, daemon=True)
            listen_thread.start()
            
            # 保持程序运行
            while True:
                time.sleep(1)
                
        else:
            print("对话模式启动失败")
            
    except KeyboardInterrupt:
        print("\n正在停止...")
        enhanced_voice.stop()
        enhanced_voice.stop_conversation_mode()
        print("测试结束")

def demo_tts_voices():
    """演示不同TTS语音"""
    print("=== TTS语音演示 ===")
    
    enhanced_voice = EnhancedVoiceController()
    
    # 启动TTS线程
    enhanced_voice.conversation_mode = True
    enhanced_voice.tts_thread = threading.Thread(target=enhanced_voice._tts_worker, daemon=True)
    enhanced_voice.tts_thread.start()
    
    voices = enhanced_voice.get_available_voices()
    test_text = "你好，我是快快，很高兴认识你！"
    
    for voice in voices:
        print(f"\n测试语音: {voice['description']}")
        enhanced_voice.set_tts_voice(voice['name'])
        enhanced_voice.speak_text(test_text)
        time.sleep(3)  # 等待播放完成
    
    enhanced_voice.conversation_mode = False
    print("\n语音演示完成")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo_tts_voices()
    else:
        test_enhanced_voice_control()