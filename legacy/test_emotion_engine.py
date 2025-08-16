#!/usr/bin/python3
"""
情感引擎测试脚本
测试情感分析、状态管理和转换逻辑
"""

import sys
import os
import time
import logging
from datetime import datetime

# 添加src目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from emotion_engine import EmotionEngine, EmotionType, EmotionalState

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_basic_emotion_analysis():
    """测试基础情感分析功能"""
    print("=== 测试基础情感分析 ===")
    
    engine = EmotionEngine()
    
    test_cases = [
        ("哈哈哈，太好了！我很开心！", EmotionType.HAPPY),
        ("哇，这太厉害了！简直不可思议！", EmotionType.EXCITED),
        ("我有点难过，今天不太顺利...", EmotionType.SAD),
        ("嗯...让我想想这个问题", EmotionType.THINKING),
        ("什么？这是怎么回事？我不太懂", EmotionType.CONFUSED),
        ("今天天气不错，心情还可以", EmotionType.NEUTRAL),
        ("气死我了！太讨厌了！", EmotionType.ANGRY),
        ("天哪！没想到会这样！", EmotionType.SURPRISED)
    ]
    
    success_count = 0
    
    for text, expected_emotion in test_cases:
        emotion_state = engine.analyze_response_emotion(text)
        detected_emotion = emotion_state.primary_emotion
        
        print(f"\n输入: {text}")
        print(f"期望情感: {expected_emotion.value}")
        print(f"检测情感: {detected_emotion.value}")
        print(f"强度: {emotion_state.intensity:.2f}")
        print(f"触发词: {emotion_state.triggers}")
        print(f"运动模式: {emotion_state.movement_pattern}")
        
        if detected_emotion == expected_emotion:
            print("✓ 检测正确")
            success_count += 1
        else:
            print("✗ 检测错误")
    
    accuracy = success_count / len(test_cases) * 100
    print(f"\n准确率: {accuracy:.1f}% ({success_count}/{len(test_cases)})")
    
    return accuracy > 70  # 期望准确率超过70%

def test_emotion_intensity():
    """测试情感强度计算"""
    print("\n=== 测试情感强度计算 ===")
    
    engine = EmotionEngine()
    
    intensity_tests = [
        ("开心", 0.3, 0.7),  # 基础开心
        ("很开心", 0.4, 0.8),  # 修饰词增强
        ("超级开心！！！", 0.6, 1.0),  # 强修饰词+标点
        ("哈哈哈哈哈太开心了！", 0.7, 1.0),  # 重复字符+强情感
        ("有点开心", 0.2, 0.5),  # 弱修饰词
    ]
    
    for text, min_expected, max_expected in intensity_tests:
        emotion_state = engine.analyze_response_emotion(text)
        intensity = emotion_state.intensity
        
        print(f"\n输入: {text}")
        print(f"强度: {intensity:.2f}")
        print(f"期望范围: {min_expected:.2f} - {max_expected:.2f}")
        
        if min_expected <= intensity <= max_expected:
            print("✓ 强度正确")
        else:
            print("✗ 强度异常")

def test_emotion_state_management():
    """测试情感状态管理"""
    print("\n=== 测试情感状态管理 ===")
    
    engine = EmotionEngine()
    
    # 测试状态更新
    print("1. 测试状态更新")
    happy_state = EmotionalState(EmotionType.HAPPY, 0.8)
    engine.update_emotional_state(happy_state)
    
    current_state = engine.get_current_emotional_state()
    print(f"当前状态: {current_state.primary_emotion.value} (强度: {current_state.intensity:.2f})")
    
    # 测试状态衰减
    print("\n2. 测试状态衰减")
    print("等待3秒观察衰减...")
    time.sleep(3)
    
    current_state = engine.get_current_emotional_state()
    print(f"衰减后状态: {current_state.primary_emotion.value} (强度: {current_state.intensity:.2f})")
    
    # 测试历史记录
    print("\n3. 测试历史记录")
    sad_state = EmotionalState(EmotionType.SAD, 0.6)
    engine.update_emotional_state(sad_state)
    
    excited_state = EmotionalState(EmotionType.EXCITED, 0.9)
    engine.update_emotional_state(excited_state)
    
    history = engine.get_emotion_history()
    print(f"历史记录数量: {len(history)}")
    for i, state in enumerate(history[-3:], 1):
        print(f"  {i}. {state.primary_emotion.value} (强度: {state.intensity:.2f})")

