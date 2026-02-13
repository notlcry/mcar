#!/usr/bin/python3
"""
性能优化器 - 优化AI语音桌宠的性能和用户体验
包括语音识别延迟优化、动画同步、内存管理和情感检测精度提升
"""

import time
import threading
import logging
import queue
import asyncio
import gc
import psutil
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Tuple, Any
from collections import deque
import numpy as np
import json
import os

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """性能指标数据模型"""
    speech_recognition_latency: float = 0.0
    ai_response_latency: float = 0.0
    tts_generation_latency: float = 0.0
    animation_sync_accuracy: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    emotion_detection_accuracy: float = 0.0
    total_response_time: float = 0.0
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'speech_recognition_latency': self.speech_recognition_latency,
            'ai_response_latency': self.ai_response_latency,
            'tts_generation_latency': self.tts_generation_latency,
            'animation_sync_accuracy': self.animation_sync_accuracy,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'emotion_detection_accuracy': self.emotion_detection_accuracy,
            'total_response_time': self.total_response_time
        }

@dataclass
class OptimizationConfig:
    """优化配置"""
    # 语音识别优化
    whisper_model_size: str = "base"  # tiny, base, small, medium, large
    speech_timeout: float = 2.0
    phrase_time_limit: float = 8.0
    energy_threshold: int = 300
    
    # AI响应优化
    max_tokens: int = 150
    temperature: float = 0.7
    response_cache_size: int = 50
    
    # TTS优化
    tts_rate: str = "+10%"  # 稍微加快语速
    tts_quality: str = "medium"  # low, medium, high
    audio_buffer_size: int = 1024
    
    # 动画同步优化
    animation_fps: float = 15.0
    sync_tolerance_ms: float = 50.0
    preload_animations: bool = True
    
    # 内存优化
    max_conversation_cache: int = 100
    memory_cleanup_interval: float = 300.0  # 5分钟
    gc_threshold: float = 80.0  # 内存使用率阈值
    
    # 情感检测优化
    emotion_smoothing_window: int = 3
    confidence_threshold: float = 0.6
    emotion_cache_size: int = 20

