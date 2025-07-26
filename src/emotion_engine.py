#!/usr/bin/python3
"""
情感引擎 - 分析AI回复内容确定情感状态
支持情感强度计算、状态转换逻辑和持续时间管理
"""

import re
import time
import logging
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import jieba
import jieba.posseg as pseg

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmotionType(Enum):
    """情感类型枚举"""
    HAPPY = "happy"
    EXCITED = "excited"
    SAD = "sad"
    CONFUSED = "confused"
    THINKING = "thinking"
    NEUTRAL = "neutral"
    ANGRY = "angry"
    SURPRISED = "surprised"

@dataclass
class EmotionalState:
    """情感状态数据模型"""
    primary_emotion: EmotionType
    intensity: float  # 0.0 到 1.0
    secondary_emotions: Dict[EmotionType, float] = field(default_factory=dict)
    duration: float = 0.0  # 持续时间（秒）
    triggers: List[str] = field(default_factory=list)  # 触发词
    movement_pattern: str = "default"
    timestamp: datetime = field(default_factory=datetime.now)
    decay_rate: float = 0.1  # 情感衰减率
    
    def __post_init__(self):
        """初始化后处理"""
        # 确保强度在有效范围内
        self.intensity = max(0.0, min(1.0, self.intensity))
        
        # 设置运动模式
        self.movement_pattern = self._get_movement_pattern()
    
    def _get_movement_pattern(self) -> str:
        """根据情感类型获取运动模式"""
        movement_mapping = {
            EmotionType.HAPPY: "bouncy",
            EmotionType.EXCITED: "energetic", 
            EmotionType.SAD: "slow",
            EmotionType.CONFUSED: "hesitant",
            EmotionType.THINKING: "gentle_sway",
            EmotionType.NEUTRAL: "default",
            EmotionType.ANGRY: "sharp",
            EmotionType.SURPRISED: "sudden"
        }
        return movement_mapping.get(self.primary_emotion, "default")
    
    def update_intensity(self, delta_time: float):
        """更新情感强度（随时间衰减）"""
        if self.primary_emotion != EmotionType.NEUTRAL:
            decay = self.decay_rate * delta_time
            self.intensity = max(0.0, self.intensity - decay)
            
            # 如果强度太低，转为中性情感
            if self.intensity < 0.1:
                self.primary_emotion = EmotionType.NEUTRAL
                self.intensity = 0.5
    
    def is_expired(self, max_duration: float = 30.0) -> bool:
        """检查情感状态是否过期"""
        elapsed = (datetime.now() - self.timestamp).total_seconds()
        return elapsed > max_duration or self.intensity < 0.1