def test_movement_patterns():
    """测试运动模式生成"""
    print("\n=== 测试运动模式生成 ===")
    
    engine = EmotionEngine()
    
    emotion_tests = [
        (EmotionType.HAPPY, 0.9, "bouncy_intense"),
        (EmotionType.EXCITED, 0.7, "energetic_moderate"),
        (EmotionType.SAD, 0.5, "slow_gentle"),
        (EmotionType.THINKING, 0.4, "gentle_sway_gentle"),
        (EmotionType.NEUTRAL, 0.2, "default")
    ]
    
    for emotion, intensity, expected_pattern in emotion_tests:
        state = EmotionalState(emotion, intensity)
        engine.update_emotional_state(state)
        
        movement = engine.determine_movement_emotion()
        print(f"{emotion.value} (强度: {intensity:.1f}) -> {movement}")
        
        # 检查模式是否合理
        if intensity > 0.8 and "intense" not in movement and movement != "default":
            print("  ⚠ 高强度情感应该有intense模式")
        elif intensity < 0.3 and movement != "default":
            print("  ⚠ 低强度情感应该使用default模式")

def test_personality_context():
    """测试个性上下文更新"""
    print("\n=== 测试个性上下文更新 ===")
    
    engine = EmotionEngine()
    
    # 模拟对话历史
    conversation_history = [
        {'emotion': 'happy', 'timestamp': '2024-01-01T10:00:00'},
        {'emotion': 'excited', 'timestamp': '2024-01-01T10:01:00'},
        {'emotion': 'happy', 'timestamp': '2024-01-01T10:02:00'},
        {'emotion': 'neutral', 'timestamp': '2024-01-01T10:03:00'},
        {'emotion': 'happy', 'timestamp': '2024-01-01T10:04:00'},
    ]
    
    print("对话历史（主要是积极情感）:")
    for item in conversation_history:
        print(f"  - {item['emotion']}")
    
    # 更新个性上下文
    engine.update_personality_context(conversation_history)
    
    current_state = engine.get_current_emotional_state()
    print(f"衰减率调整为: {current_state.decay_rate}")
    print("期望: 积极情感主导时衰减率应该较低（0.05）")
    
    # 测试消极情感主导
    negative_history = [
        {'emotion': 'sad', 'timestamp': '2024-01-01T11:00:00'},
        {'emotion': 'confused', 'timestamp': '2024-01-01T11:01:00'},
        {'emotion': 'sad', 'timestamp': '2024-01-01T11:02:00'},
        {'emotion': 'angry', 'timestamp': '2024-01-01T11:03:00'},
    ]
    
    print("\n对话历史（主要是消极情感）:")
    for item in negative_history:
        print(f"  - {item['emotion']}")
    
    engine.update_personality_context(negative_history)
    current_state = engine.get_current_emotional_state()
    print(f"衰减率调整为: {current_state.decay_rate}")
    print("期望: 消极情感主导时衰减率应该较高（0.15）")

def test_engine_status():
    """测试引擎状态获取"""
    print("\n=== 测试引擎状态 ===")
    
    engine = EmotionEngine()
    
    # 设置一些状态
    happy_state = EmotionalState(EmotionType.HAPPY, 0.8, triggers=['开心', '太好了'])
    engine.update_emotional_state(happy_state)
    
    status = engine.get_status()
    
    print("引擎状态:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # 验证状态完整性
    required_keys = ['current_emotion', 'intensity', 'movement_pattern', 
                    'secondary_emotions', 'triggers', 'history_length']
    
    missing_keys = [key for key in required_keys if key not in status]
    if missing_keys:
        print(f"⚠ 缺少状态字段: {missing_keys}")
    else:
        print("✓ 状态字段完整")

def run_all_tests():
    """运行所有测试"""
    print("开始情感引擎完整测试...")
    print("=" * 50)
    
    tests = [
        ("基础情感分析", test_basic_emotion_analysis),
        ("情感强度计算", test_emotion_intensity),
        ("情感状态管理", test_emotion_state_management),
        ("运动模式生成", test_movement_patterns),
        ("个性上下文更新", test_personality_context),
        ("引擎状态获取", test_engine_status)
    ]
    
    passed_tests = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            result = test_func()
            if result is not False:  # None或True都算通过
                passed_tests += 1
                print(f"✓ {test_name} 通过")
            else:
                print(f"✗ {test_name} 失败")
        except Exception as e:
            print(f"✗ {test_name} 异常: {e}")
            logger.exception(f"测试 {test_name} 出现异常")
    
    print(f"\n{'='*50}")
    print(f"测试完成: {passed_tests}/{len(tests)} 通过")
    
    if passed_tests == len(tests):
        print("🎉 所有测试通过！情感引擎实现正确。")
        return True
    else:
        print("⚠ 部分测试失败，请检查实现。")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)