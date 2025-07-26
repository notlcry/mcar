#!/usr/bin/python3
"""
个性管理器 - 将情感状态映射到机器人动作
实现情感驱动的运动模式和个性化行为控制
"""

import time
import random
import logging
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Tuple
from enum import Enum

from LOBOROBOT import LOBOROBOT
from emotion_engine import EmotionEngine, EmotionType, EmotionalState
from memory_manager import MemoryManager

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MovementStyle(Enum):
    """运动风格枚举"""
    BOUNCY = "bouncy"           # 弹跳式 - 开心时
    ENERGETIC = "energetic"     # 充满活力 - 兴奋时
    SLOW = "slow"              # 缓慢 - 悲伤时
    HESITANT = "hesitant"      # 犹豫 - 困惑时
    GENTLE_SWAY = "gentle_sway" # 轻柔摆动 - 思考时
    DEFAULT = "default"        # 默认 - 中性时
    SHARP = "sharp"            # 急促 - 生气时
    SUDDEN = "sudden"          # 突然 - 惊讶时

@dataclass
class PersonalityProfile:
    """个性档案数据模型"""
    name: str = "圆滚滚"
    traits: Dict[str, float] = field(default_factory=lambda: {
        "friendliness": 0.8,    # 友好度
        "energy_level": 0.7,    # 活力水平
        "curiosity": 0.6,       # 好奇心
        "playfulness": 0.9,     # 顽皮程度
        "responsiveness": 0.8   # 反应敏感度
    })
    preferred_responses: List[str] = field(default_factory=list)
    movement_style: str = "bouncy"
    voice_characteristics: Dict[str, str] = field(default_factory=dict)
    
    def adjust_trait(self, trait_name: str, value: float):
        """调整个性特征"""
        if trait_name in self.traits:
            self.traits[trait_name] = max(0.0, min(1.0, value))

@dataclass
class MovementSequence:
    """运动序列数据模型"""
    name: str
    actions: List[Dict]  # 动作列表，每个动作包含方法名、参数等
    emotion_type: EmotionType
    intensity_range: Tuple[float, float] = (0.0, 1.0)
    cooldown: float = 2.0  # 冷却时间
    priority: int = 1  # 优先级，数字越大优先级越高