class EmotionEngine:
    """情感引擎 - 分析文本情感并管理情感状态"""
    
    def __init__(self):
        """初始化情感引擎"""
        # 当前情感状态
        self.current_state = EmotionalState(
            primary_emotion=EmotionType.NEUTRAL,
            intensity=0.5
        )
        
        # 情感历史
        self.emotion_history: List[EmotionalState] = []
        self.max_history_length = 50
        
        # 线程锁
        self.state_lock = threading.Lock()
        
        # 初始化情感词典
        self._initialize_emotion_keywords()
        
        # 初始化jieba分词
        jieba.initialize()
        
        logger.info("情感引擎初始化完成")
    
    def _initialize_emotion_keywords(self):
        """初始化情感关键词词典"""
        self.emotion_keywords = {
            EmotionType.HAPPY: {
                'keywords': ['开心', '高兴', '快乐', '愉快', '喜悦', '欢乐', '兴高采烈', 
                           '心情好', '太好了', '棒', '喜欢', '满意', '舒服', '美好'],
                'patterns': [r'哈+', r'嘿+', r'呵+'],
                'punctuation': ['😊', '😄', '😃', '🎉'],
                'weight': 1.0
            },
            
            EmotionType.EXCITED: {
                'keywords': ['兴奋', '激动', '太棒了', '厉害', '惊喜', '震撼', '精彩',
                           '不可思议', '太酷了', 'amazing', '哇', '天哪', '牛'],
                'patterns': [r'哇+', r'啊+(?=.*(棒|好|厉害))', r'太.*了'],
                'punctuation': ['!', '！', '🤩', '😍', '🔥'],
                'weight': 1.2
            },
            
            EmotionType.SAD: {
                'keywords': ['难过', '伤心', '不开心', '失望', '沮丧', '郁闷', '悲伤',
                           '痛苦', '不舒服', '糟糕', '倒霉', '哭', '眼泪'],
                'patterns': [r'呜+', r'555+', r'T_T', r'哎+'],
                'punctuation': ['😢', '😭', '😞', '💔'],
                'weight': 0.8
            },
            
            EmotionType.CONFUSED: {
                'keywords': ['困惑', '不懂', '疑惑', '奇怪', '为什么', '怎么回事', 
                           '什么意思', '不明白', '搞不懂', '莫名其妙'],
                'patterns': [r'.*吗\?', r'什么.*', r'为什么.*', r'怎么.*'],
                'punctuation': ['?', '？', '🤔', '😕'],
                'weight': 0.9
            },
            
            EmotionType.THINKING: {
                'keywords': ['想想', '思考', '让我想想', '考虑', '琢磨', '研究', 
                           '分析', '判断', '评估', '嗯'],
                'patterns': [r'嗯+', r'额+', r'呃+', r'\.\.\.+'],
                'punctuation': ['🤔', '💭'],
                'weight': 0.7
            },
            
            EmotionType.ANGRY: {
                'keywords': ['生气', '愤怒', '气死了', '讨厌', '烦', '恼火', '火大',
                           '受不了', '忍不了', '可恶', '该死'],
                'patterns': [r'哼+', r'切+'],
                'punctuation': ['😠', '😡', '💢'],
                'weight': 1.1
            },
            
            EmotionType.SURPRISED: {
                'keywords': ['惊讶', '意外', '没想到', '竟然', '居然', '真的吗', 
                           '不会吧', '天哪', '我的天'],
                'patterns': [r'哇+(?!.*(棒|好|厉害))', r'啊+(?!.*(棒|好|厉害))'],
                'punctuation': ['😲', '😯', '🤯'],
                'weight': 1.0
            }
        }
        
        # 情感修饰词权重
        self.intensity_modifiers = {
            '非常': 1.5, '特别': 1.4, '超级': 1.6, '极其': 1.7, '十分': 1.3,
            '很': 1.2, '挺': 1.1, '比较': 0.9, '有点': 0.8, '稍微': 0.7,
            '一点': 0.6, '略': 0.5, '太': 1.8, '超': 1.5, '巨': 1.4
        }
    
    def analyze_response_emotion(self, text: str, context: Optional[Dict] = None) -> EmotionalState:
        """
        分析AI回复文本的情感
        Args:
            text: 要分析的文本
            context: 对话上下文（可选）
        Returns:
            EmotionalState: 检测到的情感状态
        """
        if not text or not text.strip():
            return EmotionalState(EmotionType.NEUTRAL, 0.5)
        
        # 文本预处理
        text = text.strip().lower()
        
        # 分词处理
        words = list(jieba.cut(text))
        pos_tags = list(pseg.cut(text))
        
        # 计算各种情感的得分
        emotion_scores = self._calculate_emotion_scores(text, words, pos_tags)
        
        # 确定主要情感
        primary_emotion, primary_score = self._determine_primary_emotion(emotion_scores)
        
        # 计算情感强度
        intensity = self._calculate_intensity(text, primary_score, words)
        
        # 获取次要情感
        secondary_emotions = self._get_secondary_emotions(emotion_scores, primary_emotion)
        
        # 获取触发词
        triggers = self._extract_triggers(text, primary_emotion)
        
        # 创建情感状态
        emotional_state = EmotionalState(
            primary_emotion=primary_emotion,
            intensity=intensity,
            secondary_emotions=secondary_emotions,
            triggers=triggers
        )
        
        logger.info(f"情感分析结果: {primary_emotion.value} (强度: {intensity:.2f})")
        
        return emotional_state
    
    def _calculate_emotion_scores(self, text: str, words: List[str], pos_tags) -> Dict[EmotionType, float]:
        """计算各种情感的得分"""
        scores = {emotion: 0.0 for emotion in EmotionType}
        
        for emotion_type, emotion_data in self.emotion_keywords.items():
            score = 0.0
            
            # 关键词匹配
            for keyword in emotion_data['keywords']:
                if keyword in text:
                    score += emotion_data['weight']
            
            # 正则模式匹配
            for pattern in emotion_data['patterns']:
                matches = re.findall(pattern, text)
                score += len(matches) * emotion_data['weight'] * 0.8
            
            # 标点符号匹配
            for punct in emotion_data['punctuation']:
                score += text.count(punct) * emotion_data['weight'] * 0.6
            
            scores[emotion_type] = score
        
        return scores
    
    def _determine_primary_emotion(self, emotion_scores: Dict[EmotionType, float]) -> Tuple[EmotionType, float]:
        """确定主要情感"""
        # 排除中性情感进行比较
        non_neutral_scores = {k: v for k, v in emotion_scores.items() if k != EmotionType.NEUTRAL}
        
        if not non_neutral_scores or max(non_neutral_scores.values()) < 0.3:
            return EmotionType.NEUTRAL, 0.5
        
        primary_emotion = max(non_neutral_scores, key=non_neutral_scores.get)
        primary_score = non_neutral_scores[primary_emotion]
        
        return primary_emotion, primary_score
    
    def _calculate_intensity(self, text: str, base_score: float, words: List[str]) -> float:
        """计算情感强度"""
        intensity = min(base_score / 2.0, 1.0)  # 基础强度
        
        # 修饰词影响
        for word in words:
            if word in self.intensity_modifiers:
                intensity *= self.intensity_modifiers[word]
        
        # 重复字符影响（如"哈哈哈"）
        repeat_patterns = re.findall(r'(.)\1{2,}', text)
        if repeat_patterns:
            intensity *= (1 + len(repeat_patterns) * 0.2)
        
        # 标点符号影响
        exclamation_count = text.count('!') + text.count('！')
        if exclamation_count > 0:
            intensity *= (1 + exclamation_count * 0.1)
        
        # 确保在有效范围内
        return max(0.1, min(1.0, intensity))
    
    def _get_secondary_emotions(self, emotion_scores: Dict[EmotionType, float], 
                              primary_emotion: EmotionType) -> Dict[EmotionType, float]:
        """获取次要情感"""
        secondary = {}
        
        for emotion, score in emotion_scores.items():
            if emotion != primary_emotion and score > 0.2:
                # 归一化次要情感强度
                secondary[emotion] = min(score / 3.0, 0.8)
        
        return secondary
    
    def _extract_triggers(self, text: str, emotion: EmotionType) -> List[str]:
        """提取情感触发词"""
        triggers = []
        
        if emotion in self.emotion_keywords:
            emotion_data = self.emotion_keywords[emotion]
            
            # 查找匹配的关键词
            for keyword in emotion_data['keywords']:
                if keyword in text:
                    triggers.append(keyword)
            
            # 查找匹配的模式
            for pattern in emotion_data['patterns']:
                matches = re.findall(pattern, text)
                triggers.extend(matches)
        
        return triggers[:5]  # 限制触发词数量
    
    def update_emotional_state(self, new_state: EmotionalState):
        """更新当前情感状态"""
        with self.state_lock:
            # 保存历史状态
            if self.current_state:
                self.emotion_history.append(self.current_state)
                
                # 限制历史长度
                if len(self.emotion_history) > self.max_history_length:
                    self.emotion_history = self.emotion_history[-self.max_history_length:]
            
            # 更新当前状态
            self.current_state = new_state
            
            logger.info(f"情感状态已更新: {new_state.primary_emotion.value} "
                       f"(强度: {new_state.intensity:.2f})")
    
    def get_current_emotional_state(self) -> EmotionalState:
        """获取当前情感状态"""
        with self.state_lock:
            # 检查状态是否需要衰减
            if self.current_state:
                current_time = datetime.now()
                delta_time = (current_time - self.current_state.timestamp).total_seconds()
                
                if delta_time > 1.0:  # 每秒更新一次
                    self.current_state.update_intensity(delta_time)
                    self.current_state.timestamp = current_time
            
            return self.current_state
    
    def determine_movement_emotion(self, context: Optional[Dict] = None) -> str:
        """根据情感状态确定运动模式"""
        current_state = self.get_current_emotional_state()
        
        if not current_state:
            return "default"
        
        # 考虑情感强度调整运动模式
        base_pattern = current_state.movement_pattern
        intensity = current_state.intensity
        
        # 根据强度调整运动模式
        if intensity > 0.8:
            return f"{base_pattern}_intense"
        elif intensity > 0.6:
            return f"{base_pattern}_moderate"
        elif intensity > 0.3:
            return f"{base_pattern}_gentle"
        else:
            return "default"
    
    def update_personality_context(self, conversation_history: List[Dict]):
        """根据对话历史更新个性上下文"""
        if not conversation_history:
            return
        
        # 分析最近的情感趋势
        recent_emotions = []
        for item in conversation_history[-10:]:  # 最近10条对话
            if 'emotion' in item:
                try:
                    emotion_type = EmotionType(item['emotion'])
                    recent_emotions.append(emotion_type)
                except ValueError:
                    continue
        
        # 统计情感分布
        emotion_counts = {}
        for emotion in recent_emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        # 根据情感趋势调整衰减率
        if emotion_counts:
            dominant_emotion = max(emotion_counts, key=emotion_counts.get)
            
            # 如果主导情感是积极的，减慢衰减
            if dominant_emotion in [EmotionType.HAPPY, EmotionType.EXCITED]:
                self.current_state.decay_rate = 0.05
            # 如果主导情感是消极的，加快衰减
            elif dominant_emotion in [EmotionType.SAD, EmotionType.ANGRY]:
                self.current_state.decay_rate = 0.15
            else:
                self.current_state.decay_rate = 0.1
        
        logger.info(f"个性上下文已更新，当前衰减率: {self.current_state.decay_rate}")
    
    def get_emotion_history(self) -> List[EmotionalState]:
        """获取情感历史"""
        with self.state_lock:
            return self.emotion_history.copy()
    
    def clear_emotion_history(self):
        """清空情感历史"""
        with self.state_lock:
            self.emotion_history = []
            self.current_state = EmotionalState(EmotionType.NEUTRAL, 0.5)
        
        logger.info("情感历史已清空")
    
    def get_status(self) -> Dict:
        """获取情感引擎状态"""
        current_state = self.get_current_emotional_state()
        
        return {
            'current_emotion': current_state.primary_emotion.value,
            'intensity': current_state.intensity,
            'movement_pattern': current_state.movement_pattern,
            'secondary_emotions': {k.value: v for k, v in current_state.secondary_emotions.items()},
            'triggers': current_state.triggers,
            'history_length': len(self.emotion_history),
            'decay_rate': current_state.decay_rate,
            'timestamp': current_state.timestamp.isoformat()
        }

