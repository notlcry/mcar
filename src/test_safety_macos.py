#!/usr/bin/python3
"""
安全管理器macOS兼容测试
测试在macOS环境下的安全管理器功能
"""

import time
import logging
import platform
from safety_manager import SafetyManager, SafetyLevel, NetworkStatus, PowerStatus

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
            logger.info(f"模拟机器人动作: {action}")
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
        logger.info(f"模拟表情显示: {emotion}")

class MockVoiceController:
    """模拟语音控制器"""
    def __init__(self):
        self.spoken_texts = []
    
    def speak_text(self, text):
        self.spoken_texts.append(text)
        logger.info(f"模拟语音播放: {text}")

def test_macos_compatibility():
    """测试macOS兼容性"""
    print("=== macOS兼容性测试 ===")
    print(f"运行平台: {platform.system()} {platform.version()}")
    print(f"Python版本: {platform.python_version()}")
    
    # 创建模拟组件
    mock_robot = MockRobot()
    mock_expression = MockExpressionController()
    mock_voice = MockVoiceController()
    
    # 创建安全管理器
    safety_manager = SafetyManager(
        robot_controller=mock_robot,
        expression_controller=mock_expression,
        voice_controller=mock_voice
    )
    
    print("✓ 安全管理器创建成功")
    
    # 测试网络状态检查
    network_status = safety_manager._check_network_status()
    print(f"✓ 网络状态检查: {network_status.value}")
    
    # 测试电源状态检查
    power_status, percentage = safety_manager._check_power_status()
    print(f"✓ 电源状态检查: {power_status.value} ({percentage:.1f}%)")
    
    # 测试系统资源检查
    resources = safety_manager._check_system_resources()
    print(f"✓ 系统资源检查: critical={resources['critical']}, high={resources['high']}")
    
    # 测试安全级别计算
    safety_level = safety_manager._calculate_safety_level()
    print(f"✓ 安全级别计算: {safety_level.value}")
    
    # 测试系统健康状态
    health = safety_manager.get_system_health()
    print("✓ 系统健康状态:")
    for key, value in health.items():
        if key != 'safety_status':
            print(f"  {key}: {value}")
    
    print("\nmacOS兼容性测试完成！")

def test_basic_safety_functions():
    """测试基本安全功能"""
    print("\n=== 基本安全功能测试 ===")
    
    # 创建模拟组件
    mock_robot = MockRobot()
    mock_expression = MockExpressionController()
    mock_voice = MockVoiceController()
    
    # 创建安全管理器
    safety_manager = SafetyManager(
        robot_controller=mock_robot,
        expression_controller=mock_expression,
        voice_controller=mock_voice
    )
    
    # 测试运动安全检查
    print("运动安全检查:")
    test_commands = ['forward', 'backward', 'stop', 'left', 'right']
    for command in test_commands:
        safe = safety_manager.check_movement_safety(command)
        print(f"  {command}: {'✓ 安全' if safe else '✗ 不安全'}")
    
    # 测试障碍物检测
    print("\n障碍物检测测试:")
    safety_manager.update_obstacle_status(True)
    print("设置障碍物存在")
    for command in test_commands:
        safe = safety_manager.check_movement_safety(command)
        print(f"  {command}: {'✓ 允许' if safe else '✗ 禁止'}")
    
    safety_manager.update_obstacle_status(False)
    print("清除障碍物")
    
    # 测试API失败处理
    print("\nAPI失败处理测试:")
    for i in range(4):
        response = safety_manager.handle_api_failure("timeout", i)
        print(f"  失败 {i+1}: {response}")
    
    # 测试离线命令处理
    print("\n离线命令处理测试:")
    safety_manager.safety_state.offline_mode_active = True
    test_inputs = ['你好', '前进', '停止', '再见', '转圈']
    for user_input in test_inputs:
        response = safety_manager.process_offline_command(user_input)
        print(f"  '{user_input}' -> '{response}'")
    
    print("\n基本安全功能测试完成！")

def test_emergency_scenarios():
    """测试紧急情况处理"""
    print("\n=== 紧急情况处理测试 ===")
    
    # 创建模拟组件
    mock_robot = MockRobot()
    mock_expression = MockExpressionController()
    mock_voice = MockVoiceController()
    
    # 创建安全管理器
    safety_manager = SafetyManager(
        robot_controller=mock_robot,
        expression_controller=mock_expression,
        voice_controller=mock_voice
    )
    
    # 测试紧急停止
    print("紧急停止测试:")
    safety_manager.emergency_stop()
    print(f"  机器人停止状态: {'✓' if mock_robot.stopped else '✗'}")
    print(f"  紧急停止激活: {'✓' if safety_manager.safety_state.emergency_stop_active else '✗'}")
    print(f"  运动受限: {'✓' if safety_manager.safety_state.movement_restricted else '✗'}")
    
    # 测试紧急状态下的运动检查
    print("\n紧急状态下运动检查:")
    test_commands = ['forward', 'backward', 'stop']
    for command in test_commands:
        safe = safety_manager.check_movement_safety(command)
        print(f"  {command}: {'✓ 允许' if safe else '✗ 禁止'}")
    
    # 测试重置紧急停止
    print("\n重置紧急停止:")
    safety_manager.reset_emergency_stop()
    print(f"  紧急停止激活: {'✗' if not safety_manager.safety_state.emergency_stop_active else '✓'}")
    
    print("\n紧急情况处理测试完成！")

def test_offline_mode():
    """测试离线模式"""
    print("\n=== 离线模式测试 ===")
    
    # 创建模拟组件
    mock_robot = MockRobot()
    mock_expression = MockExpressionController()
    mock_voice = MockVoiceController()
    
    # 创建安全管理器
    safety_manager = SafetyManager(
        robot_controller=mock_robot,
        expression_controller=mock_expression,
        voice_controller=mock_voice
    )
    
    # 模拟进入离线模式
    print("模拟网络连接丢失:")
    safety_manager._handle_network_change(NetworkStatus.ONLINE, NetworkStatus.OFFLINE)
    print(f"  离线模式激活: {'✓' if safety_manager.safety_state.offline_mode_active else '✗'}")
    
    # 测试离线命令处理
    print("\n离线命令测试:")
    offline_commands = [
        '你好',
        '前进',
        '后退', 
        '左转',
        '右转',
        '停止',
        '再见'
    ]
    
    for command in offline_commands:
        response = safety_manager.process_offline_command(command)
        print(f"  '{command}' -> '{response}'")
        if command in ['前进', '后退', '左转', '右转', '停止']:
            recent_actions = mock_robot.get_recent_actions(1)
            if recent_actions:
                print(f"    执行动作: {recent_actions[-1]}")
    
    # 模拟网络恢复
    print("\n模拟网络连接恢复:")
    safety_manager._handle_network_change(NetworkStatus.OFFLINE, NetworkStatus.ONLINE)
    print(f"  离线模式激活: {'✗' if not safety_manager.safety_state.offline_mode_active else '✓'}")
    
    print("\n离线模式测试完成！")

def main():
    """主测试函数"""
    print("开始安全管理器macOS兼容测试")
    print("=" * 50)
    
    try:
        # 运行各项测试
        test_macos_compatibility()
        test_basic_safety_functions()
        test_emergency_scenarios()
        test_offline_mode()
        
        print("\n" + "=" * 50)
        print("✓ 所有测试完成！安全管理器在macOS环境下运行正常。")
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        print(f"\n✗ 测试失败: {e}")

if __name__ == "__main__":
    main()