class PersonalityManager:
    """个性管理器 - 将情感状态转换为个性化机器人动作"""
    
    def __init__(self, robot_controller: LOBOROBOT, emotion_engine: EmotionEngine = None, 
                 memory_manager: MemoryManager = None, safety_manager=None):
        """
        初始化个性管理器
        Args:
            robot_controller: LOBOROBOT控制器实例
            emotion_engine: 情感引擎实例（可选）
            memory_manager: 记忆管理器实例（可选）
            safety_manager: 安全管理器实例（可选）
        """
        self.robot = robot_controller
        self.emotion_engine = emotion_engine or EmotionEngine()
        self.memory_manager = memory_manager
        self.safety_manager = safety_manager
        
        # 个性档案
        self.personality = PersonalityProfile()
        
        # 从记忆管理器加载个性设置
        if self.memory_manager:
            self._load_personality_from_memory()
        
        # 运动序列缓存
        self.movement_sequences: Dict[str, MovementSequence] = {}
        self.last_movement_time = {}  # 记录上次执行时间，用于冷却
        
        # 当前执行状态
        self.is_executing = False
        self.current_sequence = None
        self.execution_lock = threading.Lock()
        
        # 安全参数
        self.safety_enabled = True
        self.max_continuous_time = 10.0  # 最大连续运动时间
        self.default_speed = 50  # 默认速度
        self.obstacle_override = True  # 障碍物检测优先级
        
        # 初始化运动序列
        self._initialize_movement_sequences()
        
        logger.info("个性管理器初始化完成")
    
    def _initialize_movement_sequences(self):
        """初始化预定义的运动序列"""
        
        # 开心情感 - 庆祝动作
        self.movement_sequences["happy_celebration"] = MovementSequence(
            name="happy_celebration",
            emotion_type=EmotionType.HAPPY,
            intensity_range=(0.6, 1.0),
            actions=[
                {"method": "turnRight", "speed": 60, "duration": 0.5},
                {"method": "t_stop", "duration": 0.2},
                {"method": "turnLeft", "speed": 60, "duration": 0.5},
                {"method": "t_stop", "duration": 0.2},
                {"method": "turnRight", "speed": 60, "duration": 0.5},
                {"method": "t_stop", "duration": 0.3}
            ],
            cooldown=3.0,
            priority=2
        )
        
        # 开心情感 - 轻快移动
        self.movement_sequences["happy_bounce"] = MovementSequence(
            name="happy_bounce",
            emotion_type=EmotionType.HAPPY,
            intensity_range=(0.3, 0.7),
            actions=[
                {"method": "t_up", "speed": 45, "duration": 0.3},
                {"method": "t_stop", "duration": 0.1},
                {"method": "t_down", "speed": 45, "duration": 0.2},
                {"method": "t_stop", "duration": 0.1},
                {"method": "t_up", "speed": 45, "duration": 0.3},
                {"method": "t_stop", "duration": 0.2}
            ],
            cooldown=2.0,
            priority=1
        )
        
        # 兴奋情感 - 快速旋转
        self.movement_sequences["excited_spin"] = MovementSequence(
            name="excited_spin",
            emotion_type=EmotionType.EXCITED,
            intensity_range=(0.7, 1.0),
            actions=[
                {"method": "turnRight", "speed": 80, "duration": 1.0},
                {"method": "t_stop", "duration": 0.2},
                {"method": "turnLeft", "speed": 80, "duration": 1.0},
                {"method": "t_stop", "duration": 0.3}
            ],
            cooldown=4.0,
            priority=3
        )
        
        # 兴奋情感 - 活力四射
        self.movement_sequences["excited_energetic"] = MovementSequence(
            name="excited_energetic",
            emotion_type=EmotionType.EXCITED,
            intensity_range=(0.5, 0.8),
            actions=[
                {"method": "moveLeft", "speed": 70, "duration": 0.4},
                {"method": "moveRight", "speed": 70, "duration": 0.4},
                {"method": "t_up", "speed": 70, "duration": 0.3},
                {"method": "t_down", "speed": 70, "duration": 0.3},
                {"method": "t_stop", "duration": 0.2}
            ],
            cooldown=3.0,
            priority=2
        )
        
        # 悲伤情感 - 缓慢移动
        self.movement_sequences["sad_slow"] = MovementSequence(
            name="sad_slow",
            emotion_type=EmotionType.SAD,
            intensity_range=(0.4, 1.0),
            actions=[
                {"method": "t_down", "speed": 25, "duration": 1.0},
                {"method": "t_stop", "duration": 0.5},
                {"method": "turnLeft", "speed": 20, "duration": 0.8},
                {"method": "t_stop", "duration": 1.0}
            ],
            cooldown=5.0,
            priority=1
        )
        
        # 困惑情感 - 犹豫动作
        self.movement_sequences["confused_hesitant"] = MovementSequence(
            name="confused_hesitant",
            emotion_type=EmotionType.CONFUSED,
            intensity_range=(0.3, 1.0),
            actions=[
                {"method": "turnLeft", "speed": 30, "duration": 0.3},
                {"method": "t_stop", "duration": 0.4},
                {"method": "turnRight", "speed": 30, "duration": 0.3},
                {"method": "t_stop", "duration": 0.4},
                {"method": "turnLeft", "speed": 30, "duration": 0.2},
                {"method": "t_stop", "duration": 0.6}
            ],
            cooldown=3.0,
            priority=1
        )
        
        # 思考情感 - 轻柔摆动
        self.movement_sequences["thinking_sway"] = MovementSequence(
            name="thinking_sway",
            emotion_type=EmotionType.THINKING,
            intensity_range=(0.2, 0.8),
            actions=[
                {"method": "moveLeft", "speed": 25, "duration": 0.6},
                {"method": "t_stop", "duration": 0.3},
                {"method": "moveRight", "speed": 25, "duration": 0.6},
                {"method": "t_stop", "duration": 0.3},
                {"method": "moveLeft", "speed": 25, "duration": 0.4},
                {"method": "t_stop", "duration": 0.5}
            ],
            cooldown=4.0,
            priority=1
        )
        
        # 生气情感 - 急促动作
        self.movement_sequences["angry_sharp"] = MovementSequence(
            name="angry_sharp",
            emotion_type=EmotionType.ANGRY,
            intensity_range=(0.5, 1.0),
            actions=[
                {"method": "t_up", "speed": 70, "duration": 0.2},
                {"method": "t_stop", "duration": 0.1},
                {"method": "t_down", "speed": 70, "duration": 0.2},
                {"method": "t_stop", "duration": 0.1},
                {"method": "turnRight", "speed": 80, "duration": 0.3},
                {"method": "t_stop", "duration": 0.2}
            ],
            cooldown=3.0,
            priority=2
        )
        
        # 惊讶情感 - 突然停止和后退
        self.movement_sequences["surprised_sudden"] = MovementSequence(
            name="surprised_sudden",
            emotion_type=EmotionType.SURPRISED,
            intensity_range=(0.4, 1.0),
            actions=[
                {"method": "t_stop", "duration": 0.3},
                {"method": "t_down", "speed": 60, "duration": 0.4},
                {"method": "t_stop", "duration": 0.5},
                {"method": "turnLeft", "speed": 40, "duration": 0.3},
                {"method": "turnRight", "speed": 40, "duration": 0.3},
                {"method": "t_stop", "duration": 0.3}
            ],
            cooldown=4.0,
            priority=2
        )
        
        logger.info(f"已初始化 {len(self.movement_sequences)} 个运动序列")
    
    def execute_emotional_movement(self, emotion: EmotionType, intensity: float = 0.5, 
                                 context: Optional[Dict] = None) -> bool:
        """
        执行情感驱动的运动
        Args:
            emotion: 情感类型
            intensity: 情感强度 (0.0-1.0)
            context: 额外上下文信息
        Returns:
            bool: 是否成功执行
        """
        if not self.safety_enabled:
            logger.warning("安全模式已禁用，跳过运动执行")
            return False
        
        with self.execution_lock:
            if self.is_executing:
                logger.info("正在执行其他动作，跳过当前请求")
                return False
            
            # 查找合适的运动序列
            suitable_sequences = self._find_suitable_sequences(emotion, intensity)
            
            if not suitable_sequences:
                logger.info(f"未找到适合的运动序列: {emotion.value} (强度: {intensity:.2f})")
                return False
            
            # 选择最佳序列
            selected_sequence = self._select_best_sequence(suitable_sequences, context)
            
            if not selected_sequence:
                return False
            
            # 执行运动序列
            return self._execute_sequence(selected_sequence, intensity)
    
    def _find_suitable_sequences(self, emotion: EmotionType, intensity: float) -> List[MovementSequence]:
        """查找适合的运动序列"""
        suitable = []
        current_time = time.time()
        
        for sequence in self.movement_sequences.values():
            # 检查情感类型匹配
            if sequence.emotion_type != emotion:
                continue
            
            # 检查强度范围
            min_intensity, max_intensity = sequence.intensity_range
            if not (min_intensity <= intensity <= max_intensity):
                continue
            
            # 检查冷却时间
            last_time = self.last_movement_time.get(sequence.name, 0)
            if current_time - last_time < sequence.cooldown:
                continue
            
            suitable.append(sequence)
        
        return suitable
    
    def _select_best_sequence(self, sequences: List[MovementSequence], 
                            context: Optional[Dict] = None) -> Optional[MovementSequence]:
        """选择最佳运动序列"""
        if not sequences:
            return None
        
        # 根据优先级和个性特征选择
        def score_sequence(seq: MovementSequence) -> float:
            score = seq.priority
            
            # 根据个性特征调整分数
            if seq.emotion_type == EmotionType.HAPPY:
                score *= self.personality.traits.get("playfulness", 1.0)
            elif seq.emotion_type == EmotionType.EXCITED:
                score *= self.personality.traits.get("energy_level", 1.0)
            elif seq.emotion_type in [EmotionType.CONFUSED, EmotionType.THINKING]:
                score *= self.personality.traits.get("curiosity", 1.0)
            
            # 添加随机因子，增加行为多样性
            score *= (0.8 + random.random() * 0.4)
            
            return score
        
        # 选择得分最高的序列
        best_sequence = max(sequences, key=score_sequence)
        return best_sequence
    
    def _execute_sequence(self, sequence: MovementSequence, intensity: float) -> bool:
        """执行运动序列"""
        try:
            self.is_executing = True
            self.current_sequence = sequence.name
            
            logger.info(f"开始执行运动序列: {sequence.name} (强度: {intensity:.2f})")
            
            # 记录执行时间
            self.last_movement_time[sequence.name] = time.time()
            
            # 根据强度调整动作参数
            adjusted_actions = self._adjust_actions_for_intensity(sequence.actions, intensity)
            
            # 执行每个动作
            for i, action in enumerate(adjusted_actions):
                if not self.safety_enabled:
                    logger.warning("安全检查失败，停止执行")
                    break
                
                # 执行动作
                success = self._execute_single_action(action)
                if not success:
                    logger.warning(f"动作执行失败: {action}")
                    break
                
                logger.debug(f"完成动作 {i+1}/{len(adjusted_actions)}: {action['method']}")
            
            logger.info(f"运动序列执行完成: {sequence.name}")
            return True
            
        except Exception as e:
            logger.error(f"执行运动序列时发生错误: {e}")
            return False
        
        finally:
            self.is_executing = False
            self.current_sequence = None
            # 确保机器人停止
            self.robot.t_stop(0.1)
    
    def _adjust_actions_for_intensity(self, actions: List[Dict], intensity: float) -> List[Dict]:
        """根据情感强度调整动作参数"""
        adjusted = []
        
        for action in actions:
            adjusted_action = action.copy()
            
            # 调整速度
            if "speed" in adjusted_action:
                base_speed = adjusted_action["speed"]
                # 根据强度和个性特征调整速度
                energy_factor = self.personality.traits.get("energy_level", 0.7)
                speed_multiplier = 0.5 + (intensity * energy_factor * 0.8)
                adjusted_action["speed"] = int(base_speed * speed_multiplier)
                adjusted_action["speed"] = max(15, min(100, adjusted_action["speed"]))  # 限制范围
            
            # 调整持续时间
            if "duration" in adjusted_action:
                base_duration = adjusted_action["duration"]
                # 高强度时动作更快，低强度时更慢
                duration_multiplier = 0.7 + (1.0 - intensity) * 0.6
                adjusted_action["duration"] = base_duration * duration_multiplier
                adjusted_action["duration"] = max(0.1, adjusted_action["duration"])  # 最小持续时间
            
            adjusted.append(adjusted_action)
        
        return adjusted
    
    def _execute_single_action(self, action: Dict) -> bool:
        """执行单个动作"""
        try:
            method_name = action.get("method")
            if not method_name:
                return False
            
            # 安全检查 - 障碍物避让系统优先级高于个性化动作
            if self.safety_manager:
                # 将方法名转换为命令格式进行安全检查
                command_mapping = {
                    't_up': 'forward',
                    't_down': 'backward',
                    'turnLeft': 'left',
                    'turnRight': 'right',
                    'moveLeft': 'move_left',
                    'moveRight': 'move_right',
                    't_stop': 'stop'
                }
                
                command = command_mapping.get(method_name, method_name)
                if not self.safety_manager.check_movement_safety(command):
                    logger.warning(f"安全检查失败，跳过动作: {method_name}")
                    return False
            
            # 获取机器人控制方法
            if not hasattr(self.robot, method_name):
                logger.error(f"机器人控制器没有方法: {method_name}")
                return False
            
            method = getattr(self.robot, method_name)
            
            # 准备参数
            args = []
            if "speed" in action:
                speed = action["speed"]
                # 根据安全状态调整速度
                if self.safety_manager:
                    safety_status = self.safety_manager.get_safety_status()
                    if safety_status['power_status'] == 'low':
                        speed = min(speed, 40)  # 低电量时限制最大速度
                    elif safety_status['power_status'] == 'critical':
                        speed = min(speed, 20)  # 危险电量时严格限制速度
                args.append(speed)
            if "duration" in action:
                args.append(action["duration"])
            
            # 执行方法
            method(*args)
            return True
            
        except Exception as e:
            logger.error(f"执行动作时发生错误: {e}")
            return False
    
    def handle_conversation_command(self, command: str, emotion: EmotionType = EmotionType.NEUTRAL) -> bool:
        """
        处理对话中的运动指令
        Args:
            command: 语音指令
            emotion: 当前情感状态
        Returns:
            bool: 是否成功处理
        """
        command = command.lower().strip()
        
        # 定义指令映射
        command_mappings = {
            # 移动指令
            "前进": {"method": "t_up", "speed": 50, "duration": 1.0},
            "后退": {"method": "t_down", "speed": 50, "duration": 1.0},
            "左转": {"method": "turnLeft", "speed": 50, "duration": 0.8},
            "右转": {"method": "turnRight", "speed": 50, "duration": 0.8},
            "左移": {"method": "moveLeft", "speed": 50, "duration": 1.0},
            "右移": {"method": "moveRight", "speed": 50, "duration": 1.0},
            "停止": {"method": "t_stop", "duration": 0.1},
            
            # 特殊动作
            "转圈": {"method": "turnRight", "speed": 60, "duration": 2.0},
            "转个圈": {"method": "turnRight", "speed": 60, "duration": 2.0},
            "跳舞": {"sequence": "happy_celebration"},
            "庆祝": {"sequence": "excited_spin"},
            "摆动": {"sequence": "thinking_sway"}
        }
        
        # 查找匹配的指令
        for key, action in command_mappings.items():
            if key in command:
                return self._execute_conversation_action(action, emotion)
        
        # 模糊匹配
        if any(word in command for word in ["走", "去", "移动"]):
            return self._execute_conversation_action(
                {"method": "t_up", "speed": 50, "duration": 1.0}, emotion
            )
        
        logger.info(f"未识别的运动指令: {command}")
        return False
    
    def _execute_conversation_action(self, action: Dict, emotion: EmotionType) -> bool:
        """执行对话触发的动作"""
        try:
            with self.execution_lock:
                if self.is_executing:
                    logger.info("正在执行其他动作，跳过对话指令")
                    return False
                
                # 如果是预定义序列
                if "sequence" in action:
                    sequence_name = action["sequence"]
                    if sequence_name in self.movement_sequences:
                        sequence = self.movement_sequences[sequence_name]
                        return self._execute_sequence(sequence, 0.7)
                    return False
                
                # 单个动作
                self.is_executing = True
                
                # 根据情感调整动作参数
                adjusted_action = self._adjust_action_for_emotion(action, emotion)
                
                # 执行动作
                success = self._execute_single_action(adjusted_action)
                
                return success
                
        except Exception as e:
            logger.error(f"执行对话动作时发生错误: {e}")
            return False
        
        finally:
            self.is_executing = False
            self.robot.t_stop(0.1)
    
    def _adjust_action_for_emotion(self, action: Dict, emotion: EmotionType) -> Dict:
        """根据情感调整动作参数"""
        adjusted = action.copy()
        
        # 情感对速度的影响
        emotion_speed_factors = {
            EmotionType.HAPPY: 1.2,
            EmotionType.EXCITED: 1.4,
            EmotionType.SAD: 0.6,
            EmotionType.CONFUSED: 0.8,
            EmotionType.THINKING: 0.7,
            EmotionType.ANGRY: 1.3,
            EmotionType.SURPRISED: 1.1,
            EmotionType.NEUTRAL: 1.0
        }
        
        speed_factor = emotion_speed_factors.get(emotion, 1.0)
        
        if "speed" in adjusted:
            adjusted["speed"] = int(adjusted["speed"] * speed_factor)
            adjusted["speed"] = max(20, min(100, adjusted["speed"]))
        
        return adjusted
    
    def get_personality_response_style(self) -> Dict[str, float]:
        """获取个性化响应风格"""
        return {
            "enthusiasm": self.personality.traits.get("energy_level", 0.7),
            "friendliness": self.personality.traits.get("friendliness", 0.8),
            "playfulness": self.personality.traits.get("playfulness", 0.9),
            "responsiveness": self.personality.traits.get("responsiveness", 0.8)
        }
    
    def adjust_movement_speed_for_emotion(self, base_speed: int, emotion: EmotionType, 
                                        intensity: float = 0.5) -> int:
        """根据情感调整运动速度"""
        # 基础情感速度调整
        emotion_factors = {
            EmotionType.HAPPY: 1.1,
            EmotionType.EXCITED: 1.3,
            EmotionType.SAD: 0.5,
            EmotionType.CONFUSED: 0.7,
            EmotionType.THINKING: 0.6,
            EmotionType.ANGRY: 1.2,
            EmotionType.SURPRISED: 1.0,
            EmotionType.NEUTRAL: 1.0
        }
        
        emotion_factor = emotion_factors.get(emotion, 1.0)
        
        # 强度影响
        intensity_factor = 0.5 + (intensity * 0.8)
        
        # 个性特征影响
        energy_factor = self.personality.traits.get("energy_level", 0.7)
        
        # 计算最终速度
        final_speed = int(base_speed * emotion_factor * intensity_factor * energy_factor)
        
        # 限制在安全范围内
        return max(15, min(100, final_speed))
    
    def update_personality_traits(self, traits: Dict[str, float]):
        """更新个性特征"""
        for trait_name, value in traits.items():
            if trait_name in self.personality.traits:
                self.personality.adjust_trait(trait_name, value)
                logger.info(f"个性特征已更新: {trait_name} = {value:.2f}")
                
                # 保存到记忆管理器
                if self.memory_manager:
                    self.memory_manager.store_user_preference(
                        'personality', trait_name, value, confidence=1.0
                    )
    
    def add_custom_sequence(self, sequence: MovementSequence):
        """添加自定义运动序列"""
        self.movement_sequences[sequence.name] = sequence
        logger.info(f"已添加自定义运动序列: {sequence.name}")
    
    def remove_sequence(self, sequence_name: str):
        """移除运动序列"""
        if sequence_name in self.movement_sequences:
            del self.movement_sequences[sequence_name]
            logger.info(f"已移除运动序列: {sequence_name}")
    
    def emergency_stop(self):
        """紧急停止"""
        logger.warning("执行紧急停止")
        self.safety_enabled = False
        self.is_executing = False
        self.robot.t_stop(0.1)
        time.sleep(0.5)
        self.safety_enabled = True
    
    def _load_personality_from_memory(self):
        """从记忆管理器加载个性设置"""
        try:
            # 加载个性特征
            personality_prefs = self.memory_manager.get_all_preferences('personality')
            for trait_name, value in personality_prefs.items():
                if trait_name in self.personality.traits and isinstance(value, (int, float)):
                    self.personality.traits[trait_name] = float(value)
            
            # 加载个性名称
            name = self.memory_manager.get_user_preference('personality', 'name')
            if name:
                self.personality.name = name
            
            # 加载运动风格
            movement_style = self.memory_manager.get_user_preference('behavior', 'movement_style')
            if movement_style:
                self.personality.movement_style = movement_style
            
            logger.info("已从记忆管理器加载个性设置")
            
        except Exception as e:
            logger.error(f"从记忆管理器加载个性设置失败: {e}")
    
    def learn_from_interaction(self, user_input: str, user_reaction: str, success: bool):
        """从交互中学习并调整个性"""
        if not self.memory_manager:
            return
        
        try:
            # 根据用户反应调整个性特征
            if success and user_reaction in ['开心', '满意', '喜欢']:
                # 强化当前行为模式
                current_energy = self.personality.traits.get('energy_level', 0.7)
                if '快' in user_input or '活泼' in user_input:
                    new_energy = min(1.0, current_energy + 0.1)
                    self.update_personality_traits({'energy_level': new_energy})
                
                current_playfulness = self.personality.traits.get('playfulness', 0.9)
                if '有趣' in user_input or '好玩' in user_input:
                    new_playfulness = min(1.0, current_playfulness + 0.1)
                    self.update_personality_traits({'playfulness': new_playfulness})
            
            elif not success or user_reaction in ['不满', '烦躁', '不喜欢']:
                # 调整行为模式
                if '太快' in user_input or '慢点' in user_input:
                    current_energy = self.personality.traits.get('energy_level', 0.7)
                    new_energy = max(0.1, current_energy - 0.1)
                    self.update_personality_traits({'energy_level': new_energy})
                
                if '太吵' in user_input or '安静' in user_input:
                    current_playfulness = self.personality.traits.get('playfulness', 0.9)
                    new_playfulness = max(0.1, current_playfulness - 0.1)
                    self.update_personality_traits({'playfulness': new_playfulness})
            
            # 记录学习事件
            self.memory_manager.store_user_preference(
                'learning_events', 
                f'interaction_{int(time.time())}',
                {
                    'user_input': user_input,
                    'user_reaction': user_reaction,
                    'success': success,
                    'timestamp': datetime.now().isoformat()
                },
                confidence=0.8
            )
            
        except Exception as e:
            logger.error(f"从交互中学习失败: {e}")
    
    def get_status(self) -> Dict:
        """获取个性管理器状态"""
        current_emotion = self.emotion_engine.get_current_emotional_state()
        
        return {
            "personality_name": self.personality.name,
            "personality_traits": self.personality.traits,
            "current_emotion": current_emotion.primary_emotion.value if current_emotion else "neutral",
            "emotion_intensity": current_emotion.intensity if current_emotion else 0.0,
            "is_executing": self.is_executing,
            "current_sequence": self.current_sequence,
            "available_sequences": list(self.movement_sequences.keys()),
            "safety_enabled": self.safety_enabled,
            "last_movements": {k: time.time() - v for k, v in self.last_movement_time.items()}
        }