# 测试函数
def test_emotion_engine():
    """测试情感引擎功能"""
    print("=== 情感引擎测试 ===")
    
    # 创建情感引擎
    engine = EmotionEngine()
    
    # 测试文本
    test_texts = [
        "哈哈哈，太好了！我很开心！",
        "哇，这太厉害了！简直不可思议！",
        "我有点难过，今天不太顺利...",
        "嗯...让我想想这个问题",
        "什么？这是怎么回事？我不太懂",
        "今天天气不错，心情还可以"
    ]
    
    print("测试情感分析:")
    for i, text in enumerate(test_texts, 1):
        print(f"\n{i}. 输入: {text}")
        
        # 分析情感
        emotion_state = engine.analyze_response_emotion(text)
        
        # 更新状态
        engine.update_emotional_state(emotion_state)
        
        print(f"   情感: {emotion_state.primary_emotion.value}")
        print(f"   强度: {emotion_state.intensity:.2f}")
        print(f"   运动模式: {emotion_state.movement_pattern}")
        print(f"   触发词: {emotion_state.triggers}")
        
        # 测试运动情感
        movement = engine.determine_movement_emotion()
        print(f"   推荐运动: {movement}")
        
        time.sleep(1)  # 模拟时间流逝
    
    # 显示状态
    print(f"\n=== 引擎状态 ===")
    status = engine.get_status()
    for key, value in status.items():
        print(f"{key}: {value}")
    
    # 测试历史
    print(f"\n=== 情感历史 ===")
    history = engine.get_emotion_history()
    for i, state in enumerate(history[-3:], 1):  # 显示最近3个状态
        print(f"{i}. {state.primary_emotion.value} (强度: {state.intensity:.2f})")

if __name__ == "__main__":
    test_emotion_engine()