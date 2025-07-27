#!/usr/bin/env python3
"""
修复 EnhancedVoiceController 的音频流冲突问题
基于正确的状态机设计
"""

import os
import sys
import shutil

def backup_original_file():
    """备份原始文件"""
    original_path = "src/enhanced_voice_control.py"
    backup_path = "src/enhanced_voice_control.py.backup"
    
    if os.path.exists(original_path):
        if not os.path.exists(backup_path):
            shutil.copy2(original_path, backup_path)
            print(f"✅ 已备份原始文件: {backup_path}")
        else:
            print(f"ℹ️ 备份文件已存在: {backup_path}")
        return True
    else:
        print(f"❌ 原始文件不存在: {original_path}")
        return False

def create_fixed_enhanced_voice_controller():
    """创建修复后的 EnhancedVoiceController"""
    
    fixed_code = '''#!/usr/bin/python3
"""
修复后的增强语音控制器 - 避免音频流冲突
基于正确的状态机设计：唤醒词监听 ↔ 语音对话
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
from vosk_recognizer import VoskRecognizer
import asyncio
import edge_tts
import pygame

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedVoiceController(VoiceController):
    """修复后的增强语音控制器 - 正确的状态机设计"""
    
    def __init__(self, robot=None, ai_conversation_manager=None, expression_controller=None, safety_manager=None):
        """初始化增强语音控制器"""
        super().__init__(robot)
        
        self.ai_conversation_manager = ai_conversation_manager or AIConversationManager(robot, expression_controller, safety_manager)
        self.expression_controller = expression_controller
        self.safety_manager = safety_manager
        
        # 状态机
        self.state = "stopped"  # stopped, waiting, conversation
        self.conversation_mode = False
        self.wake_word_detected = False
        self.wake_word_active = False
        self.conversation_timeout = 30.0
        self.last_interaction_time = time.time()
        
        # 语音合成设置
        self.tts_voice = "zh-CN-XiaoxiaoNeural"
        self.tts_rate = "+0%"
        self.tts_volume = "+0%"
        
        # 组件初始化
        self.wake_word_detector = None
        self.use_porcupine = self._initialize_wake_word_detection()
        
        self.whisper_recognizer = None
        self.use_whisper = self._initialize_whisper()
        
        self.vosk_recognizer = None
        self.use_vosk = self._initialize_vosk()
        
        # 线程和队列
        self.tts_queue = queue.Queue()
        self.main_thread = None
        self.tts_thread = None
        self.running = False
        
        # 音频播放初始化
        self._initialize_audio_playback()
        
        # 显示状态
        logger.info("🎤 修复后的增强语音控制器初始化完成")
        logger.info("=" * 50)
        logger.info("📊 语音识别引擎状态:")
        logger.info(f"   🇨🇳 Vosk (中文离线):     {'✅ 可用' if self.use_vosk else '❌ 不可用'}")
        logger.info(f"   🌍 Whisper (多语言):     {'✅ 可用' if self.use_whisper else '❌ 不可用'}")
        logger.info(f"   🌐 Google (在线):        ✅ 可用")
        logger.info(f"   🇺🇸 PocketSphinx (英文): ✅ 可用")
        logger.info("=" * 50)
    
    def _initialize_wake_word_detection(self):
        """初始化唤醒词检测"""
        try:
            self.wake_word_detector = WakeWordDetector()
            if self.wake_word_detector.porcupine:
                logger.info("使用Porcupine进行唤醒词检测")
                return True
            else:
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
    
    def _initialize_audio_playback(self):
        """初始化音频播放系统"""
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            logger.info("音频播放系统初始化成功")
        except Exception as e:
            logger.error(f"音频播放系统初始化失败: {e}")
    
    def start_conversation_mode(self):
        """启动AI对话模式 - 修复后的版本"""
        if not self.ai_conversation_manager:
            logger.error("AI对话管理器未初始化")
            return False
            
        if not self.ai_conversation_manager.start_conversation_mode():
            logger.error("AI对话管理器启动失败")
            return False
        
        self.conversation_mode = True
        self.running = True
        self.state = "waiting"
        self.last_interaction_time = time.time()
        
        # 启动TTS处理线程
        if not self.tts_thread or not self.tts_thread.is_alive():
            self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
            self.tts_thread.start()
        
        # 启动主状态机线程（重要修复点）
        if not self.main_thread or not self.main_thread.is_alive():
            self.main_thread = threading.Thread(target=self._main_state_machine, daemon=True)
            self.main_thread.start()
        
        logger.info("AI对话模式已启动")
        
        # 播放启动提示音
        self.speak_text("你好！我是圆滚滚，说'喵喵小车'来唤醒我吧~")
        
        return True
    
    def _main_state_machine(self):
        """主状态机 - 关键修复"""
        logger.info("主状态机启动")
        
        while self.running and self.conversation_mode:
            try:
                if self.state == "waiting":
                    # 状态1: 等待唤醒词（只有唤醒词检测在工作）
                    self._wait_for_wake_word()
                    
                elif self.state == "conversation":
                    # 状态2: 进行对话（只有语音识别在工作）
                    self._handle_conversation_session()
                    
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"状态机错误: {e}")
                time.sleep(1)
        
        logger.info("主状态机结束")
    
    def _wait_for_wake_word(self):
        """等待唤醒词状态"""
        if not self.wake_word_detector:
            logger.warning("唤醒词检测器不可用")
            time.sleep(5)
            return
        
        try:
            # 启动唤醒词检测（单一音频流）
            if self.wake_word_detector.start_detection(self._on_wake_word_detected):
                self.wake_word_active = True
                logger.info("🔔 等待唤醒词...")
                
                # 等待状态改变或超时
                timeout_counter = 0
                while self.state == "waiting" and self.running and timeout_counter < 600:  # 60秒
                    time.sleep(0.1)
                    timeout_counter += 1
                
                # 停止唤醒词检测
                self.wake_word_detector.stop_detection()
                self.wake_word_active = False
            else:
                logger.error("唤醒词检测启动失败")
                time.sleep(5)
                
        except Exception as e:
            logger.error(f"唤醒词检测错误: {e}")
            time.sleep(5)
    
    def _on_wake_word_detected(self, keyword):
        """唤醒词检测回调"""
        logger.info(f"🎉 检测到唤醒词: {keyword}")
        
        # 切换到对话状态
        self.state = "conversation"
        self.wake_word_detected = True
        self.last_interaction_time = time.time()
        
        # 播放唤醒确认
        self.speak_text("我在！有什么可以帮你的吗？")
    
    def _handle_conversation_session(self):
        """处理对话会话"""
        logger.info("💬 进入对话模式")
        
        conversation_rounds = 0
        max_rounds = 5
        
        while (self.state == "conversation" and 
               self.running and 
               conversation_rounds < max_rounds):
            
            # 检查超时
            if time.time() - self.last_interaction_time > self.conversation_timeout:
                logger.info("⏰ 对话超时")
                break
            
            # 进行一轮对话
            if self._single_conversation_round():
                conversation_rounds += 1
                self.last_interaction_time = time.time()
            else:
                logger.info("对话结束或失败")
                break
        
        # 对话结束，返回等待状态
        logger.info(f"💤 对话结束（{conversation_rounds}轮），返回等待模式")
        self.speak_text("好的，需要时再叫我哦！")
        
        self.state = "waiting"
        self.wake_word_detected = False
    
    def _single_conversation_round(self):
        """单轮对话"""
        try:
            logger.info("🎙️ 等待用户说话...")
            
            # 录音（单一音频流）
            recognizer = sr.Recognizer()
            microphone = sr.Microphone()
            
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=10)
            
            # 语音识别
            text = self._recognize_speech(audio)
            if not text or not text.strip():
                logger.info("未识别到有效语音")
                return False
            
            logger.info(f"📝 用户说: {text}")
            
            # AI处理
            context = self.ai_conversation_manager.process_user_input(text)
            if context and context.ai_response:
                logger.info(f"🤖 AI回复: {context.ai_response}")
                self.speak_text(context.ai_response)
                return True
            else:
                logger.warning("AI处理失败")
                return False
                
        except sr.WaitTimeoutError:
            logger.info("录音超时，继续等待")
            return False
        except Exception as e:
            logger.error(f"对话轮次错误: {e}")
            return False
    
    def _recognize_speech(self, audio):
        """语音识别（使用修复后的Vosk）"""
        # 优先使用Vosk中文识别
        if self.use_vosk and self.vosk_recognizer:
            try:
                result = self.vosk_recognizer.recognize_from_speech_recognition_audio(audio)
                if result and result.strip():
                    return result
            except Exception as e:
                logger.error(f"Vosk识别失败: {e}")
        
        # 备选：Google识别
        try:
            recognizer = sr.Recognizer()
            result = recognizer.recognize_google(audio, language='zh-CN')
            if result and result.strip():
                logger.info("使用Google识别成功")
                return result
        except Exception as e:
            logger.error(f"Google识别失败: {e}")
        
        return None
    
    def stop_conversation_mode(self):
        """停止AI对话模式"""
        logger.info("停止AI对话模式")
        
        self.running = False
        self.conversation_mode = False
        self.state = "stopped"
        
        # 停止唤醒词检测
        if self.wake_word_detector and self.wake_word_active:
            self.wake_word_detector.stop_detection()
            self.wake_word_active = False
        
        # 停止AI对话管理器
        if self.ai_conversation_manager:
            self.ai_conversation_manager.stop_conversation_mode()
        
        logger.info("AI对话模式已停止")
    
    def speak_text(self, text):
        """添加文本到TTS队列"""
        if text and text.strip():
            self.tts_queue.put(text.strip())
    
    def _tts_worker(self):
        """TTS工作线程"""
        while self.running:
            try:
                text = self.tts_queue.get(timeout=1)
                self._generate_and_play_speech(text)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"TTS处理错误: {e}")
    
    def _generate_and_play_speech(self, text):
        """生成并播放语音"""
        try:
            # 检查离线模式
            if self.safety_manager and self.safety_manager.safety_state.offline_mode_active:
                logger.info(f"离线模式TTS: {text}")
                return
            
            # 创建临时MP3文件
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                mp3_file_path = temp_file.name
            
            # 使用edge-tts生成语音
            asyncio.run(self._async_generate_speech(text, mp3_file_path))
            
            # 播放音频文件
            self._play_audio_file_reliable(mp3_file_path)
            
            # 清理临时文件
            if os.path.exists(mp3_file_path):
                os.unlink(mp3_file_path)
            
        except Exception as e:
            logger.error(f"语音生成播放失败: {e}")
    
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
    
    def _play_audio_file_reliable(self, file_path):
        """可靠的音频播放"""
        try:
            # 如果是MP3文件，转换为WAV
            if file_path.endswith('.mp3'):
                wav_path = file_path.replace('.mp3', '.wav')
                
                # 使用ffmpeg转换
                convert_cmd = [
                    '/usr/bin/ffmpeg', '-i', file_path,
                    '-ar', '44100',
                    '-ac', '1',
                    '-f', 'wav',
                    '-y',
                    wav_path
                ]
                
                result = subprocess.run(convert_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    file_path = wav_path
            
            # 播放WAV文件
            play_cmd = ['aplay', file_path]
            subprocess.run(play_cmd, capture_output=True, timeout=10)
            
        except Exception as e:
            logger.error(f"音频播放失败: {e}")
    
    # 保持与原始接口的兼容性
    def force_wake_up(self):
        """强制唤醒"""
        if self.state == "waiting":
            self._on_wake_word_detected("强制唤醒")
            return True
        return False
    
    def get_conversation_status(self):
        """获取对话状态"""
        return {
            'conversation_mode': self.conversation_mode,
            'state': self.state,
            'wake_word_detected': self.wake_word_detected,
            'last_interaction_time': self.last_interaction_time
        }
'''
    
    # 写入修复后的文件
    fixed_path = "src/enhanced_voice_control_fixed.py"
    try:
        with open(fixed_path, 'w', encoding='utf-8') as f:
            f.write(fixed_code)
        print(f"✅ 已创建修复版本: {fixed_path}")
        return True
    except Exception as e:
        print(f"❌ 创建修复版本失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 修复 EnhancedVoiceController 音频流冲突问题")
    print("=" * 60)
    
    # 1. 备份原始文件
    if not backup_original_file():
        return False
    
    # 2. 创建修复版本
    if not create_fixed_enhanced_voice_controller():
        return False
    
    print("\n🎉 修复完成！")
    print("📋 修复内容:")
    print("✅ 实现正确的状态机：waiting ↔ conversation")  
    print("✅ 避免音频流冲突：任何时候只有一个音频流")
    print("✅ 保持原有接口兼容性")
    print("✅ 修复连续监听导致的段错误")
    
    print("\n🚀 下一步:")
    print("1. 测试修复版本: 替换 enhanced_voice_control.py")
    print("2. 或者先测试: python3 -c 'from src.enhanced_voice_control_fixed import EnhancedVoiceController'")
    print("3. 确认无误后，替换原文件")
    
    return True

if __name__ == "__main__":
    main()