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
from whisper_integration import get_whisper_recognizer
import asyncio
import edge_tts
import pygame

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedVoiceController(VoiceController):
    """增强的语音控制器，支持AI对话和唤醒词检测"""
    
    def __init__(self, robot=None, ai_conversation_manager=None, expression_controller=None, safety_manager=None):
        """
        初始化增强语音控制器
        Args:
            robot: LOBOROBOT实例
            ai_conversation_manager: AI对话管理器实例
            expression_controller: 表情控制器实例
            safety_manager: 安全管理器实例
        """
        super().__init__(robot)
        
        self.ai_conversation_manager = ai_conversation_manager or AIConversationManager(robot, expression_controller, safety_manager)
        self.expression_controller = expression_controller
        self.safety_manager = safety_manager
        
        # 对话模式状态
        self.conversation_mode = False
        self.wake_word_detected = False
        self.wake_word_active = False
        self.conversation_timeout = 30.0  # 对话超时时间（秒）
        self.last_interaction_time = time.time()
        
        # 语音合成设置
        self.tts_voice = "zh-CN-XiaoxiaoNeural"  # 中文女声
        self.tts_rate = "+0%"
        self.tts_volume = "+0%"
        
        # 唤醒词检测器
        self.wake_word_detector = None
        self.use_porcupine = self._initialize_wake_word_detection()
        
        # Whisper语音识别
        self.whisper_recognizer = None
        self.use_whisper = self._initialize_whisper()
        
        # 音频处理队列
        self.audio_queue = queue.Queue()
        self.tts_queue = queue.Queue()
        
        # 线程控制
        self.tts_thread = None
        self.conversation_thread = None
        self.timeout_thread = None
        
        # 音频播放初始化
        self._initialize_audio_playback()
        
        logger.info("增强语音控制器初始化完成")
    
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
                self.wake_word_detector = SimpleWakeWordDetector(["喵喵小车", "小车", "机器人"])
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
                logger.warning("Whisper初始化失败，将使用PocketSphinx")
                return False
        except Exception as e:
            logger.error(f"Whisper初始化失败: {e}")
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
        
        # 启动唤醒词检测
        if self.wake_word_detector and not self.wake_word_active:
            if self.wake_word_detector.start_detection(self._on_wake_word_detected):
                self.wake_word_active = True
                logger.info("唤醒词检测已启动")
            else:
                logger.warning("唤醒词检测启动失败")
        
        # 启动TTS处理线程
        if not self.tts_thread or not self.tts_thread.is_alive():
            self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
            self.tts_thread.start()
        
        # 启动对话处理线程
        if not self.conversation_thread or not self.conversation_thread.is_alive():
            self.conversation_thread = threading.Thread(target=self._conversation_worker, daemon=True)
            self.conversation_thread.start()
        
        # 启动超时检查线程
        if not self.timeout_thread or not self.timeout_thread.is_alive():
            self.timeout_thread = threading.Thread(target=self._timeout_worker, daemon=True)
            self.timeout_thread.start()
        
        logger.info("AI对话模式已启动")
        
        # 播放启动提示音并提供即时音频确认
        self.speak_text("你好！我是圆滚滚，说'喵喵小车'来唤醒我吧~")
        
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
        
        # 播放停止提示音
        self.speak_text("对话模式已关闭，再见~")
    
    def _on_wake_word_detected(self, keyword_index):
        """唤醒词检测回调"""
        if not self.conversation_mode:
            return
            
        self.wake_word_detected = True
        self.last_interaction_time = time.time()
        
        logger.info(f"检测到唤醒词，索引: {keyword_index}")
        
        # 提供即时音频确认（在1秒内）
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
                    
                    # 如果有表情控制器，显示空闲状态
                    if self.expression_controller:
                        self.expression_controller.show_idle_animation()
                
                time.sleep(5)  # 每5秒检查一次
                
            except Exception as e:
                logger.error(f"超时检查错误: {e}")
                time.sleep(5)

    def listen_continuously(self):
        """持续监听语音命令和对话"""
        if not self.microphone:
            logger.error("麦克风未初始化，无法开始语音识别")
            return
            
        self.is_listening = True
        logger.info("开始语音识别监听...")
        
        # 设置识别器参数
        self.recognizer.energy_threshold = 300
        self.recognizer.pause_threshold = 0.8
        self.recognizer.timeout = 1
        
        while self.is_listening:
            try:
                # 只有在唤醒状态下才进行语音识别
                if self.conversation_mode and self.wake_word_detected:
                    with self.microphone as source:
                        logger.debug("正在监听对话...")
                        # 监听音频，对话模式下延长监听时间
                        audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=8)
                    
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
            # 显示思考状态
            if self.expression_controller:
                self.expression_controller.show_thinking_animation()
            
            # 语音识别 - 优先使用Whisper
            text = None
            if self.use_whisper and self.whisper_recognizer:
                text = self._whisper_recognize_from_audio(audio)
            
            # 备选：使用PocketSphinx
            if not text:
                try:
                    text = self.recognizer.recognize_sphinx(audio, language='zh-cn')
                except:
                    pass
            
            if not text or not text.strip():
                logger.debug("未识别到有效语音")
                return
                
            text = text.strip()
            logger.info(f"识别到语音: '{text}'")
            
            # 更新交互时间
            self.last_interaction_time = time.time()
            
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
    
    def speak_text(self, text, priority=False):
        """将文本转换为语音并播放"""
        if text:
            if priority:
                # 优先级高的消息插入队列前端
                temp_queue = queue.Queue()
                temp_queue.put(text)
                while not self.tts_queue.empty():
                    temp_queue.put(self.tts_queue.get())
                self.tts_queue = temp_queue
            else:
                self.tts_queue.put(text)
    
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
    
    def _generate_and_play_speech(self, text):
        """生成并播放语音"""
        try:
            # 检查是否在离线模式
            if self.safety_manager and self.safety_manager.safety_state.offline_mode_active:
                # 离线模式下使用简单的文本输出
                logger.info(f"离线模式TTS: {text}")
                return
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            # 使用edge-tts生成语音
            asyncio.run(self._async_generate_speech(text, temp_file_path))
            
            # 播放音频文件
            self._play_audio_file_pygame(temp_file_path)
            
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            
        except Exception as e:
            logger.error(f"语音生成播放失败: {e}")
            
            # 如果有安全管理器，记录TTS失败
            if self.safety_manager:
                self.safety_manager.handle_api_failure("tts_error", 0)
    
    async def _async_generate_speech(self, text, output_path):
        """异步生成语音"""
        try:
            communicate = edge_tts.Communicate(
                text, 
                self.tts_voice,
                rate=self.tts_rate,
                volume=self.tts_volume
            )
            await communicate.save(output_path)
        except Exception as e:
            logger.error(f"edge-tts语音生成失败: {e}")
            raise
    
    def _play_audio_file_pygame(self, file_path):
        """使用pygame播放音频文件"""
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            # 等待播放完成
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"pygame音频播放失败: {e}")
            # 备选方案
            self._play_audio_file_system(file_path)
    
    def _play_audio_file_system(self, file_path):
        """使用系统命令播放音频文件"""
        try:
            # 首先尝试aplay（树莓派常用）
            result = subprocess.run(['aplay', file_path], 
                                  capture_output=True, 
                                  timeout=10)
            if result.returncode == 0:
                return
        except:
            pass
        
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
        return {
            'conversation_mode': self.conversation_mode,
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
            print("- 说'喵喵小车'来唤醒机器人")
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
    test_text = "你好，我是圆滚滚，很高兴认识你！"
    
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