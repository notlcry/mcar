#!/usr/bin/python3
"""
个性管理器集成测试脚本
测试情感驱动的运动模式和个性化动作序列（无硬件依赖）
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Tuple
from enum import Enum

from emotion_engine import EmotionEngine, EmotionType, EmotionalState

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MovementIntensity(Enum):
    """运动强度枚举"""
    GENTLE = "gentle"
    MODERATE = "moderate" 
    INTENSE = "intense"
    DEFAULT = "default"

@dataclass
class MovementPattern:
    """运动模式数据模型"""
    name: str
    base_speed: int  # 基础速度 (0-100)
    duration_range: Tuple[float, float]  # 持续时间范围（秒）
    actions: List[Dict]  # 动作序列
    repetitions: int = 1  # 重复次数
    pause_between: float = 0.5  # 动作间暂停时间
    randomize: bool = False  # 是否随机化动作顺序
    
    def get_adjusted_speed(self, intensity: float) -> int:
        """根据情感强度调整速度"""
        speed_multiplier = 0.5 + intensity
        adjusted_speed = int(self.base_speed * speed_multiplier)
        return max(10, min(100, adjusted_speed))
    
    def get_adjusted_duration(self, intensity: float) -> float:
        """根据情感强度调整持续时间"""
        min_dur, max_dur = self.duration_range
        duration = min_dur + (max_dur - min_dur) * intensity
        return duration

@dataclass 
class PersonalityProfile:
    """个性档案数据模型"""
    name: str = "快快"
    traits: Dict[str, float] = field(default_factory=lambda: {
        "friendliness": 0.8,
        "energy_level": 0.7,
        "curiosity": 0.6,
        "playfulness": 0.9,
        "responsiveness": 0.8
    })
    emotional_sensitivity: Dict[EmotionType, float] = field(default_factory=lambda: {
        EmotionType.HAPPY: 1.2,
        EmotionType.EXCITED: 1.5,
        EmotionType.SAD: 0.8,
        EmotionType.CONFUSED: 0.9,
        EmotionType.THINKING: 0.6,
        EmotionType.NEUTRAL: 1.0,
        EmotionType.ANGRY: 1.1,
        EmotionType.SURPRISED: 1.3
    })

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
    
    def t_up(self, speed, t_time):
        self._log_action("t_up", speed=speed, t_time=t_time)
        time.sleep(min(t_time, 0.3))  # 限制测试时间
    
    def t_down(self, speed, t_time):
        self._log_action("t_down", speed=speed, t_time=t_time)
        time.sleep(min(t_time, 0.3))
    
    def moveLeft(self, speed, t_time):
        self._log_action("moveLeft", speed=speed, t_time=t_time)
        time.sleep(min(t_time, 0.3))
    
    def moveRight(self, speed, t_time):
        self._log_action("moveRight", speed=speed, t_time=t_time)
        time.sleep(min(t_time, 0.3))
    
    def turnLeft(self, speed, t_time):
        self._log_action("turnLeft", speed=speed, t_time=t_time)
        time.sleep(min(t_time, 0.3))
    
    def turnRight(self, speed, t_time):
        self._log_action("turnRight", speed=speed, t_time=t_time)
        time.sleep(min(t_time, 0.3))
    
    def t_stop(self, t_time):
        self._log_action("t_stop", t_time=t_time)
        time.sleep(min(t_time, 0.1))
    
    def set_servo_angle(self, channel, angle):
        self._log_action("set_servo_angle", channel=channel, angle=angle)
        time.sleep(0.05)
    
    def get_action_log(self) -> List[Dict]:
        return self.action_log.copy()
    
    def clear_action_log(self):
        self.action_log = []

class TestPersonalityManager:
    """测试版个性管理器"""
    
    def __init__(self, robot_controller: MockLOBOROBOT, emotion_engine: Optional[EmotionEngine] = None):
        self.robot = robot_controller
        self.emotion_engine = emotion_engine
        self.personality = PersonalityProfile()
        self.is_moving = False
        self.current_action = None
        self.action_lock = threading.Lock()
        self.safety_enabled = True
        self.max_continuous_movement_time = 5.0  # 测试用较短时间
        self.movement_start_time = None
        
        self._initialize_movement_patterns()
        logger.info("测试个性管理器初始化完成")
    
    def _initialize_movement_patterns(self):
        """初始化运动模式"""
        self.movement_patterns = {
            EmotionType.HAPPY: {
                MovementIntensity.GENTLE: MovementPattern(
                    name="happy_gentle",
                    base_speed=40,
                    duration_range=(0.5, 1.0),
                    actions=[
                        {"action": "turnRight", "params": {}},
                        {"action": "t_stop", "params": {"t_time": 0.2}},
                        {"action": "turnLeft", "params": {}},
                        {"action": "t_stop", "params": {"t_time": 0.2}}
                    ],
                    repetitions=1
                ),
                MovementIntensity.MODERATE: MovementPattern(
                    name="happy_moderate", 
                    base_speed=60,
                    duration_range=(0.8, 1.5),
                    actions=[
                        {"action": "turnRight", "params": {}},
                        {"action": "t_up", "params": {}},
                        {"action": "turnLeft", "params": {}},
                        {"action": "t_stop", "params": {"t_time": 0.2}}
                    ],
                    repetitions=2
                ),
                MovementIntensity.INTENSE: MovementPattern(
                    name="happy_intense",
                    base_speed=80,
                    duration_range=(1.0, 2.0),
                    actions=[
                        {"action": "turnRight", "params": {}},
                        {"action": "turnRight", "params": {}},
                        {"action": "t_up", "params": {}},
                        {"action": "turnLeft", "params": {}}
                    ],
                    repetitions=2,
                    randomize=True
                )
            },
            
            EmotionType.EXCITED: {
                MovementIntensity.MODERATE: MovementPattern(
                    name="excited_moderate",
                    base_speed=70,
                    duration_range=(1.0, 1.8),
                    actions=[
                        {"action": "t_up", "params": {}},
                        {"action": "turnRight", "params": {}},
                        {"action": "moveRight", "params": {}},
                        {"action": "turnLeft", "params": {}}
                    ],
                    repetitions=1,
                    randomize=True
                )
            },
            
            EmotionType.SAD: {
                MovementIntensity.GENTLE: MovementPattern(
                    name="sad_gentle",
                    base_speed=20,
                    duration_range=(1.0, 2.0),
                    actions=[
                        {"action": "t_down", "params": {}},
                        {"action": "t_stop", "params": {"t_time": 0.5}},
                        {"action": "set_servo_angle", "params": {"channel": 2, "angle": 45}}
                    ],
                    repetitions=1
                )
            },
            
            EmotionType.CONFUSED: {
                MovementIntensity.GENTLE: MovementPattern(
                    name="confused_gentle",
                    base_speed=30,
                    duration_range=(0.8, 1.5),
                    actions=[
                        {"action": "turnLeft", "params": {}},
                        {"action": "t_stop", "params": {"t_time": 0.3}},
                        {"action": "turnRight", "params": {}},
                        {"action": "t_stop", "params": {"t_time": 0.3}}
                    ],
                    repetitions=2
                )
            },
            
            EmotionType.THINKING: {
                MovementIntensity.GENTLE: MovementPattern(
                    name="thinking_gentle",
                    base_speed=25,
                    duration_range=(1.0, 2.0),
                    actions=[
                        {"action": "moveLeft", "params": {}},
                        {"action": "t_stop", "params": {"t_time": 0.5}},
                        {"action": "moveRight", "params": {}},
                        {"action": "t_stop", "params": {"t_time": 0.5}}
                    ],
                    repetitions=1
                )
            },
            
            EmotionType.NEUTRAL: {
                MovementIntensity.DEFAULT: MovementPattern(
                    name="neutral_default",
                    base_speed=30,
                    duration_range=(0.5, 1.0),
                    actions=[
                        {"action": "t_stop", "params": {"t_time": 0.5}},
                        {"action": "set_servo_angle", "params": {"channel": 2, "angle": 90}}
                    ],
                    repetitions=1
                )
            }
        }
    
    def execute_emotional_movement(self, emotion: EmotionType, intensity: float, 
                                 duration: Optional[float] = None) -> bool:
        """执行情感驱动的运动"""
        if not self.safety_enabled:
            logger.warning("安全模式禁用，跳过运动执行")
            return False
        
        with self.action_lock:
            if self.is_moving:
                logger.info("机器人正在运动中，跳过新的运动指令")
                return False
            
            movement_pattern = self._get_movement_pattern(emotion, intensity)
            if not movement_pattern:
                logger.warning(f"未找到情感 {emotion.value} 的运动模式")
                return False
            
            adjusted_pattern = self._apply_personality_adjustments(movement_pattern, emotion)
            return self._execute_movement_pattern(adjusted_pattern, intensity, duration)
    
    def _get_movement_pattern(self, emotion: EmotionType, intensity: float) -> Optional[MovementPattern]:
        """根据情感和强度获取运动模式"""
        if emotion not in self.movement_patterns:
            return None
        
        emotion_patterns = self.movement_patterns[emotion]
        
        if intensity >= 0.8:
            intensity_level = MovementIntensity.INTENSE
        elif intensity >= 0.5:
            intensity_level = MovementIntensity.MODERATE
        elif intensity >= 0.2:
            intensity_level = MovementIntensity.GENTLE
        else:
            intensity_level = MovementIntensity.DEFAULT
        
        if intensity_level in emotion_patterns:
            return emotion_patterns[intensity_level]
        elif MovementIntensity.DEFAULT in emotion_patterns:
            return emotion_patterns[MovementIntensity.DEFAULT]
        elif MovementIntensity.GENTLE in emotion_patterns:
            return emotion_patterns[MovementIntensity.GENTLE]
        
        return None
    
    def _apply_personality_adjustments(self, pattern: MovementPattern, emotion: EmotionType) -> MovementPattern:
        """根据个性特征调整运动模式"""
        adjusted_pattern = MovementPattern(
            name=f"{pattern.name}_personalized",
            base_speed=pattern.base_speed,
            duration_range=pattern.duration_range,
            actions=pattern.actions.copy(),
            repetitions=pattern.repetitions,
            pause_between=pattern.pause_between,
            randomize=pattern.randomize
        )
        
        # 根据活力水平调整速度
        energy_multiplier = 0.7 + (self.personality.traits["energy_level"] * 0.6)
        adjusted_pattern.base_speed = int(pattern.base_speed * energy_multiplier)
        
        # 根据顽皮程度调整重复次数
        if self.personality.traits["playfulness"] > 0.7:
            adjusted_pattern.repetitions = min(pattern.repetitions + 1, 3)  # 测试用限制
            adjusted_pattern.randomize = True
        
        # 根据情感敏感度调整
        if emotion in self.personality.emotional_sensitivity:
            sensitivity = self.personality.emotional_sensitivity[emotion]
            adjusted_pattern.base_speed = int(adjusted_pattern.base_speed * sensitivity)
        
        adjusted_pattern.base_speed = max(15, min(95, adjusted_pattern.base_speed))
        return adjusted_pattern
    
    def _execute_movement_pattern(self, pattern: MovementPattern, intensity: float, 
                                duration: Optional[float] = None) -> bool:
        """执行运动模式"""
        try:
            self.is_moving = True
            self.current_action = pattern.name
            self.movement_start_time = time.time()
            
            logger.info(f"开始执行运动模式: {pattern.name} (强度: {intensity:.2f})")
            
            actual_speed = pattern.get_adjusted_speed(intensity)
            actual_duration = duration or pattern.get_adjusted_duration(intensity)
            actual_duration = min(actual_duration, self.max_continuous_movement_time)
            
            actions = pattern.actions.copy()
            if pattern.randomize:
                import random
                random.shuffle(actions)
            
            for rep in range(pattern.repetitions):
                if not self.safety_enabled:
                    break
                
                if time.time() - self.movement_start_time > self.max_continuous_movement_time:
                    logger.warning("运动时间超限，强制停止")
                    break
                
                for action_data in actions:
                    if not self.safety_enabled:
                        break
                    
                    action_name = action_data["action"]
                    action_params = action_data["params"].copy()
                    
                    if action_name in ["t_up", "t_down", "moveLeft", "moveRight", 
                                     "turnLeft", "turnRight"]:
                        if "speed" not in action_params:
                            action_params["speed"] = actual_speed
                        if "t_time" not in action_params:
                            time_per_action = actual_duration / (len(actions) * pattern.repetitions)
                            action_params["t_time"] = min(time_per_action, 0.5)  # 测试用限制
                    
                    self._execute_single_action(action_name, action_params)
                    
                    if pattern.pause_between > 0:
                        time.sleep(min(pattern.pause_between, 0.2))  # 测试用限制
                
                if rep < pattern.repetitions - 1:
                    time.sleep(min(pattern.pause_between * 2, 0.3))
            
            self.robot.t_stop(0.1)
            logger.info(f"运动模式 {pattern.name} 执行完成")
            return True
            
        except Exception as e:
            logger.error(f"执行运动模式时出错: {e}")
            return False
        finally:
            self.is_moving = False
            self.current_action = None
            self.movement_start_time = None
    
    def _execute_single_action(self, action_name: str, params: Dict):
        """执行单个动作"""
        try:
            if hasattr(self.robot, action_name):
                action_method = getattr(self.robot, action_name)
                action_method(**params)
                logger.debug(f"执行动作: {action_name} {params}")
            else:
                logger.warning(f"未知动作: {action_name}")
        except Exception as e:
            logger.error(f"执行动作 {action_name} 时出错: {e}")
    
    def handle_conversation_command(self, command: str, emotion: EmotionType) -> bool:
        """处理对话中的运动指令"""
        command = command.lower().strip()
        
        command_mappings = {
            "前进": ("t_up", {"speed": 50, "t_time": 1.0}),
            "后退": ("t_down", {"speed": 50, "t_time": 1.0}),
            "左转": ("turnLeft", {"speed": 50, "t_time": 0.5}),
            "右转": ("turnRight", {"speed": 50, "t_time": 0.5}),
            "停止": ("t_stop", {"t_time": 0.1}),
            "转个圈": ("spin_happy", {}),
            "跳舞": ("dance", {}),
        }
        
        matched_action = None
        for cmd_key, action_data in command_mappings.items():
            if cmd_key in command:
                matched_action = action_data
                break
        
        if matched_action:
            action_name, base_params = matched_action
            adjusted_params = self._adjust_params_for_emotion(base_params, emotion)
            
            if action_name in ["spin_happy", "dance"]:
                return self._execute_special_action(action_name, emotion, adjusted_params)
            else:
                return self._execute_basic_command(action_name, adjusted_params)
        
        return False
    
    def _adjust_params_for_emotion(self, base_params: Dict, emotion: EmotionType) -> Dict:
        """根据情感调整动作参数"""
        adjusted_params = base_params.copy()
        
        emotion_speed_multipliers = {
            EmotionType.HAPPY: 1.2,
            EmotionType.EXCITED: 1.5,
            EmotionType.SAD: 0.6,
            EmotionType.CONFUSED: 0.8,
            EmotionType.THINKING: 0.7,
            EmotionType.NEUTRAL: 1.0
        }
        
        multiplier = emotion_speed_multipliers.get(emotion, 1.0)
        
        if "speed" in adjusted_params:
            adjusted_params["speed"] = int(adjusted_params["speed"] * multiplier)
            adjusted_params["speed"] = max(20, min(90, adjusted_params["speed"]))
        
        if "t_time" in adjusted_params:
            if emotion in [EmotionType.HAPPY, EmotionType.EXCITED]:
                adjusted_params["t_time"] *= 0.8
            elif emotion == EmotionType.SAD:
                adjusted_params["t_time"] *= 1.5
        
        return adjusted_params
    
    def _execute_special_action(self, action_name: str, emotion: EmotionType, params: Dict) -> bool:
        """执行特殊动作"""
        try:
            if action_name == "spin_happy":
                speed = 60 if emotion == EmotionType.HAPPY else 40
                self.robot.turnRight(speed, 0.3)
                self.robot.turnRight(speed, 0.3)
                self.robot.t_stop(0.1)
                
            elif action_name == "dance":
                speed = 50
                self.robot.turnLeft(speed, 0.2)
                self.robot.turnRight(speed, 0.2)
                self.robot.t_up(speed, 0.3)
                self.robot.t_stop(0.1)
            
            logger.info(f"特殊动作 {action_name} 执行完成")
            return True
            
        except Exception as e:
            logger.error(f"执行特殊动作 {action_name} 时出错: {e}")
            return False
    
    def _execute_basic_command(self, action_name: str, params: Dict) -> bool:
        """执行基础指令"""
        try:
            if hasattr(self.robot, action_name):
                action_method = getattr(self.robot, action_name)
                action_method(**params)
                logger.info(f"基础指令 {action_name} 执行完成")
                return True
            else:
                logger.warning(f"未知基础指令: {action_name}")
                return False
        except Exception as e:
            logger.error(f"执行基础指令 {action_name} 时出错: {e}")
            return False
    
    def update_personality(self, new_traits: Dict[str, float]):
        """更新个性特征"""
        for trait, value in new_traits.items():
            if trait in self.personality.traits:
                self.personality.traits[trait] = max(0.0, min(1.0, value))
        logger.info(f"个性特征已更新: {self.personality.traits}")
    
    def get_status(self) -> Dict:
        """获取状态"""
        current_emotion = EmotionType.NEUTRAL
        if self.emotion_engine:
            current_state = self.emotion_engine.get_current_emotional_state()
            current_emotion = current_state.primary_emotion
        
        return {
            "is_moving": self.is_moving,
            "current_action": self.current_action,
            "safety_enabled": self.safety_enabled,
            "personality_traits": self.personality.traits,
            "current_emotion": current_emotion.value,
            "movement_patterns_count": sum(len(patterns) for patterns in self.movement_patterns.values())
        }

def test_emotional_movements():
    """测试情感驱动的运动模式"""
    print("\n=== 测试情感驱动运动模式 ===")
    
    mock_robot = MockLOBOROBOT()
    emotion_engine = EmotionEngine()
    personality_manager = TestPersonalityManager(mock_robot, emotion_engine)
    
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
        
        mock_robot.clear_action_log()
        
        start_time = time.time()
        success = personality_manager.execute_emotional_movement(emotion, intensity)
        execution_time = time.time() - start_time
        
        print(f"执行结果: {'成功' if success else '失败'}")
        print(f"执行时间: {execution_time:.2f}秒")
        
        action_log = mock_robot.get_action_log()
        print(f"执行动作数量: {len(action_log)}")
        
        if action_log:
            print("动作序列:")
            for i, action in enumerate(action_log[:3], 1):
                print(f"  {i}. {action['action']} {action['params']}")
            if len(action_log) > 3:
                print(f"  ... 还有 {len(action_log) - 3} 个动作")
        
        time.sleep(0.2)

def test_conversation_commands():
    """测试对话指令处理"""
    print("\n=== 测试对话指令处理 ===")
    
    mock_robot = MockLOBOROBOT()
    personality_manager = TestPersonalityManager(mock_robot)
    
    test_commands = [
        ("前进", EmotionType.HAPPY, "开心状态下前进"),
        ("后退", EmotionType.SAD, "悲伤状态下后退"),
        ("左转", EmotionType.CONFUSED, "困惑状态下左转"),
        ("转个圈", EmotionType.HAPPY, "开心转圈"),
        ("跳舞", EmotionType.EXCITED, "兴奋跳舞"),
        ("停止", EmotionType.NEUTRAL, "停止动作")
    ]
    
    for command, emotion, description in test_commands:
        print(f"\n--- 测试 {description} ---")
        print(f"指令: '{command}', 情感: {emotion.value}")
        
        mock_robot.clear_action_log()
        
        start_time = time.time()
        success = personality_manager.handle_conversation_command(command, emotion)
        execution_time = time.time() - start_time
        
        print(f"处理结果: {'成功' if success else '失败'}")
        print(f"执行时间: {execution_time:.2f}秒")
        
        action_log = mock_robot.get_action_log()
        if action_log:
            print(f"执行动作: {len(action_log)}个")
            for action in action_log:
                print(f"  - {action['action']} {action['params']}")
        else:
            print("  无动作执行")
        
        time.sleep(0.2)

def test_emotion_integration():
    """测试与情感引擎的集成"""
    print("\n=== 测试情感引擎集成 ===")
    
    mock_robot = MockLOBOROBOT()
    emotion_engine = EmotionEngine()
    personality_manager = TestPersonalityManager(mock_robot, emotion_engine)
    
    test_texts = [
        "哈哈哈，太好了！我很开心！",
        "哇，这太厉害了！简直不可思议！",
        "我有点难过，今天不太顺利...",
        "嗯...让我想想这个问题",
        "什么？这是怎么回事？我不太懂"
    ]
    
    for text in test_texts:
        print(f"\n--- 分析文本: '{text}' ---")
        
        emotional_state = emotion_engine.analyze_response_emotion(text)
        emotion_engine.update_emotional_state(emotional_state)
        
        print(f"检测情感: {emotional_state.primary_emotion.value}")
        print(f"情感强度: {emotional_state.intensity:.2f}")
        print(f"运动模式: {emotional_state.movement_pattern}")
        
        mock_robot.clear_action_log()
        
        success = personality_manager.execute_emotional_movement(
            emotional_state.primary_emotion, 
            emotional_state.intensity
        )
        
        action_log = mock_robot.get_action_log()
        print(f"运动执行: {'成功' if success else '失败'}")
        print(f"动作数量: {len(action_log)}")
        
        time.sleep(0.3)

def test_personality_adjustments():
    """测试个性化调整"""
    print("\n=== 测试个性化调整 ===")
    
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
        }
    ]
    
    for personality_config in personalities:
        print(f"\n--- 测试 {personality_config['name']} 个性 ---")
        
        mock_robot = MockLOBOROBOT()
        personality_manager = TestPersonalityManager(mock_robot)
        personality_manager.update_personality(personality_config['traits'])
        
        emotion = EmotionType.HAPPY
        intensity = 0.7
        
        print(f"个性特征: {personality_config['traits']}")
        
        mock_robot.clear_action_log()
        success = personality_manager.execute_emotional_movement(emotion, intensity)
        
        action_log = mock_robot.get_action_log()
        if action_log:
            speeds = [action['params'].get('speed', 0) for action in action_log 
                     if 'speed' in action['params']]
            avg_speed = sum(speeds) / len(speeds) if speeds else 0
            
            print(f"动作数量: {len(action_log)}")
            print(f"平均速度: {avg_speed:.1f}")
        
        time.sleep(0.3)

def main():
    """主测试函数"""
    print("开始个性管理器集成测试")
    print("=" * 50)
    
    try:
        test_emotional_movements()
        test_conversation_commands()
        test_emotion_integration()
        test_personality_adjustments()
        
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