class PerformanceOptimizer:
    """性能优化器 - 提升系统整体性能和用户体验"""
    
    def __init__(self, ai_conversation_manager=None, enhanced_voice_controller=None,
                 expression_controller=None, emotion_engine=None, memory_manager=None):
        """
        初始化性能优化器
        Args:
            ai_conversation_manager: AI对话管理器
            enhanced_voice_controller: 增强语音控制器
            expression_controller: 表情控制器
            emotion_engine: 情感引擎
            memory_manager: 记忆管理器
        """
        self.ai_manager = ai_conversation_manager
        self.voice_controller = enhanced_voice_controller
        self.expression_controller = expression_controller
        self.emotion_engine = emotion_engine
        self.memory_manager = memory_manager
        
        # 优化配置
        self.config = OptimizationConfig()
        
        # 性能指标
        self.metrics = PerformanceMetrics()
        self.metrics_history = deque(maxlen=100)
        
        # 缓存系统
        self.response_cache = {}
        self.animation_cache = {}
        self.emotion_cache = deque(maxlen=self.config.emotion_cache_size)
        
        # 同步控制
        self.sync_queue = queue.Queue()
        self.animation_sync_thread = None
        self.memory_cleanup_thread = None
        
        # 性能监控
        self.monitoring_active = False
        self.performance_monitor_thread = None
        
        # 优化状态
        self.optimizations_applied = {
            'speech_recognition': False,
            'ai_response': False,
            'tts_generation': False,
            'animation_sync': False,
            'memory_management': False,
            'emotion_detection': False
        }
        
        logger.info("性能优化器初始化完成")
    
    def start_optimization(self):
        """启动性能优化"""
        logger.info("开始应用性能优化...")
        
        # 应用各项优化
        self._optimize_speech_recognition()
        self._optimize_ai_response()
        self._optimize_tts_generation()
        self._optimize_animation_sync()
        self._optimize_memory_management()
        self._optimize_emotion_detection()
        
        # 启动监控线程
        self._start_monitoring()
        
        logger.info("性能优化启动完成")
    
    def _optimize_speech_recognition(self):
        """优化语音识别延迟"""
        try:
            if not self.voice_controller:
                return
            
            logger.info("优化语音识别延迟...")
            
            # 调整Whisper模型大小以平衡速度和准确性
            if hasattr(self.voice_controller, 'whisper_recognizer') and self.voice_controller.whisper_recognizer:
                # 如果当前使用的不是最优模型，建议切换
                current_model = getattr(self.voice_controller.whisper_recognizer, 'model_size', 'base')
                if current_model != self.config.whisper_model_size:
                    logger.info(f"建议将Whisper模型从 {current_model} 切换到 {self.config.whisper_model_size}")
            
            # 优化语音识别参数
            if hasattr(self.voice_controller, 'recognizer'):
                recognizer = self.voice_controller.recognizer
                
                # 调整能量阈值以减少误触发
                recognizer.energy_threshold = self.config.energy_threshold
                
                # 优化超时设置
                recognizer.timeout = 1.0  # 减少等待时间
                recognizer.phrase_time_limit = self.config.phrase_time_limit
                
                # 调整暂停阈值
                recognizer.pause_threshold = 0.6  # 减少暂停检测时间
                
                logger.info("语音识别参数已优化")
            
            # 预热语音识别系统
            self._preheat_speech_recognition()
            
            self.optimizations_applied['speech_recognition'] = True
            
        except Exception as e:
            logger.error(f"语音识别优化失败: {e}")
    
    def _optimize_ai_response(self):
        """优化AI响应延迟"""
        try:
            if not self.ai_manager:
                return
            
            logger.info("优化AI响应延迟...")
            
            # 调整AI模型参数
            if hasattr(self.ai_manager, 'model') and self.ai_manager.model:
                # 优化生成配置
                if hasattr(self.ai_manager.model, '_generation_config'):
                    config = self.ai_manager.model._generation_config
                    config.max_output_tokens = self.config.max_tokens
                    config.temperature = self.config.temperature
                    
                    logger.info("AI生成参数已优化")
            
            # 实现响应缓存
            self._implement_response_cache()
            
            # 预加载常用响应模板
            self._preload_response_templates()
            
            self.optimizations_applied['ai_response'] = True
            
        except Exception as e:
            logger.error(f"AI响应优化失败: {e}")
    
    def _optimize_tts_generation(self):
        """优化TTS语音生成"""
        try:
            if not self.voice_controller:
                return
            
            logger.info("优化TTS语音生成...")
            
            # 调整TTS参数以提高速度
            if hasattr(self.voice_controller, 'set_tts_parameters'):
                self.voice_controller.set_tts_parameters(
                    rate=self.config.tts_rate,
                    volume="+0%"
                )
            
            # 优化音频播放缓冲区
            if hasattr(self.voice_controller, '_initialize_audio_playback'):
                # 调整pygame音频缓冲区大小
                try:
                    import pygame
                    pygame.mixer.quit()
                    pygame.mixer.init(
                        frequency=22050, 
                        size=-16, 
                        channels=2, 
                        buffer=self.config.audio_buffer_size
                    )
                    logger.info("音频缓冲区已优化")
                except:
                    pass
            
            # 实现TTS缓存
            self._implement_tts_cache()
            
            self.optimizations_applied['tts_generation'] = True
            
        except Exception as e:
            logger.error(f"TTS优化失败: {e}")
    
    def _optimize_animation_sync(self):
        """优化动画和语音同步"""
        try:
            if not self.expression_controller:
                return
            
            logger.info("优化动画和语音同步...")
            
            # 调整动画帧率
            if hasattr(self.expression_controller, 'config'):
                self.expression_controller.config.animation_fps = self.config.animation_fps
            
            # 启动动画同步线程
            self._start_animation_sync_thread()
            
            # 预加载动画帧
            if self.config.preload_animations:
                self._preload_animations()
            
            self.optimizations_applied['animation_sync'] = True
            
        except Exception as e:
            logger.error(f"动画同步优化失败: {e}")
    
    def _optimize_memory_management(self):
        """优化内存使用和对话历史管理"""
        try:
            logger.info("优化内存使用和对话历史管理...")
            
            # 优化对话历史缓存
            if self.ai_manager and hasattr(self.ai_manager, 'max_history_length'):
                self.ai_manager.max_history_length = self.config.max_conversation_cache
            
            # 优化记忆管理器缓存
            if self.memory_manager:
                if hasattr(self.memory_manager, 'max_cache_size'):
                    self.memory_manager.max_cache_size = min(
                        self.memory_manager.max_cache_size, 
                        self.config.max_conversation_cache
                    )
            
            # 启动内存清理线程
            self._start_memory_cleanup_thread()
            
            # 优化垃圾回收
            self._optimize_garbage_collection()
            
            self.optimizations_applied['memory_management'] = True
            
        except Exception as e:
            logger.error(f"内存管理优化失败: {e}")
    
    def _optimize_emotion_detection(self):
        """优化情感检测算法准确性"""
        try:
            if not self.emotion_engine:
                return
            
            logger.info("优化情感检测算法准确性...")
            
            # 实现情感平滑算法
            self._implement_emotion_smoothing()
            
            # 调整情感检测阈值
            self._tune_emotion_thresholds()
            
            # 增强情感上下文分析
            self._enhance_emotion_context_analysis()
            
            self.optimizations_applied['emotion_detection'] = True
            
        except Exception as e:
            logger.error(f"情感检测优化失败: {e}")
    
    def _preheat_speech_recognition(self):
        """预热语音识别系统"""
        try:
            if not self.voice_controller or not hasattr(self.voice_controller, 'whisper_recognizer'):
                return
            
            # 创建一个短暂的测试音频来预热模型
            import tempfile
            import wave
            import numpy as np
            
            # 生成1秒的静音音频
            sample_rate = 16000
            duration = 1.0
            samples = np.zeros(int(sample_rate * duration), dtype=np.int16)
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                with wave.open(temp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(samples.tobytes())
                
                # 使用测试音频预热Whisper
                if self.voice_controller.whisper_recognizer:
                    try:
                        self.voice_controller.whisper_recognizer.recognize_audio_file(temp_file.name)
                        logger.info("语音识别系统预热完成")
                    except:
                        pass
                
                # 清理临时文件
                os.unlink(temp_file.name)
                
        except Exception as e:
            logger.debug(f"语音识别预热失败: {e}")
    
    def _implement_response_cache(self):
        """实现AI响应缓存"""
        try:
            # 为常见问题创建缓存
            common_responses = {
                "你好": "你好！我是快快，很高兴见到你！",
                "你是谁": "我是快快，你的AI语音桌宠伙伴！",
                "你能做什么": "我可以和你聊天、做各种动作、表达情感，还能记住我们的对话呢！",
                "再见": "再见！有需要随时叫我哦~",
                "谢谢": "不客气！能帮到你我很开心！"
            }
            
            self.response_cache.update(common_responses)
            logger.info(f"已缓存 {len(common_responses)} 个常用响应")
            
        except Exception as e:
            logger.error(f"响应缓存实现失败: {e}")
    
    def _preload_response_templates(self):
        """预加载响应模板"""
        try:
            # 预定义响应模板
            templates = {
                "greeting": ["你好！", "嗨！", "很高兴见到你！"],
                "confirmation": ["好的！", "明白了！", "收到！"],
                "thinking": ["让我想想...", "嗯...", "这个问题很有趣..."],
                "error": ["抱歉，我没理解", "请再说一遍", "我有点困惑"]
            }
            
            # 将模板添加到缓存
            for category, responses in templates.items():
                for i, response in enumerate(responses):
                    cache_key = f"template_{category}_{i}"
                    self.response_cache[cache_key] = response
            
            logger.info("响应模板预加载完成")
            
        except Exception as e:
            logger.error(f"响应模板预加载失败: {e}")
    
    def _implement_tts_cache(self):
        """实现TTS缓存"""
        try:
            # 为常用短语预生成音频
            common_phrases = [
                "好的", "明白了", "让我想想", "抱歉", "谢谢", 
                "你好", "再见", "我在听", "请说", "收到"
            ]
            
            # 这里可以预生成音频文件并缓存
            # 由于实际生成需要异步操作，这里只是标记需要缓存的内容
            self.tts_cache_targets = common_phrases
            logger.info(f"标记了 {len(common_phrases)} 个短语用于TTS缓存")
            
        except Exception as e:
            logger.error(f"TTS缓存实现失败: {e}")
    
    def _start_animation_sync_thread(self):
        """启动动画同步线程"""
        try:
            if self.animation_sync_thread and self.animation_sync_thread.is_alive():
                return
            
            def sync_worker():
                while self.monitoring_active:
                    try:
                        # 从队列获取同步任务
                        sync_task = self.sync_queue.get(timeout=1.0)
                        
                        if sync_task['type'] == 'speaking':
                            self._sync_speaking_animation(sync_task)
                        elif sync_task['type'] == 'emotion':
                            self._sync_emotion_animation(sync_task)
                        
                        self.sync_queue.task_done()
                        
                    except queue.Empty:
                        continue
                    except Exception as e:
                        logger.error(f"动画同步错误: {e}")
            
            self.animation_sync_thread = threading.Thread(target=sync_worker, daemon=True)
            self.animation_sync_thread.start()
            
            logger.info("动画同步线程已启动")
            
        except Exception as e:
            logger.error(f"动画同步线程启动失败: {e}")
    
    def _preload_animations(self):
        """预加载动画帧"""
        try:
            if not self.expression_controller:
                return
            
            # 预生成常用表情的动画帧
            emotions = ['happy', 'sad', 'surprised', 'confused', 'thinking', 'neutral']
            
            for emotion in emotions:
                try:
                    # 这里可以预生成动画帧并缓存
                    # 由于实际生成需要PIL操作，这里只是标记
                    self.animation_cache[emotion] = f"preloaded_{emotion}"
                except Exception as e:
                    logger.debug(f"预加载 {emotion} 动画失败: {e}")
            
            logger.info(f"已预加载 {len(emotions)} 个表情动画")
            
        except Exception as e:
            logger.error(f"动画预加载失败: {e}")
    
    def _start_memory_cleanup_thread(self):
        """启动内存清理线程"""
        try:
            if self.memory_cleanup_thread and self.memory_cleanup_thread.is_alive():
                return
            
            def cleanup_worker():
                while self.monitoring_active:
                    try:
                        # 检查内存使用情况
                        memory_percent = psutil.virtual_memory().percent
                        
                        if memory_percent > self.config.gc_threshold:
                            logger.info(f"内存使用率 {memory_percent:.1f}%，开始清理...")
                            self._perform_memory_cleanup()
                        
                        time.sleep(self.config.memory_cleanup_interval)
                        
                    except Exception as e:
                        logger.error(f"内存清理错误: {e}")
                        time.sleep(60)  # 出错时等待1分钟
            
            self.memory_cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
            self.memory_cleanup_thread.start()
            
            logger.info("内存清理线程已启动")
            
        except Exception as e:
            logger.error(f"内存清理线程启动失败: {e}")
    
    def _optimize_garbage_collection(self):
        """优化垃圾回收"""
        try:
            # 调整垃圾回收阈值
            import gc
            
            # 获取当前阈值
            thresholds = gc.get_threshold()
            
            # 调整为更积极的垃圾回收
            new_thresholds = (
                max(100, thresholds[0] // 2),  # 减少第0代阈值
                max(10, thresholds[1] // 2),   # 减少第1代阈值
                max(10, thresholds[2] // 2)    # 减少第2代阈值
            )
            
            gc.set_threshold(*new_thresholds)
            
            # 启用垃圾回收调试（仅在开发环境）
            if logger.level <= logging.DEBUG:
                gc.set_debug(gc.DEBUG_STATS)
            
            logger.info(f"垃圾回收阈值已调整: {thresholds} -> {new_thresholds}")
            
        except Exception as e:
            logger.error(f"垃圾回收优化失败: {e}")
    
    def _implement_emotion_smoothing(self):
        """实现情感平滑算法"""
        try:
            if not self.emotion_engine:
                return
            
            # 保存原始的情感分析方法
            original_analyze = self.emotion_engine.analyze_response_emotion
            
            def smoothed_analyze(text, context=None):
                # 调用原始分析
                raw_emotion = original_analyze(text, context)
                
                # 添加到缓存
                self.emotion_cache.append({
                    'emotion': raw_emotion.primary_emotion,
                    'intensity': raw_emotion.intensity,
                    'timestamp': datetime.now()
                })
                
                # 应用平滑算法
                if len(self.emotion_cache) >= self.config.emotion_smoothing_window:
                    smoothed_emotion = self._calculate_smoothed_emotion()
                    raw_emotion.primary_emotion = smoothed_emotion['emotion']
                    raw_emotion.intensity = smoothed_emotion['intensity']
                
                return raw_emotion
            
            # 替换方法
            self.emotion_engine.analyze_response_emotion = smoothed_analyze
            
            logger.info("情感平滑算法已实现")
            
        except Exception as e:
            logger.error(f"情感平滑算法实现失败: {e}")
    
    def _calculate_smoothed_emotion(self) -> Dict:
        """计算平滑后的情感"""
        try:
            recent_emotions = list(self.emotion_cache)[-self.config.emotion_smoothing_window:]
            
            # 统计情感类型
            emotion_counts = {}
            intensity_sum = 0.0
            
            for entry in recent_emotions:
                emotion = entry['emotion']
                intensity = entry['intensity']
                
                if emotion not in emotion_counts:
                    emotion_counts[emotion] = []
                emotion_counts[emotion].append(intensity)
                intensity_sum += intensity
            
            # 选择最频繁的情感
            dominant_emotion = max(emotion_counts.keys(), 
                                 key=lambda e: len(emotion_counts[e]))
            
            # 计算平均强度
            avg_intensity = intensity_sum / len(recent_emotions)
            
            # 应用置信度阈值
            confidence = len(emotion_counts[dominant_emotion]) / len(recent_emotions)
            if confidence < self.config.confidence_threshold:
                # 置信度不足，使用中性情感
                from emotion_engine import EmotionType
                dominant_emotion = EmotionType.NEUTRAL
                avg_intensity = 0.5
            
            return {
                'emotion': dominant_emotion,
                'intensity': avg_intensity,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"情感平滑计算失败: {e}")
            from emotion_engine import EmotionType
            return {
                'emotion': EmotionType.NEUTRAL,
                'intensity': 0.5,
                'confidence': 0.0
            }
    
    def _tune_emotion_thresholds(self):
        """调整情感检测阈值"""
        try:
            if not self.emotion_engine or not hasattr(self.emotion_engine, 'emotion_keywords'):
                return
            
            # 调整情感关键词权重
            for emotion_type, emotion_data in self.emotion_engine.emotion_keywords.items():
                # 提高高置信度情感的权重
                if emotion_type.value in ['happy', 'excited', 'sad']:
                    emotion_data['weight'] *= 1.1
                # 降低容易误判的情感权重
                elif emotion_type.value in ['confused', 'thinking']:
                    emotion_data['weight'] *= 0.9
            
            # 调整强度修饰词权重
            if hasattr(self.emotion_engine, 'intensity_modifiers'):
                for modifier, weight in self.emotion_engine.intensity_modifiers.items():
                    # 适度调整修饰词影响
                    if weight > 1.5:
                        self.emotion_engine.intensity_modifiers[modifier] = min(weight, 1.8)
                    elif weight < 0.5:
                        self.emotion_engine.intensity_modifiers[modifier] = max(weight, 0.3)
            
            logger.info("情感检测阈值已调整")
            
        except Exception as e:
            logger.error(f"情感阈值调整失败: {e}")
    
    def _enhance_emotion_context_analysis(self):
        """增强情感上下文分析"""
        try:
            if not self.emotion_engine:
                return
            
            # 保存原始的上下文更新方法
            if hasattr(self.emotion_engine, 'update_personality_context'):
                original_update = self.emotion_engine.update_personality_context
                
                def enhanced_update(conversation_history):
                    # 调用原始更新
                    original_update(conversation_history)
                    
                    # 增强上下文分析
                    if len(conversation_history) >= 3:
                        # 分析情感趋势
                        recent_emotions = [item.get('emotion', 'neutral') 
                                         for item in conversation_history[-3:]]
                        
                        # 检测情感一致性
                        if len(set(recent_emotions)) == 1:
                            # 情感一致，增强当前情感
                            current_state = self.emotion_engine.get_current_emotional_state()
                            if current_state:
                                current_state.intensity = min(1.0, current_state.intensity * 1.1)
                        
                        # 检测情感波动
                        elif len(set(recent_emotions)) == len(recent_emotions):
                            # 情感波动大，降低强度
                            current_state = self.emotion_engine.get_current_emotional_state()
                            if current_state:
                                current_state.intensity *= 0.9
                
                # 替换方法
                self.emotion_engine.update_personality_context = enhanced_update
            
            logger.info("情感上下文分析已增强")
            
        except Exception as e:
            logger.error(f"情感上下文分析增强失败: {e}")
    
    def _start_monitoring(self):
        """启动性能监控"""
        try:
            self.monitoring_active = True
            
            def monitor_worker():
                while self.monitoring_active:
                    try:
                        # 收集性能指标
                        self._collect_performance_metrics()
                        
                        # 记录到历史
                        self.metrics_history.append({
                            'timestamp': datetime.now(),
                            'metrics': self.metrics.to_dict()
                        })
                        
                        time.sleep(10.0)  # 每10秒收集一次
                        
                    except Exception as e:
                        logger.error(f"性能监控错误: {e}")
                        time.sleep(10.0)
            
            self.performance_monitor_thread = threading.Thread(target=monitor_worker, daemon=True)
            self.performance_monitor_thread.start()
            
            logger.info("性能监控已启动")
            
        except Exception as e:
            logger.error(f"性能监控启动失败: {e}")
    
    def _collect_performance_metrics(self):
        """收集性能指标"""
        try:
            # 系统资源指标
            self.metrics.memory_usage_mb = psutil.virtual_memory().used / (1024 * 1024)
            self.metrics.cpu_usage_percent = psutil.cpu_percent(interval=0.1)
            
            # 计算平均响应时间
            if len(self.metrics_history) > 0:
                recent_metrics = [entry['metrics'] for entry in list(self.metrics_history)[-10:]]
                if recent_metrics:
                    avg_total_time = sum(m.get('total_response_time', 0) for m in recent_metrics) / len(recent_metrics)
                    self.metrics.total_response_time = avg_total_time
            
        except Exception as e:
            logger.error(f"性能指标收集失败: {e}")
    
    def _perform_memory_cleanup(self):
        """执行内存清理"""
        try:
            logger.info("开始内存清理...")
            
            # 清理响应缓存
            if len(self.response_cache) > self.config.response_cache_size:
                # 保留最近使用的缓存项
                cache_items = list(self.response_cache.items())
                self.response_cache = dict(cache_items[-self.config.response_cache_size:])
            
            # 清理对话历史缓存
            if self.ai_manager and hasattr(self.ai_manager, 'conversation_history'):
                history = self.ai_manager.conversation_history
                if len(history) > self.config.max_conversation_cache:
                    self.ai_manager.conversation_history = history[-self.config.max_conversation_cache:]
            
            # 清理记忆管理器缓存
            if self.memory_manager and hasattr(self.memory_manager, 'conversation_cache'):
                cache = self.memory_manager.conversation_cache
                if len(cache) > self.config.max_conversation_cache:
                    self.memory_manager.conversation_cache = cache[-self.config.max_conversation_cache:]
            
            # 强制垃圾回收
            import gc
            collected = gc.collect()
            
            logger.info(f"内存清理完成，回收了 {collected} 个对象")
            
        except Exception as e:
            logger.error(f"内存清理失败: {e}")
    
    def _sync_speaking_animation(self, sync_task):
        """同步说话动画"""
        try:
            if not self.expression_controller:
                return
            
            text = sync_task.get('text', '')
            start_time = sync_task.get('start_time', time.time())
            
            # 估算说话时长
            estimated_duration = len(text) * 0.12  # 优化后的估算：每字0.12秒
            
            # 计算同步延迟
            current_time = time.time()
            sync_delay = max(0, start_time - current_time)
            
            if sync_delay > 0:
                time.sleep(sync_delay)
            
            # 启动说话动画
            self.expression_controller.animate_speaking(estimated_duration)
            
            # 记录同步精度
            actual_delay = time.time() - start_time
            sync_accuracy = max(0, 1.0 - abs(actual_delay * 1000) / self.config.sync_tolerance_ms)
            self.metrics.animation_sync_accuracy = sync_accuracy
            
        except Exception as e:
            logger.error(f"说话动画同步失败: {e}")
    
    def _sync_emotion_animation(self, sync_task):
        """同步情感动画"""
        try:
            if not self.expression_controller:
                return
            
            emotion = sync_task.get('emotion', 'neutral')
            
            # 显示情感表情
            self.expression_controller.show_emotion(emotion)
            
        except Exception as e:
            logger.error(f"情感动画同步失败: {e}")
    
    def measure_response_latency(self, start_time: float, stage: str):
        """测量响应延迟"""
        try:
            latency = time.time() - start_time
            
            if stage == 'speech_recognition':
                self.metrics.speech_recognition_latency = latency
            elif stage == 'ai_response':
                self.metrics.ai_response_latency = latency
            elif stage == 'tts_generation':
                self.metrics.tts_generation_latency = latency
            
            # 更新总响应时间
            self.metrics.total_response_time = (
                self.metrics.speech_recognition_latency +
                self.metrics.ai_response_latency +
                self.metrics.tts_generation_latency
            )
            
        except Exception as e:
            logger.error(f"延迟测量失败: {e}")
    
    def schedule_animation_sync(self, sync_type: str, **kwargs):
        """调度动画同步任务"""
        try:
            sync_task = {
                'type': sync_type,
                'timestamp': time.time(),
                **kwargs
            }
            
            self.sync_queue.put(sync_task)
            
        except Exception as e:
            logger.error(f"动画同步调度失败: {e}")
    
    def get_performance_report(self) -> Dict:
        """获取性能报告"""
        try:
            # 计算平均指标
            if len(self.metrics_history) > 0:
                recent_metrics = [entry['metrics'] for entry in list(self.metrics_history)[-10:]]
                
                avg_metrics = {}
                for key in self.metrics.to_dict().keys():
                    values = [m.get(key, 0) for m in recent_metrics if m.get(key, 0) > 0]
                    avg_metrics[f'avg_{key}'] = sum(values) / len(values) if values else 0
            else:
                avg_metrics = {}
            
            return {
                'current_metrics': self.metrics.to_dict(),
                'average_metrics': avg_metrics,
                'optimizations_applied': self.optimizations_applied,
                'cache_stats': {
                    'response_cache_size': len(self.response_cache),
                    'animation_cache_size': len(self.animation_cache),
                    'emotion_cache_size': len(self.emotion_cache)
                },
                'system_info': {
                    'memory_usage_mb': psutil.virtual_memory().used / (1024 * 1024),
                    'cpu_usage_percent': psutil.cpu_percent(),
                    'available_memory_mb': psutil.virtual_memory().available / (1024 * 1024)
                }
            }
            
        except Exception as e:
            logger.error(f"性能报告生成失败: {e}")
            return {}
    
    def stop_optimization(self):
        """停止性能优化"""
        logger.info("停止性能优化...")
        
        self.monitoring_active = False
        
        # 等待线程结束
        for thread in [self.animation_sync_thread, self.memory_cleanup_thread, self.performance_monitor_thread]:
            if thread and thread.is_alive():
                thread.join(timeout=2.0)
        
        logger.info("性能优化已停止")

# 测试函数
def test_performance_optimizer():
    """测试性能优化器"""
    print("=== 性能优化器测试 ===")
    
    # 创建性能优化器
    optimizer = PerformanceOptimizer()
    
    try:
        # 启动优化
        optimizer.start_optimization()
        
        print("性能优化已启动")
        print(f"应用的优化: {optimizer.optimizations_applied}")
        
        # 运行一段时间收集指标
        time.sleep(5)
        
        # 获取性能报告
        report = optimizer.get_performance_report()
        print("\n性能报告:")
        for key, value in report.items():
            print(f"  {key}: {value}")
        
        # 停止优化
        optimizer.stop_optimization()
        print("\n性能优化测试完成")
        
    except KeyboardInterrupt:
        print("\n测试被中断")
        optimizer.stop_optimization()

if __name__ == "__main__":
    test_performance_optimizer()