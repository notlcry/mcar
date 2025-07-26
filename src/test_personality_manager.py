#!/usr/bin/python3
"""
个性管理器测试脚本
测试情感驱动的运动模式和个性化动作序列
"""

import sys
import time
import logging
from typing import Dict, List

# 添加当前目录到Python路径
sys.path.append('.')

# 先导入情感引擎
from emotion_engine import EmotionEngine, EmotionType, EmotionalState

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockLOBOROBOT:
    """模拟LOBOROBOT控制器用于测试"""
    
    def __init__(self):
        self.action_log = []
        logger.info("模拟LOBOROBOT控制器初始化")
    
    def _log_action(self, action: str, **params):
        """记录动作日志"""
        log_entry = {"action": action, "params": params, "timestamp": time.time()}
        self.action_log.append(log_entry)
        logger.info(f"执行动作: {action} {params}")
    
    def MotorRun(self, motor, direction, speed):
        self._log_action("MotorRun", motor=motor, direction=direction, speed=speed)
    
    def MotorStop(self, motor):
        self._log_action("MotorStop", motor=motor)
    
    def t_up(self, speed, t_time):
        self._log_action("t_up", speed=speed, t_time=t_time)
        time.sleep(min(t_time, 0.5))  # 限制测试时间
    
    def t_down(self, speed, t_time):
        self._log_action("t_down", speed=speed, t_time=t_time)
        time.sleep(min(t_time, 0.5))
    
    def moveLeft(self, speed, t_time):
        self._log_action("moveLeft", speed=speed, t_time=t_time)
        time.sleep(min(t_time, 0.5))
    
    def moveRight(self, speed, t_time):
        self._log_action("moveRight", speed=speed, t_time=t_time)
        time.sleep(min(t_time, 0.5))
    
    def turnLeft(self, speed, t_time):
        self._log_action("turnLeft", speed=speed, t_time=t_time)
        time.sleep(min(t_time, 0.5))
    
    def turnRight(self, speed, t_time):
        self._log_action("turnRight", speed=speed, t_time=t_time)
        time.sleep(min(t_time, 0.5))
    
    def forward_Left(self, speed, t_time):
        self._log_action("forward_Left", speed=speed, t_time=t_time)
        time.sleep(min(t_time, 0.5))
    
    def forward_Right(self, speed, t_time):
        self._log_action("forward_Right", speed=speed, t_time=t_time)
        time.sleep(min(t_time, 0.5))
    
    def backward_Left(self, speed, t_time):
        self._log_action("backward_Left", speed=speed, t_time=t_time)
        time.sleep(min(t_time, 0.5))
    
    def backward_Right(self, speed, t_time):
        self._log_action("backward_Right", speed=speed, t_time=t_time)
        time.sleep(min(t_time, 0.5))
    
    def t_stop(self, t_time):
        self._log_action("t_stop", t_time=t_time)
        time.sleep(min(t_time, 0.2))
    
    def set_servo_angle(self, channel, angle):
        self._log_action("set_servo_angle", channel=channel, angle=angle)
        time.sleep(0.1)
    
    def get_action_log(self) -> List[Dict]:
        """获取动作日志"""
        return self.action_log.copy()
    
    def clear_action_log(self):
        """清空动作日志"""
        self.action_log = []

def test_emotional_movements():
    """测试情感驱动的运动模式"""
    print("\n=== 测试情感驱动运动模式 ===")
    
    # 创建模拟组件
    mock_robot = MockLOBOROBOT()
    emotion_engine = EmotionEngine()
    personality_manager = PersonalityManager(mock_robot, emotion_engine)
    
    # 测试不同情感和强度的组合
    test_cases = [
        (EmotionType.HAPPY, 0.3, "轻度开心"),
        (EmotionType.HAPPY, 0.6, "中度开心"),
        (EmotionType.HAPPY, 0.9, "极度开心"),
        (EmotionType.EXCITED, 0.8, "兴奋"),
        (EmotionType.SAD, 0.7, "悲伤"),
        (EmotionType.CONFUSED, 0.5, "困惑"),
        (EmotionType.THINKING, 0.4, "思考"),
        (EmotionType.NEUTRAL, 0.5, "中性")
    ]
    
    for emotion, intensity, description in test_cases:
        print(f"\n--- 测试 {description} ---")
        print(f"情感: {emotion.value}, 强度: {intensity}")
        
        # 清空日志
        mock_robot.clear_action_log()
        
        # 执行情感运动
        start_time = time.time()
        success = personality_manager.execute_emotional_movement(emotion, intensity)
        execution_time = time.time() - start_time
        
        print(f"执行结果: {'成功' if success else '失败'}")
        print(f"执行时间: {execution_time:.2f}秒")
        
        # 分析动作日志
        action_log = mock_robot.get_action_log()
        print(f"执行动作数量: {len(action_log)}")
        
        if action_log:
            print("动作序列:")
            for i, action in enumerate(action_log[:5], 1):  # 只显示前5个动作
                print(f"  {i}. {action['action']} {action['params']}")
            if len(action_log) > 5:
                print(f"  ... 还有 {len(action_log) - 5} 个动作")
        
        time.sleep(0.5)  # 测试间隔

