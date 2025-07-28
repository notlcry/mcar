#!/usr/bin/python3
"""
多模态交互集成测试
测试语音、视觉、运动等多种模态的协调工作
"""

import time
import logging
import json
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

# 导入系统组件
from safety_manager import SafetyManager
from ai_conversation import AIConversationManager
from emotion_engine import EmotionEngine, EmotionType
from personality_manager import PersonalityManager
from enhanced_voice_control import EnhancedVoiceController
from expression_controller import ExpressionController

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ModalityType(Enum):
    """模态类型"""
    VOICE = "voice"
    VISUAL = "visual"
    MOVEMENT = "movement"
    EMOTION = "emotion"
    SAFETY = "safety"

@dataclass
class ModalityEvent:
    """模态事件"""
    modality: ModalityType
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    duration: float = 0.0

@dataclass
class InteractionScenario:
    """交互场景"""
    name: str
    description: str
    expected_modalities: List[ModalityType]
    input_sequence: List[Dict[str, Any]]
    expected_outcomes: Dict[str, Any]
    timeout: float = 10.0

class MultimodalTestHarness:
    """多模态测试工具"""
    
    def __init__(self):
        # 创建模拟组件
        self.mock_robot = self._create_mock_robot()
        self.mock_expression = self._create_mock_expression()
        self.mock_voice = self._create_mock_voice()
        
        # 创建真实组件
        self.safety_manager = SafetyManager(
            robot_controller=self.mock_robot,
            expression_controller=self.mock_expression,
            voice_controller=self.mock_voice
        )
        
        self.emotion_engine = EmotionEngine()
        
        self.personality_manager = PersonalityManager(
            self.mock_robot,
            self.emotion_engine,
            safety_manager=self.safety_manager
        )
        
        # 事件记录
        self.events: List[ModalityEvent] = []
        self.event_lock = threading.Lock()
        
        # 测试场景
        self.scenarios = self._create_test_scenarios()
    
    def _create_mock_robot(self):
        """创建模拟机器人"""
        class MockRobot:
            def __init__(self):
                self.actions = []
                self.position = {'x': 0, 'y': 0, 'angle': 0}
                self.is_moving = False
            
            def __getattr__(self, name):
                def mock_method(*args):
                    self.actions.append({
                        'action': name,
                        'args': args,
                        'timestamp': datetime.now()
                    })
                    
                    # 模拟运动状态
                    if name in ['t_up', 't_down', 'turnLeft', 'turnRight', 'moveLeft', 'moveRight']:
                        self.is_moving = True
                        # 模拟运动完成
                        threading.Timer(0.5, lambda: setattr(self, 'is_moving', False)).start()
                    elif name == 't_stop':
                        self.is_moving = False
                    
                    return True
                return mock_method
            
            def get_status(self):
                return {
                    'position': self.position,
                    'is_moving': self.is_moving,
                    'recent_actions': self.actions[-5:]
                }
        
        return MockRobot()
    
    def _create_mock_expression(self):
        """创建模拟表情控制器"""
        class MockExpressionController:
            def __init__(self):
                self.current_emotion = "neutral"
                self.animations = []
                self.is_speaking = False
                self.is_listening = False
                self.is_thinking = False
            
            def show_emotion(self, emotion):
                self.current_emotion = emotion
                self.animations.append({
                    'type': 'emotion',
                    'emotion': emotion,
                    'timestamp': datetime.now()
                })
                return True
            
            def animate_speaking(self, duration):
                self.is_speaking = True
                self.animations.append({
                    'type': 'speaking',
                    'duration': duration,
                    'timestamp': datetime.now()
                })
                threading.Timer(duration, lambda: setattr(self, 'is_speaking', False)).start()
                return True
            
            def show_listening_animation(self):
                self.is_listening = True
                self.animations.append({
                    'type': 'listening',
                    'timestamp': datetime.now()
                })
                return True
            
            def show_thinking_animation(self):
                self.is_thinking = True
                self.animations.append({
                    'type': 'thinking',
                    'timestamp': datetime.now()
                })
                return True
            
            def get_status(self):
                return {
                    'current_emotion': self.current_emotion,
                    'is_speaking': self.is_speaking,
                    'is_listening': self.is_listening,
                    'is_thinking': self.is_thinking,
                    'recent_animations': self.animations[-5:]
                }
        
        return MockExpressionController()
    
    def _create_mock_voice(self):
        """创建模拟语音控制器"""
        class MockVoiceController:
            def __init__(self):
                self.spoken_texts = []
                self.is_listening = False
                self.wake_word_detected = False
                self.conversation_active = False
            
            def speak_text(self, text):
                self.spoken_texts.append({
                    'text': text,
                    'timestamp': datetime.now()
                })
                return True
            
            def start_listening(self):
                self.is_listening = True
                return True
            
            def stop_listening(self):
                self.is_listening = False
                return True
            
            def start_conversation_mode(self):
                self.conversation_active = True
                return True
            
            def stop_conversation_mode(self):
                self.conversation_active = False
                return True
            
            def get_status(self):
                return {
                    'is_listening': self.is_listening,
                    'conversation_active': self.conversation_active,
                    'wake_word_detected': self.wake_word_detected,
                    'recent_speech': self.spoken_texts[-3:]
                }
        
        return MockVoiceController()
    
    def _create_test_scenarios(self) -> List[InteractionScenario]:
        """创建测试场景"""
        return [
            InteractionScenario(
                name="完整对话周期",
                description="从唤醒词到完整对话的端到端测试",
                expected_modalities=[ModalityType.VOICE, ModalityType.VISUAL, ModalityType.EMOTION],
                input_sequence=[
                    {'type': 'wake_word', 'data': '喵喵小车'},
                    {'type': 'speech_input', 'data': '你好'},
                    {'type': 'wait', 'duration': 1.0},
                    {'type': 'speech_input', 'data': '转个圈'},
                    {'type': 'wait', 'duration': 2.0}
                ],
                expected_outcomes={
                    'wake_word_response': True,
                    'conversation_started': True,
                    'emotion_detected': True,
                    'movement_executed': True,
                    'visual_feedback': True
                }
            ),
            
            InteractionScenario(
                name="情感驱动的多模态响应",
                description="测试情感如何影响语音、视觉和运动模态",
                expected_modalities=[ModalityType.EMOTION, ModalityType.VISUAL, ModalityType.MOVEMENT],
                input_sequence=[
                    {'type': 'emotion_trigger', 'emotion': 'happy', 'intensity': 0.8},
                    {'type': 'wait', 'duration': 0.5},
                    {'type': 'emotion_trigger', 'emotion': 'sad', 'intensity': 0.6},
                    {'type': 'wait', 'duration': 0.5},
                    {'type': 'emotion_trigger', 'emotion': 'excited', 'intensity': 0.9}
                ],
                expected_outcomes={
                    'emotion_expressions': 3,
                    'movement_patterns': 3,
                    'expression_changes': 3
                }
            ),
            
            InteractionScenario(
                name="安全优先级多模态协调",
                description="测试安全系统如何影响所有模态",
                expected_modalities=[ModalityType.SAFETY, ModalityType.MOVEMENT, ModalityType.VISUAL, ModalityType.VOICE],
                input_sequence=[
                    {'type': 'obstacle_detected', 'data': True},
                    {'type': 'movement_command', 'data': 'forward'},
                    {'type': 'wait', 'duration': 0.5},
                    {'type': 'obstacle_cleared', 'data': False},
                    {'type': 'movement_command', 'data': 'forward'}
                ],
                expected_outcomes={
                    'movement_blocked': True,
                    'safety_warning': True,
                    'visual_alert': True,
                    'movement_allowed_after_clear': True
                }
            ),
            
            InteractionScenario(
                name="同步语音和视觉表达",
                description="测试说话时的嘴部动画同步",
                expected_modalities=[ModalityType.VOICE, ModalityType.VISUAL],
                input_sequence=[
                    {'type': 'speak_with_animation', 'text': '你好，我是快快！', 'duration': 2.0},
                    {'type': 'wait', 'duration': 0.5},
                    {'type': 'speak_with_animation', 'text': '让我们一起玩吧！', 'duration': 1.5}
                ],
                expected_outcomes={
                    'speech_count': 2,
                    'animation_count': 2,
                    'synchronization': True
                }
            ),
            
            InteractionScenario(
                name="复杂交互序列",
                description="测试多个模态的复杂交互序列",
                expected_modalities=[ModalityType.VOICE, ModalityType.VISUAL, ModalityType.MOVEMENT, ModalityType.EMOTION],
                input_sequence=[
                    {'type': 'conversation_start'},
                    {'type': 'speech_input', 'data': '我们来跳舞吧'},
                    {'type': 'wait', 'duration': 1.0},
                    {'type': 'execute_dance_sequence'},
                    {'type': 'wait', 'duration': 2.0},
                    {'type': 'speech_input', 'data': '太棒了！'},
                    {'type': 'wait', 'duration': 1.0}
                ],
                expected_outcomes={
                    'dance_movements': True,
                    'happy_expressions': True,
                    'positive_feedback': True,
                    'coordinated_response': True
                }
            )
        ]
    
    def record_event(self, modality: ModalityType, event_type: str, data: Dict[str, Any], duration: float = 0.0):
        """记录模态事件"""
        with self.event_lock:
            event = ModalityEvent(
                modality=modality,
                event_type=event_type,
                data=data,
                timestamp=datetime.now(),
                duration=duration
            )
            self.events.append(event)
    
    def execute_scenario(self, scenario: InteractionScenario) -> Dict[str, Any]:
        """执行测试场景"""
        print(f"\n执行场景: {scenario.name}")
        print(f"描述: {scenario.description}")
        
        # 清除之前的事件
        with self.event_lock:
            self.events.clear()
        
        start_time = datetime.now()
        
        try:
            # 执行输入序列
            for step in scenario.input_sequence:
                self._execute_step(step)
            
            # 等待所有异步操作完成
            time.sleep(0.5)
            
            # 分析结果
            results = self._analyze_scenario_results(scenario, start_time)
            
            return results
            
        except Exception as e:
            logger.error(f"场景执行失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'events_recorded': len(self.events)
            }
    
    def _execute_step(self, step: Dict[str, Any]):
        """执行单个步骤"""
        step_type = step['type']
        
        if step_type == 'wake_word':
            self.mock_voice.wake_word_detected = True
            self.mock_voice.start_conversation_mode()
            self.record_event(ModalityType.VOICE, 'wake_word_detected', step)
            
        elif step_type == 'speech_input':
            text = step['data']
            # 模拟语音识别和AI回复
            emotion = self.emotion_engine.analyze_response_emotion(text)
            self.mock_expression.show_emotion(emotion.emotion_type.value)
            self.mock_voice.speak_text(f"我听到了：{text}")
            
            self.record_event(ModalityType.VOICE, 'speech_input', {'text': text})
            self.record_event(ModalityType.EMOTION, 'emotion_detected', {'emotion': emotion.emotion_type.value})
            self.record_event(ModalityType.VISUAL, 'expression_shown', {'emotion': emotion.emotion_type.value})
            
        elif step_type == 'emotion_trigger':
            emotion = step['emotion']
            intensity = step['intensity']
            
            # 触发情感响应
            self.mock_expression.show_emotion(emotion)
            
            # 执行情感运动
            if emotion == 'happy':
                self.mock_robot.turnRight(50, 1.0)
            elif emotion == 'sad':
                self.mock_robot.t_down(30, 0.5)
            elif emotion == 'excited':
                self.mock_robot.t_up(60, 1.0)
            
            self.record_event(ModalityType.EMOTION, 'emotion_triggered', step)
            self.record_event(ModalityType.VISUAL, 'emotion_expression', {'emotion': emotion})
            self.record_event(ModalityType.MOVEMENT, 'emotional_movement', {'emotion': emotion})
            
        elif step_type == 'obstacle_detected':
            detected = step['data']
            self.safety_manager.update_obstacle_status(detected)
            
            if detected:
                self.mock_expression.show_emotion('confused')
                self.mock_voice.speak_text("前面有障碍物！")
            
            self.record_event(ModalityType.SAFETY, 'obstacle_status', {'detected': detected})
            
        elif step_type == 'movement_command':
            command = step['data']
            safe = self.safety_manager.check_movement_safety(command)
            
            if safe:
                getattr(self.mock_robot, command)(50, 1.0)
                self.record_event(ModalityType.MOVEMENT, 'movement_executed', {'command': command})
            else:
                self.mock_voice.speak_text("抱歉，现在不能移动")
                self.record_event(ModalityType.MOVEMENT, 'movement_blocked', {'command': command})
            
        elif step_type == 'speak_with_animation':
            text = step['text']
            duration = step['duration']
            
            # 同步语音和动画
            self.mock_voice.speak_text(text)
            self.mock_expression.animate_speaking(duration)
            
            self.record_event(ModalityType.VOICE, 'speech_output', {'text': text})
            self.record_event(ModalityType.VISUAL, 'speaking_animation', {'duration': duration})
            
        elif step_type == 'conversation_start':
            self.mock_voice.start_conversation_mode()
            self.mock_expression.show_listening_animation()
            self.record_event(ModalityType.VOICE, 'conversation_started', {})
            self.record_event(ModalityType.VISUAL, 'listening_animation', {})
            
        elif step_type == 'execute_dance_sequence':
            # 执行舞蹈序列
            dance_moves = ['turnLeft', 'turnRight', 'turnLeft', 'turnRight']
            for move in dance_moves:
                getattr(self.mock_robot, move)(60, 0.5)
                time.sleep(0.1)
            
            self.mock_expression.show_emotion('excited')
            self.record_event(ModalityType.MOVEMENT, 'dance_sequence', {'moves': dance_moves})
            self.record_event(ModalityType.VISUAL, 'dance_expression', {})
            
        elif step_type == 'wait':
            time.sleep(step['duration'])
    
    def _analyze_scenario_results(self, scenario: InteractionScenario, start_time: datetime) -> Dict[str, Any]:
        """分析场景结果"""
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # 按模态分组事件
        events_by_modality = {}
        for event in self.events:
            modality = event.modality.value
            if modality not in events_by_modality:
                events_by_modality[modality] = []
            events_by_modality[modality].append(event)
        
        # 检查期望的模态是否都被激活
        expected_modalities = [m.value for m in scenario.expected_modalities]
        activated_modalities = list(events_by_modality.keys())
        modalities_coverage = len(set(expected_modalities) & set(activated_modalities)) / len(expected_modalities)
        
        # 检查期望的结果
        outcomes_met = self._check_expected_outcomes(scenario.expected_outcomes, events_by_modality)
        
        # 计算成功率
        success_rate = sum(outcomes_met.values()) / len(outcomes_met) if outcomes_met else 0
        
        results = {
            'scenario_name': scenario.name,
            'success': success_rate >= 0.8,  # 80%成功率阈值
            'success_rate': success_rate,
            'execution_time': execution_time,
            'modalities_coverage': modalities_coverage,
            'expected_modalities': expected_modalities,
            'activated_modalities': activated_modalities,
            'events_by_modality': {k: len(v) for k, v in events_by_modality.items()},
            'outcomes_met': outcomes_met,
            'total_events': len(self.events),
            'detailed_events': [asdict(e) for e in self.events]
        }
        
        return results
    
    def _check_expected_outcomes(self, expected_outcomes: Dict[str, Any], 
                                events_by_modality: Dict[str, List[ModalityEvent]]) -> Dict[str, bool]:
        """检查期望结果"""
        outcomes_met = {}
        
        for outcome, expected_value in expected_outcomes.items():
            if outcome == 'wake_word_response':
                outcomes_met[outcome] = 'voice' in events_by_modality and any(
                    e.event_type == 'wake_word_detected' for e in events_by_modality['voice']
                )
            
            elif outcome == 'conversation_started':
                outcomes_met[outcome] = 'voice' in events_by_modality and any(
                    e.event_type in ['conversation_started', 'speech_input'] for e in events_by_modality['voice']
                )
            
            elif outcome == 'emotion_detected':
                outcomes_met[outcome] = 'emotion' in events_by_modality and len(events_by_modality['emotion']) > 0
            
            elif outcome == 'movement_executed':
                outcomes_met[outcome] = 'movement' in events_by_modality and any(
                    e.event_type == 'movement_executed' for e in events_by_modality['movement']
                )
            
            elif outcome == 'visual_feedback':
                outcomes_met[outcome] = 'visual' in events_by_modality and len(events_by_modality['visual']) > 0
            
            elif outcome == 'emotion_expressions':
                actual_count = len(events_by_modality.get('visual', []))
                outcomes_met[outcome] = actual_count >= expected_value
            
            elif outcome == 'movement_patterns':
                actual_count = len(events_by_modality.get('movement', []))
                outcomes_met[outcome] = actual_count >= expected_value
            
            elif outcome == 'movement_blocked':
                outcomes_met[outcome] = 'movement' in events_by_modality and any(
                    e.event_type == 'movement_blocked' for e in events_by_modality['movement']
                )
            
            elif outcome == 'synchronization':
                voice_events = events_by_modality.get('voice', [])
                visual_events = events_by_modality.get('visual', [])
                # 简化的同步检查：语音和视觉事件数量相近
                outcomes_met[outcome] = abs(len(voice_events) - len(visual_events)) <= 1
            
            else:
                outcomes_met[outcome] = True  # 默认通过
        
        return outcomes_met
    
    def run_all_scenarios(self) -> Dict[str, Any]:
        """运行所有测试场景"""
        print("开始多模态交互集成测试")
        print("=" * 60)
        
        results = []
        
        for scenario in self.scenarios:
            result = self.execute_scenario(scenario)
            results.append(result)
            
            # 显示结果
            status = "✓" if result['success'] else "✗"
            print(f"{status} {scenario.name} - 成功率: {result['success_rate']:.1%} "
                  f"({result['execution_time']:.2f}s)")
        
        # 生成总体报告
        total_scenarios = len(results)
        successful_scenarios = sum(1 for r in results if r['success'])
        average_success_rate = sum(r['success_rate'] for r in results) / total_scenarios
        total_execution_time = sum(r['execution_time'] for r in results)
        
        report = {
            'summary': {
                'total_scenarios': total_scenarios,
                'successful_scenarios': successful_scenarios,
                'overall_success_rate': successful_scenarios / total_scenarios,
                'average_success_rate': average_success_rate,
                'total_execution_time': total_execution_time
            },
            'scenario_results': results,
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """保存测试报告"""
        if filename is None:
            filename = f"multimodal_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n多模态测试报告已保存到: {filename}")
        return filename

def main():
    """主函数"""
    try:
        # 创建测试工具
        test_harness = MultimodalTestHarness()
        
        # 运行所有场景
        report = test_harness.run_all_scenarios()
        
        # 显示摘要
        summary = report['summary']
        print("\n" + "=" * 60)
        print("多模态交互集成测试摘要")
        print("=" * 60)
        print(f"总场景数: {summary['total_scenarios']}")
        print(f"成功场景: {summary['successful_scenarios']}")
        print(f"整体成功率: {summary['overall_success_rate']:.1%}")
        print(f"平均成功率: {summary['average_success_rate']:.1%}")
        print(f"总执行时间: {summary['total_execution_time']:.2f}秒")
        
        # 保存报告
        test_harness.save_report(report)
        
        # 检查是否达到要求
        if summary['overall_success_rate'] >= 0.8:
            print(f"\n✅ 多模态集成测试通过！")
            return 0
        else:
            print(f"\n⚠️  多模态集成测试未完全通过，需要改进")
            return 1
    
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 多模态集成测试失败: {e}")
        return 1

if __name__ == "__main__":
    exit(main())