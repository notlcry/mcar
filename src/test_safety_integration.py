#!/usr/bin/python3
"""
安全管理器集成测试
测试安全管理器与AI系统各组件的集成
"""

import time
import logging
import threading
from LOBOROBOT import LOBOROBOT
from safety_manager import SafetyManager, SafetyLevel, NetworkStatus, PowerStatus
from ai_conversation import AIConversationManager
from emotion_engine import EmotionEngine, EmotionType
from personality_manager import PersonalityManager
from enhanced_voice_control import EnhancedVoiceController

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockRobot:
    """模拟机器人控制器"""
    def __init__(self):
        self.actions = []
        self.stopped = False
    
    def __getattr__(self, name):
        def mock_method(*args):
            action = f"{name}({', '.join(map(str, args))})"
            self.actions.append(action)
            if name == 't_stop':
                self.stopped = True
            else:
                self.stopped = False
            logger.info(f"机器人动作: {action}")
            time.sleep(0.1)
        return mock_method
    
    def get_recent_actions(self, count=5):
        return self.actions[-count:]

class MockExpressionController:
    """模拟表情控制器"""
    def __init__(self):
        self.current_emotion = "neutral"
        self.animations = []
    
    def show_emotion(self, emotion):
        self.current_emotion = emotion
        self.animations.append(f"show_emotion({emotion})")
        logger.info(f"表情显示: {emotion}")
    
    def show_listening_animation(self):
        self.animations.append("listening")
        logger.info("表情显示: 聆听动画")
    
    def show_thinking_animation(self):
        self.animations.append("thinking")
        logger.info("表情显示: 思考动画")
    
    def show_idle_animation(self):
        self.animations.append("idle")
        logger.info("表情显示: 空闲动画")
    
    def animate_speaking(self, duration):
        self.animations.append(f"speaking({duration})")
        logger.info(f"表情显示: 说话动画 ({duration}s)")

def test_safety_manager_basic():
    """测试安全管理器基本功能"""
    print("=== 测试安全管理器基本功能 ===")
    
    # 创建模拟组件
    mock_robot = MockRobot()
    mock_expression = MockExpressionController()
    
    # 创建安全管理器
    safety_manager = SafetyManager(
        robot_controller=mock_robot,
        expression_controller=mock_expression
    )
    
    # 启动监控
    safety_manager.start_monitoring()
    
    # 测试网络状态检查
    print(f"网络状态: {safety_manager._check_network_status().value}")
    
    # 测试电源状态检查
    power_status, percentage = safety_manager._check_power_status()
    print(f"电源状态: {power_status.value} ({percentage:.1f}%)")
    
    # 测试安全级别计算
    safety_level = safety_manager._calculate_safety_level()
    print(f"安全级别: {safety_level.value}")
    
    # 测试运动安全检查
    test_commands = ['forward', 'backward', 'stop', 'left', 'right']
    print("\n运动安全检查:")
    for command in test_commands:
        safe = safety_manager.check_movement_safety(command)
        print(f"  {command}: {'✓' if safe else '✗'}")
    
    # 测试障碍物检测
    print("\n测试障碍物检测:")
    safety_manager.update_obstacle_status(True)
    print("障碍物检测: 有障碍物")
    for command in test_commands:
        safe = safety_manager.check_movement_safety(command)
        print(f"  {command}: {'✓' if safe else '✗'}")
    
    safety_manager.update_obstacle_status(False)
    print("障碍物检测: 无障碍物")
    
    # 测试API失败处理
    print("\n测试API失败处理:")
    for i in range(4):
        response = safety_manager.handle_api_failure("timeout", i)
        print(f"  失败 {i+1}: {response}")
    
    # 测试离线命令处理
    print("\n测试离线命令处理:")
    safety_manager.safety_state.offline_mode_active = True
    test_inputs = ['你好', '前进', '停止', '再见']
    for user_input in test_inputs:
        response = safety_manager.process_offline_command(user_input)
        print(f"  '{user_input}' -> '{response}'")
    
    # 停止监控
    safety_manager.stop_monitoring()
    print("\n基本功能测试完成")

def test_ai_integration():
    """测试AI系统集成"""
    print("\n=== 测试AI系统集成 ===")
    
    # 创建模拟组件
    mock_robot = MockRobot()
    mock_expression = MockExpressionController()
    
    # 创建安全管理器
    safety_manager = SafetyManager(
        robot_controller=mock_robot,
        expression_controller=mock_expression
    )
    safety_manager.start_monitoring()
    
    # 创建AI系统组件
    emotion_engine = EmotionEngine()
    personality_manager = PersonalityManager(
        mock_robot, 
        emotion_engine, 
        safety_manager=safety_manager
    )
    ai_conversation_manager = AIConversationManager(
        robot_controller=mock_robot,
        expression_controller=mock_expression,
        safety_manager=safety_manager
    )
    
    # 测试情感驱动运动的安全检查
    print("测试情感驱动运动:")
    test_emotions = [
        (EmotionType.HAPPY, 0.8),
        (EmotionType.EXCITED, 0.9),
        (EmotionType.SAD, 0.6)
    ]
    
    for emotion, intensity in test_emotions:
        print(f"\n测试情感: {emotion.value} (强度: {intensity})")
        success = personality_manager.execute_emotional_movement(emotion, intensity)
        print(f"  执行结果: {'成功' if success else '失败'}")
        print(f"  最近动作: {mock_robot.get_recent_actions(3)}")
    
    # 测试障碍物优先级
    print("\n测试障碍物优先级:")
    safety_manager.update_obstacle_status(True)
    print("设置障碍物存在")
    
    for emotion, intensity in test_emotions:
        print(f"  情感运动 {emotion.value}: ", end="")
        success = personality_manager.execute_emotional_movement(emotion, intensity)
        print('被阻止' if not success else '执行')
    
    # 测试对话命令的安全检查
    print("\n测试对话命令安全检查:")
    safety_manager.update_obstacle_status(False)
    test_commands = ['前进', '转圈', '跳舞', '停止']
    
    for command in test_commands:
        print(f"  命令 '{command}': ", end="")
        success = personality_manager.handle_conversation_command(command, EmotionType.HAPPY)
        print('成功' if success else '失败')
    
    # 测试低电量限制
    print("\n测试低电量限制:")
    # 模拟低电量状态
    safety_manager.safety_state.power_status = PowerStatus.LOW
    safety_manager._apply_power_restrictions(PowerStatus.LOW)
    
    for command in test_commands:
        print(f"  低电量下命令 '{command}': ", end="")
        success = personality_manager.handle_conversation_command(command, EmotionType.HAPPY)
        print('成功' if success else '失败')
    
    # 停止监控
    safety_manager.stop_monitoring()
    print("\nAI系统集成测试完成")