def test_conversation_commands():
    """测试对话指令处理"""
    print("\n=== 测试对话指令处理 ===")
    
    # 创建模拟组件
    mock_robot = MockLOBOROBOT()
    emotion_engine = EmotionEngine()
    personality_manager = PersonalityManager(mock_robot, emotion_engine)
    
    # 测试指令
    test_commands = [
        ("前进", EmotionType.HAPPY, "开心状态下前进"),
        ("后退", EmotionType.SAD, "悲伤状态下后退"),
        ("左转", EmotionType.CONFUSED, "困惑状态下左转"),
        ("右转", EmotionType.EXCITED, "兴奋状态下右转"),
        ("转个圈", EmotionType.HAPPY, "开心转圈"),
        ("跳舞", EmotionType.EXCITED, "兴奋跳舞"),
        ("摇摆", EmotionType.THINKING, "思考摇摆"),
        ("我们走吧", EmotionType.NEUTRAL, "中性跟随"),
        ("停止", EmotionType.NEUTRAL, "停止动作"),
        ("点头", EmotionType.HAPPY, "开心点头"),
        ("摇头", EmotionType.CONFUSED, "困惑摇头"),
        ("转一圈", EmotionType.EXCITED, "完整转圈")
    ]
    
    for command, emotion, description in test_commands:
        print(f"\n--- 测试 {description} ---")
        print(f"指令: '{command}', 情感: {emotion.value}")
        
        # 清空日志
        mock_robot.clear_action_log()
        
        # 处理指令
        start_time = time.time()
        success = personality_manager.handle_conversation_command(command, emotion)
        execution_time = time.time() - start_time
        
        print(f"处理结果: {'成功' if success else '失败'}")
        print(f"执行时间: {execution_time:.2f}秒")
        
        # 分析动作日志
        action_log = mock_robot.get_action_log()
        if action_log:
            print(f"执行动作: {len(action_log)}个")
            for action in action_log:
                print(f"  - {action['action']} {action['params']}")
        else:
            print("  无动作执行")
        
        time.sleep(0.3)

def test_personality_adjustments():
    """测试个性化调整"""
    print("\n=== 测试个性化调整 ===")
    
    # 创建不同个性的机器人
    personalities = [
        {
            "name": "活泼型",
            "traits": {
                "friendliness": 0.9,
                "energy_level": 0.9,
                "curiosity": 0.8,
                "playfulness": 0.9,
                "responsiveness": 0.8
            }
        },
        {
            "name": "温和型", 
            "traits": {
                "friendliness": 0.8,
                "energy_level": 0.4,
                "curiosity": 0.6,
                "playfulness": 0.5,
                "responsiveness": 0.7
            }
        },
        {
            "name": "好奇型",
            "traits": {
                "friendliness": 0.7,
                "energy_level": 0.6,
                "curiosity": 0.9,
                "playfulness": 0.7,
                "responsiveness": 0.9
            }
        }
    ]
    
    for personality_config in personalities:
        print(f"\n--- 测试 {personality_config['name']} 个性 ---")
        
        # 创建个性管理器
        mock_robot = MockLOBOROBOT()
        personality_manager = PersonalityManager(mock_robot)
        
        # 更新个性特征
        personality_manager.update_personality(personality_config['traits'])
        
        # 测试相同情感下的不同表现
        emotion = EmotionType.HAPPY
        intensity = 0.7
        
        print(f"个性特征: {personality_config['traits']}")
        
        # 清空日志
        mock_robot.clear_action_log()
        
        # 执行运动
        success = personality_manager.execute_emotional_movement(emotion, intensity)
        
        # 分析结果
        action_log = mock_robot.get_action_log()
        if action_log:
            # 计算平均速度
            speeds = [action['params'].get('speed', 0) for action in action_log 
                     if 'speed' in action['params']]
            avg_speed = sum(speeds) / len(speeds) if speeds else 0
            
            print(f"动作数量: {len(action_log)}")
            print(f"平均速度: {avg_speed:.1f}")
            print(f"个性响应风格: {personality_manager.get_personality_response_style()}")
        
        time.sleep(0.5)

