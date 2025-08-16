#!/usr/bin/python3
"""
应用性能优化 - 将性能优化器集成到现有AI语音桌宠系统中
"""

import logging
import time
import threading
from typing import Optional

from performance_optimizer import PerformanceOptimizer
from ai_conversation import AIConversationManager
from enhanced_voice_control import EnhancedVoiceController
from expression_controller import ExpressionController
from emotion_engine import EmotionEngine
from memory_manager import MemoryManager
from personality_manager import PersonalityManager
from safety_manager import SafetyManager

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OptimizedAISystem:
    """优化后的AI系统 - 集成所有性能优化"""
    
    def __init__(self, robot_controller=None):
        """
        初始化优化后的AI系统
        Args:
            robot_controller: LOBOROBOT控制器实例
        """
        self.robot = robot_controller
        
        # 初始化核心组件
        logger.info("初始化核心组件...")
        self._initialize_core_components()
        
        # 初始化性能优化器
        logger.info("初始化性能优化器...")
        self.performance_optimizer = PerformanceOptimizer(
            ai_conversation_manager=self.ai_manager,
            enhanced_voice_controller=self.voice_controller,
            expression_controller=self.expression_controller,
            emotion_engine=self.emotion_engine,
            memory_manager=self.memory_manager
        )
        
        # 应用性能优化
        logger.info("应用性能优化...")
        self._apply_optimizations()
        
        # 系统状态
        self.system_running = False
        
        logger.info("优化后的AI系统初始化完成")
    
    def _initialize_core_components(self):
        """初始化核心组件"""
        try:
            # 初始化记忆管理器
            self.memory_manager = MemoryManager(
                data_dir="data/ai_memory",
                max_memory_entries=500  # 优化：减少内存条目数
            )
            
            # 初始化情感引擎
            self.emotion_engine = EmotionEngine()
            
            # 初始化表情控制器
            self.expression_controller = ExpressionController()
            
            # 初始化安全管理器
            self.safety_manager = SafetyManager(
                robot_controller=self.robot,
                expression_controller=self.expression_controller
            )
            
            # 初始化个性管理器
            self.personality_manager = PersonalityManager(
                robot_controller=self.robot,
                emotion_engine=self.emotion_engine,
                memory_manager=self.memory_manager,
                safety_manager=self.safety_manager
            )
            
            # 初始化AI对话管理器
            self.ai_manager = AIConversationManager(
                robot_controller=self.robot,
                expression_controller=self.expression_controller,
                safety_manager=self.safety_manager
            )
            
            # 初始化增强语音控制器
            self.voice_controller = EnhancedVoiceController(
                robot=self.robot,
                ai_conversation_manager=self.ai_manager,
                expression_controller=self.expression_controller,
                safety_manager=self.safety_manager
            )
            
            logger.info("核心组件初始化完成")
            
        except Exception as e:
            logger.error(f"核心组件初始化失败: {e}")
            raise
    
    def _apply_optimizations(self):
        """应用性能优化"""
        try:
            # 启动性能优化器
            self.performance_optimizer.start_optimization()
            
            # 应用语音识别优化
            self._optimize_voice_recognition()
            
            # 应用AI响应优化
            self._optimize_ai_responses()
            
            # 应用动画同步优化
            self._optimize_animation_sync()
            
            # 应用内存管理优化
            self._optimize_memory_management()
            
            # 应用情感检测优化
            self._optimize_emotion_detection()
            
            logger.info("所有性能优化已应用")
            
        except Exception as e:
            logger.error(f"性能优化应用失败: {e}")
    
    def _optimize_voice_recognition(self):
        """优化语音识别"""
        try:
            if not self.voice_controller:
                return
            
            # 集成延迟测量
            original_process_audio = self.voice_controller._process_conversation_audio
            
            def optimized_process_audio(audio):
                start_time = time.time()
                
                # 调用原始处理方法
                result = original_process_audio(audio)
                
                # 测量延迟
                self.performance_optimizer.measure_response_latency(start_time, 'speech_recognition')
                
                return result
            
            # 替换方法
            self.voice_controller._process_conversation_audio = optimized_process_audio
            
            logger.info("语音识别优化已应用")
            
        except Exception as e:
            logger.error(f"语音识别优化失败: {e}")
    
    def _optimize_ai_responses(self):
        """优化AI响应"""
        try:
            if not self.ai_manager:
                return
            
            # 集成响应缓存和延迟测量
            original_process_input = self.ai_manager.process_user_input
            
            def optimized_process_input(user_text):
                start_time = time.time()
                
                # 检查响应缓存
                cache_key = user_text.strip().lower()
                if cache_key in self.performance_optimizer.response_cache:
                    logger.debug(f"使用缓存响应: {cache_key}")
                    cached_response = self.performance_optimizer.response_cache[cache_key]
                    
                    # 创建缓存响应上下文
                    from ai_conversation import ConversationContext
                    from datetime import datetime
                    
                    context = ConversationContext(
                        session_id=self.ai_manager.current_session_id or "cached",
                        user_input=user_text,
                        ai_response=cached_response,
                        emotion_detected="neutral",
                        timestamp=datetime.now()
                    )
                    
                    # 测量缓存响应延迟
                    self.performance_optimizer.measure_response_latency(start_time, 'ai_response')
                    
                    return context
                
                # 调用原始处理方法
                result = original_process_input(user_text)
                
                # 测量AI响应延迟
                self.performance_optimizer.measure_response_latency(start_time, 'ai_response')
                
                # 缓存常用响应
                if result and len(user_text) < 20:  # 只缓存短问题的回答
                    self.performance_optimizer.response_cache[cache_key] = result.ai_response
                
                return result
            
            # 替换方法
            self.ai_manager.process_user_input = optimized_process_input
            
            logger.info("AI响应优化已应用")
            
        except Exception as e:
            logger.error(f"AI响应优化失败: {e}")
    
    def _optimize_animation_sync(self):
        """优化动画同步"""
        try:
            if not self.voice_controller:
                return
            
            # 集成动画同步
            original_speak_text = self.voice_controller.speak_text
            
            def optimized_speak_text(text, priority=False):
                # 调度动画同步
                self.performance_optimizer.schedule_animation_sync(
                    'speaking',
                    text=text,
                    start_time=time.time() + 0.1  # 预留100ms同步时间
                )
                
                # 调用原始方法
                return original_speak_text(text, priority)
            
            # 替换方法
            self.voice_controller.speak_text = optimized_speak_text
            
            # 优化情感表达同步
            if self.personality_manager:
                original_execute_movement = self.personality_manager.execute_emotional_movement
                
                def optimized_execute_movement(emotion, intensity=0.5, context=None):
                    # 调度情感动画同步
                    self.performance_optimizer.schedule_animation_sync(
                        'emotion',
                        emotion=emotion.value if hasattr(emotion, 'value') else str(emotion)
                    )
                    
                    # 调用原始方法
                    return original_execute_movement(emotion, intensity, context)
                
                # 替换方法
                self.personality_manager.execute_emotional_movement = optimized_execute_movement
            
            logger.info("动画同步优化已应用")
            
        except Exception as e:
            logger.error(f"动画同步优化失败: {e}")
    
    def _optimize_memory_management(self):
        """优化内存管理"""
        try:
            # 调整记忆管理器参数
            if self.memory_manager:
                # 减少缓存大小
                self.memory_manager.max_cache_size = min(50, self.memory_manager.max_cache_size)
                
                # 更频繁的清理
                original_store_conversation = self.memory_manager.store_conversation
                
                def optimized_store_conversation(session_id, user_input, ai_response, emotion_detected, context_summary=""):
                    # 调用原始方法
                    result = original_store_conversation(session_id, user_input, ai_response, emotion_detected, context_summary)
                    
                    # 检查是否需要清理
                    if len(self.memory_manager.conversation_cache) > 80:  # 80%阈值
                        # 异步清理旧条目
                        threading.Thread(
                            target=self._cleanup_old_conversations,
                            daemon=True
                        ).start()
                    
                    return result
                
                # 替换方法
                self.memory_manager.store_conversation = optimized_store_conversation
            
            # 调整AI管理器历史长度
            if self.ai_manager:
                self.ai_manager.max_history_length = min(20, getattr(self.ai_manager, 'max_history_length', 50))
            
            logger.info("内存管理优化已应用")
            
        except Exception as e:
            logger.error(f"内存管理优化失败: {e}")
    
    def _optimize_emotion_detection(self):
        """优化情感检测"""
        try:
            if not self.emotion_engine:
                return
            
            # 集成情感检测精度测量
            original_analyze = self.emotion_engine.analyze_response_emotion
            
            def optimized_analyze(text, context=None):
                start_time = time.time()
                
                # 调用原始分析
                result = original_analyze(text, context)
                
                # 计算检测精度（基于置信度）
                confidence = getattr(result, 'confidence', 0.8)  # 默认置信度
                self.performance_optimizer.metrics.emotion_detection_accuracy = confidence
                
                return result
            
            # 替换方法
            self.emotion_engine.analyze_response_emotion = optimized_analyze
            
            logger.info("情感检测优化已应用")
            
        except Exception as e:
            logger.error(f"情感检测优化失败: {e}")
    
    def _cleanup_old_conversations(self):
        """清理旧对话"""
        try:
            if self.memory_manager and hasattr(self.memory_manager, 'conversation_cache'):
                cache = self.memory_manager.conversation_cache
                if len(cache) > 50:
                    # 保留最近50条对话
                    self.memory_manager.conversation_cache = cache[-50:]
                    logger.debug("已清理旧对话记录")
        except Exception as e:
            logger.error(f"对话清理失败: {e}")
    
    def start_system(self):
        """启动优化后的AI系统"""
        try:
            if self.system_running:
                logger.warning("系统已在运行")
                return False
            
            logger.info("启动优化后的AI系统...")
            
            # 启动安全监控
            if self.safety_manager:
                self.safety_manager.start_monitoring()
            
            # 启动对话模式
            if self.voice_controller:
                success = self.voice_controller.start_conversation_mode()
                if not success:
                    logger.error("对话模式启动失败")
                    return False
            
            # 启动语音监听
            if self.voice_controller:
                listen_thread = threading.Thread(
                    target=self.voice_controller.listen_continuously,
                    daemon=True
                )
                listen_thread.start()
            
            self.system_running = True
            logger.info("优化后的AI系统启动成功")
            
            # 显示性能报告
            self._show_performance_report()
            
            return True
            
        except Exception as e:
            logger.error(f"系统启动失败: {e}")
            return False
    
    def stop_system(self):
        """停止AI系统"""
        try:
            if not self.system_running:
                return
            
            logger.info("停止AI系统...")
            
            # 停止对话模式
            if self.voice_controller:
                self.voice_controller.stop_conversation_mode()
            
            # 停止安全监控
            if self.safety_manager:
                self.safety_manager.stop_monitoring()
            
            # 停止性能优化器
            if self.performance_optimizer:
                self.performance_optimizer.stop_optimization()
            
            # 清理表情控制器
            if self.expression_controller:
                self.expression_controller.cleanup()
            
            self.system_running = False
            logger.info("AI系统已停止")
            
        except Exception as e:
            logger.error(f"系统停止失败: {e}")
    
    def _show_performance_report(self):
        """显示性能报告"""
        try:
            report = self.performance_optimizer.get_performance_report()
            
            logger.info("=== 性能优化报告 ===")
            logger.info(f"应用的优化: {report.get('optimizations_applied', {})}")
            
            current_metrics = report.get('current_metrics', {})
            if current_metrics:
                logger.info("当前性能指标:")
                for key, value in current_metrics.items():
                    if isinstance(value, float):
                        logger.info(f"  {key}: {value:.3f}")
                    else:
                        logger.info(f"  {key}: {value}")
            
            cache_stats = report.get('cache_stats', {})
            if cache_stats:
                logger.info("缓存统计:")
                for key, value in cache_stats.items():
                    logger.info(f"  {key}: {value}")
            
        except Exception as e:
            logger.error(f"性能报告显示失败: {e}")
    
    def get_system_status(self) -> dict:
        """获取系统状态"""
        try:
            status = {
                'system_running': self.system_running,
                'components_status': {},
                'performance_metrics': {}
            }
            
            # 组件状态
            if self.ai_manager:
                status['components_status']['ai_manager'] = self.ai_manager.get_status()
            
            if self.voice_controller:
                status['components_status']['voice_controller'] = self.voice_controller.get_conversation_status()
            
            if self.emotion_engine:
                status['components_status']['emotion_engine'] = self.emotion_engine.get_status()
            
            if self.personality_manager:
                status['components_status']['personality_manager'] = self.personality_manager.get_status()
            
            if self.safety_manager:
                status['components_status']['safety_manager'] = self.safety_manager.safety_state.to_dict()
            
            # 性能指标
            if self.performance_optimizer:
                status['performance_metrics'] = self.performance_optimizer.get_performance_report()
            
            return status
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {'error': str(e)}
    
    def force_performance_cleanup(self):
        """强制执行性能清理"""
        try:
            logger.info("执行强制性能清理...")
            
            if self.performance_optimizer:
                self.performance_optimizer._perform_memory_cleanup()
            
            # 清理各组件缓存
            if self.ai_manager and hasattr(self.ai_manager, 'conversation_history'):
                history = self.ai_manager.conversation_history
                if len(history) > 10:
                    self.ai_manager.conversation_history = history[-10:]
            
            if self.memory_manager:
                self.memory_manager.cleanup_old_data(days_to_keep=7)  # 只保留7天数据
            
            # 强制垃圾回收
            import gc
            collected = gc.collect()
            
            logger.info(f"强制清理完成，回收了 {collected} 个对象")
            
        except Exception as e:
            logger.error(f"强制清理失败: {e}")

# 测试和演示函数
def test_optimized_system():
    """测试优化后的系统"""
    print("=== 优化后AI系统测试 ===")
    
    # 创建优化后的系统
    system = OptimizedAISystem()
    
    try:
        # 启动系统
        if system.start_system():
            print("系统启动成功")
            
            # 显示系统状态
            status = system.get_system_status()
            print(f"\n系统状态: {status['system_running']}")
            
            # 运行一段时间
            print("系统运行中... (按Ctrl+C停止)")
            while True:
                time.sleep(10)
                
                # 定期显示性能指标
                report = system.performance_optimizer.get_performance_report()
                current_metrics = report.get('current_metrics', {})
                print(f"当前性能: 内存 {current_metrics.get('memory_usage_mb', 0):.1f}MB, "
                      f"CPU {current_metrics.get('cpu_usage_percent', 0):.1f}%, "
                      f"总响应时间 {current_metrics.get('total_response_time', 0):.3f}s")
        else:
            print("系统启动失败")
            
    except KeyboardInterrupt:
        print("\n正在停止系统...")
        system.stop_system()
        print("系统已停止")
    except Exception as e:
        print(f"系统运行错误: {e}")
        system.stop_system()

if __name__ == "__main__":
    test_optimized_system()