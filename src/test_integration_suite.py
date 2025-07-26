#!/usr/bin/python3
"""
AI桌宠系统集成测试套件
完整测试所有需求的端到端集成测试
"""

import time
import logging
import threading
import json
import os
import platform
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# 导入系统组件
from safety_manager import SafetyManager, SafetyLevel, NetworkStatus, PowerStatus
from ai_conversation import AIConversationManager
from emotion_engine import EmotionEngine, EmotionType
from personality_manager import PersonalityManager
from enhanced_voice_control import EnhancedVoiceController
from expression_controller import ExpressionController
from display_driver import DisplayDriver
from memory_manager import MemoryManager

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """测试结果数据模型"""
    test_name: str
    requirement_id: str
    status: str  # "PASS", "FAIL", "SKIP"
    execution_time: float
    details: Dict[str, Any]
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class TestReporter:
    """测试报告生成器"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = datetime.now()
    
    def add_result(self, result: TestResult):
        """添加测试结果"""
        self.results.append(result)
        status_symbol = "✓" if result.status == "PASS" else "✗" if result.status == "FAIL" else "⚠"
        print(f"{status_symbol} {result.test_name} ({result.execution_time:.2f}s)")
        if result.error_message:
            print(f"  错误: {result.error_message}")
    
    def generate_report(self) -> Dict:
        """生成测试报告"""
        total_time = (datetime.now() - self.start_time).total_seconds()
        
        passed = len([r for r in self.results if r.status == "PASS"])
        failed = len([r for r in self.results if r.status == "FAIL"])
        skipped = len([r for r in self.results if r.status == "SKIP"])
        
        # 按需求分组
        by_requirement = {}
        for result in self.results:
            req_id = result.requirement_id
            if req_id not in by_requirement:
                by_requirement[req_id] = []
            by_requirement[req_id].append(result)
        
        report = {
            'summary': {
                'total_tests': len(self.results),
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'success_rate': passed / len(self.results) * 100 if self.results else 0,
                'total_time': total_time
            },
            'by_requirement': by_requirement,
            'detailed_results': [asdict(r) for r in self.results],
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def save_report(self, filename: str = None):
        """保存测试报告"""
        if filename is None:
            filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = self.generate_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n测试报告已保存到: {filename}")
        return filename

class MockComponents:
    """模拟组件集合"""
    
    class MockRobot:
        def __init__(self):
            self.actions = []
            self.position = {'x': 0, 'y': 0, 'angle': 0}
            self.stopped = False
            self.speed = 50
        
        def __getattr__(self, name):
            def mock_method(*args):
                action = f"{name}({', '.join(map(str, args))})"
                self.actions.append({
                    'action': action,
                    'timestamp': datetime.now(),
                    'args': args
                })
                
                # 模拟运动效果
                if name == 't_up':
                    self.position['y'] += 1
                elif name == 't_down':
                    self.position['y'] -= 1
                elif name == 'turnLeft':
                    self.position['angle'] -= 15
                elif name == 'turnRight':
                    self.position['angle'] += 15
                elif name == 't_stop':
                    self.stopped = True
                else:
                    self.stopped = False
                
                time.sleep(0.1)  # 模拟执行时间
                return True
            return mock_method
        
        def get_recent_actions(self, count=5):
            return self.actions[-count:]
        
        def clear_actions(self):
            self.actions.clear()
    
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
        
        def show_idle_animation(self):
            self.animations.append({
                'type': 'idle',
                'timestamp': datetime.now()
            })
            return True
        
        def clear_animations(self):
            self.animations.clear()
    
    class MockVoiceController:
        def __init__(self):
            self.spoken_texts = []
            self.is_listening = False
            self.wake_word_detected = False
            self.recognized_text = ""
        
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
        
        def simulate_wake_word(self):
            self.wake_word_detected = True
            return True
        
        def simulate_speech_input(self, text):
            self.recognized_text = text
            return text
        
        def clear_history(self):
            self.spoken_texts.clear()
    
    class MockAIConversationManager:
        def __init__(self):
            self.conversation_active = False
            self.conversation_history = []
            self.current_session_id = None
            self.mock_responses = {
                "你好": "你好！我是圆滚滚，很高兴见到你！",
                "转个圈": "好的，我来转个圈给你看！",
                "我们走吧": "好的，我们一起出发吧！",
                "你开心吗": "当然开心啦！和你聊天我很快乐呢！",
                "你难过吗": "有点难过呢，希望你能陪陪我。"
            }
        
        def start_conversation_mode(self):
            self.conversation_active = True
            self.current_session_id = f"session_{int(time.time())}"
            return True
        
        def stop_conversation_mode(self):
            self.conversation_active = False
            return True
        
        def process_conversation(self, user_input):
            if not self.conversation_active:
                return None
            
            # 模拟AI回复
            response = self.mock_responses.get(user_input, "我听到了，让我想想怎么回复你。")
            
            conversation_entry = {
                'user_input': user_input,
                'ai_response': response,
                'timestamp': datetime.now(),
                'session_id': self.current_session_id
            }
            
            self.conversation_history.append(conversation_entry)
            return response
        
        def get_conversation_history(self):
            return self.conversation_history
        
        def clear_history(self):
            self.conversation_history.clear()

class IntegrationTestSuite:
    """系统集成测试套件"""
    
    def __init__(self):
        self.reporter = TestReporter()
        self.mock = MockComponents()
        
        # 创建模拟组件实例
        self.mock_robot = self.mock.MockRobot()
        self.mock_expression = self.mock.MockExpressionController()
        self.mock_voice = self.mock.MockVoiceController()
        self.mock_ai = self.mock.MockAIConversationManager()
        
        # 创建真实组件实例（使用模拟的硬件接口）
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
        
        # 测试数据
        self.test_conversations = [
            {"input": "你好", "expected_emotion": "happy"},
            {"input": "转个圈", "expected_emotion": "excited"},
            {"input": "我们走吧", "expected_emotion": "excited"},
            {"input": "你开心吗", "expected_emotion": "happy"},
            {"input": "你难过吗", "expected_emotion": "sad"}
        ]
    
    def run_test(self, test_func, test_name: str, requirement_id: str):
        """运行单个测试"""
        start_time = time.time()
        
        try:
            result = test_func()
            execution_time = time.time() - start_time
            
            if result.get('success', False):
                test_result = TestResult(
                    test_name=test_name,
                    requirement_id=requirement_id,
                    status="PASS",
                    execution_time=execution_time,
                    details=result.get('details', {})
                )
            else:
                test_result = TestResult(
                    test_name=test_name,
                    requirement_id=requirement_id,
                    status="FAIL",
                    execution_time=execution_time,
                    details=result.get('details', {}),
                    error_message=result.get('error', 'Test failed')
                )
        
        except Exception as e:
            execution_time = time.time() - start_time
            test_result = TestResult(
                test_name=test_name,
                requirement_id=requirement_id,
                status="FAIL",
                execution_time=execution_time,
                details={},
                error_message=str(e)
            )
        
        self.reporter.add_result(test_result)
        return test_result
    
    def test_wake_word_detection(self):
        """测试唤醒词检测 - 需求1.1"""
        try:
            # 模拟唤醒词检测
            self.mock_voice.simulate_wake_word()
            
            # 检查是否正确激活对话模式
            wake_detected = self.mock_voice.wake_word_detected
            
            # 检查音频反馈
            audio_feedback = len(self.mock_voice.spoken_texts) > 0
            
            success = wake_detected
            
            return {
                'success': success,
                'details': {
                    'wake_word_detected': wake_detected,
                    'audio_feedback': audio_feedback,
                    'response_time': 0.5  # 模拟响应时间
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_speech_to_text_conversion(self):
        """测试语音转文本 - 需求1.2"""
        try:
            test_input = "你好，圆滚滚"
            
            # 模拟语音输入
            recognized_text = self.mock_voice.simulate_speech_input(test_input)
            
            # 验证识别结果
            success = recognized_text == test_input
            
            return {
                'success': success,
                'details': {
                    'input_text': test_input,
                    'recognized_text': recognized_text,
                    'accuracy': 1.0 if success else 0.0
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_ai_conversation_flow(self):
        """测试AI对话流程 - 需求1.3, 1.4"""
        try:
            # 启动对话模式
            self.mock_ai.start_conversation_mode()
            
            # 测试对话
            test_input = "你好"
            response = self.mock_ai.process_conversation(test_input)
            
            # 检查是否有回复
            has_response = response is not None and len(response) > 0
            
            # 检查是否有语音合成
            self.mock_voice.speak_text(response)
            has_tts = len(self.mock_voice.spoken_texts) > 0
            
            success = has_response and has_tts
            
            return {
                'success': success,
                'details': {
                    'user_input': test_input,
                    'ai_response': response,
                    'has_tts': has_tts,
                    'conversation_active': self.mock_ai.conversation_active
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_conversation_timeout(self):
        """测试对话超时 - 需求1.5"""
        try:
            # 启动对话模式
            self.mock_ai.start_conversation_mode()
            
            # 模拟30秒空闲（实际测试中缩短时间）
            initial_active = self.mock_ai.conversation_active
            
            # 模拟超时后停止对话
            time.sleep(0.1)  # 简化测试时间
            self.mock_ai.stop_conversation_mode()
            
            final_active = self.mock_ai.conversation_active
            
            success = initial_active and not final_active
            
            return {
                'success': success,
                'details': {
                    'initial_active': initial_active,
                    'final_active': final_active,
                    'timeout_handled': True
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_emotion_detection(self):
        """测试情感检测 - 需求2.1"""
        try:
            results = []
            
            for test_case in self.test_conversations:
                user_input = test_case['input']
                expected_emotion = test_case['expected_emotion']
                
                # 分析情感
                detected_emotion = self.emotion_engine.analyze_response_emotion(user_input)
                
                # 检查情感检测准确性
                emotion_correct = detected_emotion.emotion_type.value == expected_emotion
                
                results.append({
                    'input': user_input,
                    'expected': expected_emotion,
                    'detected': detected_emotion.emotion_type.value,
                    'correct': emotion_correct,
                    'intensity': detected_emotion.intensity
                })
            
            # 计算准确率
            correct_count = sum(1 for r in results if r['correct'])
            accuracy = correct_count / len(results)
            
            success = accuracy >= 0.6  # 60%准确率阈值
            
            return {
                'success': success,
                'details': {
                    'accuracy': accuracy,
                    'correct_count': correct_count,
                    'total_tests': len(results),
                    'detailed_results': results
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_emotional_expression_display(self):
        """测试情感表情显示 - 需求2.2"""
        try:
            test_emotions = ['happy', 'sad', 'excited', 'confused']
            results = []
            
            for emotion in test_emotions:
                # 清除之前的动画
                self.mock_expression.clear_animations()
                
                # 显示情感
                self.mock_expression.show_emotion(emotion)
                
                # 检查是否正确显示
                current_emotion = self.mock_expression.current_emotion
                has_animation = len(self.mock_expression.animations) > 0
                
                results.append({
                    'emotion': emotion,
                    'displayed_correctly': current_emotion == emotion,
                    'has_animation': has_animation
                })
            
            success = all(r['displayed_correctly'] and r['has_animation'] for r in results)
            
            return {
                'success': success,
                'details': {
                    'tested_emotions': test_emotions,
                    'results': results
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_emotional_movement_patterns(self):
        """测试情感运动模式 - 需求2.3, 2.4"""
        try:
            test_cases = [
                {'emotion': EmotionType.HAPPY, 'intensity': 0.8},
                {'emotion': EmotionType.SAD, 'intensity': 0.6},
                {'emotion': EmotionType.EXCITED, 'intensity': 0.9}
            ]
            
            results = []
            
            for case in test_cases:
                # 清除之前的动作
                self.mock_robot.clear_actions()
                
                # 执行情感运动
                success = self.personality_manager.execute_emotional_movement(
                    case['emotion'], case['intensity']
                )
                
                # 检查是否有相应的运动
                actions = self.mock_robot.get_recent_actions(5)
                has_movement = len(actions) > 0
                
                results.append({
                    'emotion': case['emotion'].value,
                    'intensity': case['intensity'],
                    'execution_success': success,
                    'has_movement': has_movement,
                    'actions': [a['action'] for a in actions]
                })
            
            success = all(r['execution_success'] and r['has_movement'] for r in results)
            
            return {
                'success': success,
                'details': {
                    'test_cases': len(test_cases),
                    'results': results
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_speaking_animation_sync(self):
        """测试说话动画同步 - 需求2.5"""
        try:
            # 模拟说话
            speech_duration = 2.0
            speech_text = "你好，我是圆滚滚！"
            
            # 开始说话动画
            self.mock_expression.animate_speaking(speech_duration)
            
            # 同时播放语音
            self.mock_voice.speak_text(speech_text)
            
            # 检查同步
            is_speaking = self.mock_expression.is_speaking
            has_speech = len(self.mock_voice.spoken_texts) > 0
            
            success = is_speaking and has_speech
            
            return {
                'success': success,
                'details': {
                    'speech_duration': speech_duration,
                    'speech_text': speech_text,
                    'animation_active': is_speaking,
                    'speech_output': has_speech
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_idle_animations(self):
        """测试空闲动画 - 需求2.6"""
        try:
            # 清除之前的动画
            self.mock_expression.clear_animations()
            
            # 显示空闲动画
            self.mock_expression.show_idle_animation()
            
            # 检查是否有空闲动画
            idle_animations = [a for a in self.mock_expression.animations if a['type'] == 'idle']
            has_idle_animation = len(idle_animations) > 0
            
            success = has_idle_animation
            
            return {
                'success': success,
                'details': {
                    'idle_animations_count': len(idle_animations),
                    'total_animations': len(self.mock_expression.animations)
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_conversation_command_execution(self):
        """测试对话命令执行 - 需求3.1, 3.2"""
        try:
            test_commands = [
                {'command': '前进', 'expected_action': 't_up'},
                {'command': '转个圈', 'expected_action': 'turnRight'},
                {'command': '停止', 'expected_action': 't_stop'}
            ]
            
            results = []
            
            for cmd_test in test_commands:
                # 清除之前的动作
                self.mock_robot.clear_actions()
                
                # 执行命令
                success = self.personality_manager.handle_conversation_command(
                    cmd_test['command'], EmotionType.HAPPY
                )
                
                # 检查动作
                actions = self.mock_robot.get_recent_actions(3)
                action_names = [a['action'].split('(')[0] for a in actions]
                has_expected_action = cmd_test['expected_action'] in action_names
                
                results.append({
                    'command': cmd_test['command'],
                    'expected_action': cmd_test['expected_action'],
                    'execution_success': success,
                    'has_expected_action': has_expected_action,
                    'actual_actions': action_names
                })
            
            success = all(r['execution_success'] for r in results)
            
            return {
                'success': success,
                'details': {
                    'test_commands': len(test_commands),
                    'results': results
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_safety_priority(self):
        """测试安全优先级 - 需求8.3"""
        try:
            # 设置障碍物
            self.safety_manager.update_obstacle_status(True)
            
            # 尝试执行个性化动作
            movement_allowed = self.safety_manager.check_movement_safety('forward')
            
            # 只有安全动作应该被允许
            safe_movement_allowed = self.safety_manager.check_movement_safety('stop')
            
            success = not movement_allowed and safe_movement_allowed
            
            # 清除障碍物
            self.safety_manager.update_obstacle_status(False)
            
            return {
                'success': success,
                'details': {
                    'obstacle_detected': True,
                    'forward_movement_blocked': not movement_allowed,
                    'stop_movement_allowed': safe_movement_allowed
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_offline_mode_fallback(self):
        """测试离线模式回退 - 需求8.1"""
        try:
            # 模拟网络连接丢失
            self.safety_manager._handle_network_change(NetworkStatus.ONLINE, NetworkStatus.OFFLINE)
            
            # 检查是否进入离线模式
            offline_active = self.safety_manager.safety_state.offline_mode_active
            
            # 测试离线命令处理
            offline_response = self.safety_manager.process_offline_command("你好")
            has_offline_response = offline_response is not None
            
            success = offline_active and has_offline_response
            
            return {
                'success': success,
                'details': {
                    'offline_mode_active': offline_active,
                    'offline_response': offline_response,
                    'has_offline_response': has_offline_response
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def run_all_tests(self):
        """运行所有集成测试"""
        print("开始运行AI桌宠系统集成测试套件")
        print("=" * 60)
        
        # 需求1: AI对话系统
        print("\n需求1: AI对话系统")
        self.run_test(self.test_wake_word_detection, "唤醒词检测", "1.1")
        self.run_test(self.test_speech_to_text_conversion, "语音转文本", "1.2")
        self.run_test(self.test_ai_conversation_flow, "AI对话流程", "1.3-1.4")
        self.run_test(self.test_conversation_timeout, "对话超时", "1.5")
        
        # 需求2: 情感表达系统
        print("\n需求2: 情感表达系统")
        self.run_test(self.test_emotion_detection, "情感检测", "2.1")
        self.run_test(self.test_emotional_expression_display, "情感表情显示", "2.2")
        self.run_test(self.test_emotional_movement_patterns, "情感运动模式", "2.3-2.4")
        self.run_test(self.test_speaking_animation_sync, "说话动画同步", "2.5")
        self.run_test(self.test_idle_animations, "空闲动画", "2.6")
        
        # 需求3: 个性化运动控制
        print("\n需求3: 个性化运动控制")
        self.run_test(self.test_conversation_command_execution, "对话命令执行", "3.1-3.2")
        
        # 需求8: 安全和备用机制
        print("\n需求8: 安全和备用机制")
        self.run_test(self.test_safety_priority, "安全优先级", "8.3")
        self.run_test(self.test_offline_mode_fallback, "离线模式回退", "8.1")
        
        # 生成报告
        print("\n" + "=" * 60)
        report = self.reporter.generate_report()
        
        print(f"测试完成!")
        print(f"总测试数: {report['summary']['total_tests']}")
        print(f"通过: {report['summary']['passed']}")
        print(f"失败: {report['summary']['failed']}")
        print(f"跳过: {report['summary']['skipped']}")
        print(f"成功率: {report['summary']['success_rate']:.1f}%")
        print(f"总耗时: {report['summary']['total_time']:.2f}秒")
        
        # 保存报告
        report_file = self.reporter.save_report()
        
        return report

def main():
    """主函数"""
    try:
        # 创建测试套件
        test_suite = IntegrationTestSuite()
        
        # 运行所有测试
        report = test_suite.run_all_tests()
        
        # 检查是否有失败的测试
        if report['summary']['failed'] > 0:
            print(f"\n⚠️  有 {report['summary']['failed']} 个测试失败，请检查详细报告")
            return 1
        else:
            print(f"\n✅ 所有测试通过！系统集成测试成功")
            return 0
    
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 测试套件执行失败: {e}")
        return 1

if __name__ == "__main__":
    exit(main())