def test_emotion_integration():
    """测试与情感引擎的集成"""
    print("\n=== 测试情感引擎集成 ===")
    
    # 创建组件
    mock_robot = MockLOBOROBOT()
    emotion_engine = EmotionEngine()
    personality_manager = PersonalityManager(mock_robot, emotion_engine)
    
    # 测试文本情感分析和运动响应
    test_texts = [
        "哈哈哈，太好了！我很开心！",
        "哇，这太厉害了！简直不可思议！",
        "我有点难过，今天不太顺利...",
        "嗯...让我想想这个问题",
        "什么？这是怎么回事？我不太懂"
    ]
    
    for text in test_texts:
        print(f"\n--- 分析文本: '{text}' ---")
        
        # 情感分析
        emotional_state = emotion_engine.analyze_response_emotion(text)
        emotion_engine.update_emotional_state(emotional_state)
        
        print(f"检测情感: {emotional_state.primary_emotion.value}")
        print(f"情感强度: {emotional_state.intensity:.2f}")
        print(f"运动模式: {emotional_state.movement_pattern}")
        
        # 清空日志
        mock_robot.clear_action_log()
        
        # 执行对应运动
        success = personality_manager.execute_emotional_movement(
            emotional_state.primary_emotion, 
            emotional_state.intensity
        )
        
        # 分析结果
        action_log = mock_robot.get_action_log()
        print(f"运动执行: {'成功' if success else '失败'}")
        print(f"动作数量: {len(action_log)}")
        
        time.sleep(0.5)

def test_safety_features():
    """测试安全功能"""
    print("\n=== 测试安全功能 ===")
    
    mock_robot = MockLOBOROBOT()
    personality_manager = PersonalityManager(mock_robot)
    
    # 测试紧急停止
    print("\n--- 测试紧急停止 ---")
    
    # 开始一个长时间运动
    import threading
    
    def long_movement():
        personality_manager.execute_emotional_movement(EmotionType.EXCITED, 0.9, duration=5.0)
    
    movement_thread = threading.Thread(target=long_movement)
    movement_thread.start()
    
    # 等待一段时间后紧急停止
    time.sleep(1.0)
    print("执行紧急停止...")
    personality_manager.emergency_stop()
    
    movement_thread.join(timeout=2.0)
    
    action_log = mock_robot.get_action_log()
    print(f"紧急停止前执行动作: {len(action_log)}")
    
    # 测试安全时间限制
    print("\n--- 测试运动时间限制 ---")
    mock_robot.clear_action_log()
    
    # 尝试执行超长时间运动
    success = personality_manager.execute_emotional_movement(
        EmotionType.HAPPY, 0.8, duration=15.0  # 超过最大限制
    )
    
    action_log = mock_robot.get_action_log()
    print(f"长时间运动结果: {'成功' if success else '失败'}")
    print(f"实际执行动作: {len(action_log)}")

def test_status_reporting():
    """测试状态报告"""
    print("\n=== 测试状态报告 ===")
    
    mock_robot = MockLOBOROBOT()
    emotion_engine = EmotionEngine()
    personality_manager = PersonalityManager(mock_robot, emotion_engine)
    
    # 获取初始状态
    print("初始状态:")
    status = personality_manager.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # 执行一些动作后再检查状态
    print("\n执行动作后状态:")
    personality_manager.execute_emotional_movement(EmotionType.HAPPY, 0.7)
    
    status = personality_manager.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # 测试情感引擎状态
    print("\n情感引擎状态:")
    emotion_status = emotion_engine.get_status()
    for key, value in emotion_status.items():
        print(f"  {key}: {value}")

def main():
    """主测试函数"""
    print("开始个性管理器综合测试")
    print("=" * 50)
    
    try:
        # 运行所有测试
        test_emotional_movements()
        test_conversation_commands()
        test_personality_adjustments()
        test_emotion_integration()
        test_safety_features()
        test_status_reporting()
        
        print("\n" + "=" * 50)
        print("所有测试完成！")
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()