def test_emergency_scenarios():
    """测试紧急情况处理"""
    print("\n=== 测试紧急情况处理 ===")
    
    # 创建模拟组件
    mock_robot = MockRobot()
    mock_expression = MockExpressionController()
    
    # 创建安全管理器
    safety_manager = SafetyManager(
        robot_controller=mock_robot,
        expression_controller=mock_expression
    )
    
    # 测试紧急停止
    print("测试紧急停止:")
    safety_manager.emergency_stop()
    print(f"  机器人停止状态: {mock_robot.stopped}")
    print(f"  紧急停止激活: {safety_manager.safety_state.emergency_stop_active}")
    print(f"  运动受限: {safety_manager.safety_state.movement_restricted}")
    
    # 测试紧急状态下的运动检查
    print("\n紧急状态下运动检查:")
    test_commands = ['forward', 'backward', 'stop']
    for command in test_commands:
        safe = safety_manager.check_movement_safety(command)
        print(f"  {command}: {'允许' if safe else '禁止'}")
    
    # 测试重置紧急停止
    print("\n测试重置紧急停止:")
    safety_manager.reset_emergency_stop()
    print(f"  紧急停止激活: {safety_manager.safety_state.emergency_stop_active}")
    print(f"  运动受限: {safety_manager.safety_state.movement_restricted}")
    
    # 测试危险电量情况
    print("\n测试危险电量情况:")
    safety_manager.safety_state.power_status = PowerStatus.CRITICAL
    safety_manager.safety_state.battery_percentage = 5.0
    safety_manager._apply_power_restrictions(PowerStatus.CRITICAL)
    
    print(f"  运动受限: {safety_manager.safety_state.movement_restricted}")
    for command in test_commands:
        safe = safety_manager.check_movement_safety(command)
        print(f"  {command}: {'允许' if safe else '禁止'}")
    
    print("\n紧急情况处理测试完成")

def test_offline_mode():
    """测试离线模式"""
    print("\n=== 测试离线模式 ===")
    
    # 创建模拟组件
    mock_robot = MockRobot()
    mock_expression = MockExpressionController()
    
    # 创建安全管理器
    safety_manager = SafetyManager(
        robot_controller=mock_robot,
        expression_controller=mock_expression
    )
    
    # 模拟进入离线模式
    print("模拟网络连接丢失:")
    safety_manager._handle_network_change(NetworkStatus.ONLINE, NetworkStatus.OFFLINE)
    print(f"  离线模式激活: {safety_manager.safety_state.offline_mode_active}")
    
    # 测试离线命令处理
    print("\n测试离线命令:")
    offline_commands = [
        '你好',
        '前进',
        '后退', 
        '左转',
        '右转',
        '停止',
        '再见',
        '转个圈'  # 不支持的命令
    ]
    
    for command in offline_commands:
        response = safety_manager.process_offline_command(command)
        print(f"  '{command}' -> '{response}'")
        if command in ['前进', '后退', '左转', '右转', '停止']:
            print(f"    最近动作: {mock_robot.get_recent_actions(1)}")
    
    # 模拟网络恢复
    print("\n模拟网络连接恢复:")
    safety_manager._handle_network_change(NetworkStatus.OFFLINE, NetworkStatus.ONLINE)
    print(f"  离线模式激活: {safety_manager.safety_state.offline_mode_active}")
    
    print("\n离线模式测试完成")

def test_system_health():
    """测试系统健康监控"""
    print("\n=== 测试系统健康监控 ===")
    
    # 创建安全管理器
    safety_manager = SafetyManager()
    
    # 获取系统健康状态
    health = safety_manager.get_system_health()
    
    print("系统健康状态:")
    for key, value in health.items():
        if key != 'safety_status':
            print(f"  {key}: {value}")
    
    # 获取安全状态
    safety_status = safety_manager.get_safety_status()
    print("\n安全状态:")
    for key, value in safety_status.items():
        print(f"  {key}: {value}")
    
    print("\n系统健康监控测试完成")

def main():
    """主测试函数"""
    print("开始安全管理器集成测试")
    print("=" * 50)
    
    try:
        # 运行各项测试
        test_safety_manager_basic()
        test_ai_integration()
        test_emergency_scenarios()
        test_offline_mode()
        test_system_health()
        
        print("\n" + "=" * 50)
        print("所有测试完成！")
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        print(f"\n测试失败: {e}")

if __name__ == "__main__":
    main()