# 测试函数
def test_personality_manager():
    """测试个性管理器功能"""
    print("=== 个性管理器测试 ===")
    
    # 创建模拟的机器人控制器
    class MockRobot:
        def __init__(self):
            self.actions = []
        
        def __getattr__(self, name):
            def mock_method(*args):
                self.actions.append(f"{name}({', '.join(map(str, args))})")
                print(f"执行动作: {name}({', '.join(map(str, args))})")
                time.sleep(0.1)  # 模拟执行时间
            return mock_method
    
    # 创建测试实例
    mock_robot = MockRobot()
    emotion_engine = EmotionEngine()
    personality_manager = PersonalityManager(mock_robot, emotion_engine)
    
    # 测试情感驱动运动
    test_emotions = [
        (EmotionType.HAPPY, 0.8),
        (EmotionType.EXCITED, 0.9),
        (EmotionType.SAD, 0.6),
        (EmotionType.CONFUSED, 0.5),
        (EmotionType.THINKING, 0.4)
    ]
    
    print("\n测试情感驱动运动:")
    for emotion, intensity in test_emotions:
        print(f"\n测试情感: {emotion.value} (强度: {intensity})")
        success = personality_manager.execute_emotional_movement(emotion, intensity)
        print(f"执行结果: {'成功' if success else '失败'}")
        time.sleep(1)
    
    # 测试对话指令
    print("\n测试对话指令:")
    test_commands = ["前进", "转个圈", "跳舞", "左转", "停止"]
    
    for command in test_commands:
        print(f"\n测试指令: {command}")
        success = personality_manager.handle_conversation_command(command, EmotionType.HAPPY)
        print(f"执行结果: {'成功' if success else '失败'}")
        time.sleep(0.5)
    
    # 显示状态
    print(f"\n=== 管理器状态 ===")
    status = personality_manager.get_status()
    for key, value in status.items():
        print(f"{key}: {value}")
    
    print(f"\n执行的动作历史:")
    for i, action in enumerate(mock_robot.actions[-10:], 1):  # 显示最近10个动作
        print(f"{i}. {action}")

if __name__ == "__main__":
    test_personality_manager()