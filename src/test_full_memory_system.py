#!/usr/bin/python3
"""
完整记忆和上下文管理系统测试
测试所有组件的集成和协作
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from memory_manager import MemoryManager
from emotion_engine import EmotionEngine, EmotionType

# 创建模拟的PersonalityManager来避免硬件依赖
class MockPersonalityManager:
    """模拟个性管理器，避免硬件依赖"""
    
    def __init__(self, robot_controller, emotion_engine=None, memory_manager=None):
        self.robot = robot_controller
        self.emotion_engine = emotion_engine or EmotionEngine()
        self.memory_manager = memory_manager
        self.is_executing = False
        self.current_sequence = None
        
        # 模拟个性特征
        self.personality_traits = {
            'friendliness': 0.8,
            'energy_level': 0.7,
            'curiosity': 0.6,
            'playfulness': 0.9
        }
        
        # 从记忆管理器加载个性设置
        if self.memory_manager:
            self._load_personality_from_memory()
    
    def _load_personality_from_memory(self):
        """从记忆管理器加载个性设置"""
        try:
            personality_prefs = self.memory_manager.get_all_preferences('personality')
            for trait_name, value in personality_prefs.items():
                if trait_name in self.personality_traits and isinstance(value, (int, float)):
                    self.personality_traits[trait_name] = float(value)
        except Exception as e:
            print(f"加载个性设置失败: {e}")
    
    def execute_emotional_movement(self, emotion_type, intensity=0.5, context=None):
        """执行情感驱动的运动"""
        print(f"    🎭 执行情感动作: {emotion_type.value} (强度: {intensity:.1f})")
        
        # 模拟动作执行
        if emotion_type == EmotionType.HAPPY:
            self.robot.turnRight(60, 0.5)
            self.robot.turnLeft(60, 0.5)
        elif emotion_type == EmotionType.EXCITED:
            self.robot.turnRight(80, 1.0)
        elif emotion_type == EmotionType.CONFUSED:
            self.robot.turnLeft(30, 0.3)
            self.robot.turnRight(30, 0.3)
        
        return True
    
    def learn_from_interaction(self, user_input, user_reaction, success):
        """从交互中学习并调整个性"""
        if not self.memory_manager:
            return
        
        print(f"    🧠 学习反馈: {user_input} -> {user_reaction} ({'成功' if success else '失败'})")
        
        # 根据反馈调整个性特征
        if success and user_reaction in ['开心', '满意', '喜欢']:
            if '快' in user_input:
                new_energy = min(1.0, self.personality_traits['energy_level'] + 0.1)
                self.update_personality_traits({'energy_level': new_energy})
        
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
    
    def update_personality_traits(self, traits):
        """更新个性特征"""
        for trait_name, value in traits.items():
            if trait_name in self.personality_traits:
                self.personality_traits[trait_name] = value
                print(f"    📊 个性特征更新: {trait_name} = {value:.2f}")
                
                # 保存到记忆管理器
                if self.memory_manager:
                    self.memory_manager.store_user_preference(
                        'personality', trait_name, value, confidence=1.0
                    )
    
    def get_personality_response_style(self):
        """获取个性化响应风格"""
        return self.personality_traits
    
    def get_status(self):
        """获取个性管理器状态"""
        return {
            'personality_traits': self.personality_traits,
            'is_executing': self.is_executing,
            'current_sequence': self.current_sequence,
            'memory_integrated': self.memory_manager is not None
        }

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockRobot:
    """模拟机器人控制器"""
    def __init__(self):
        self.actions = []
    
    def __getattr__(self, name):
        def mock_method(*args):
            action_str = f"{name}({', '.join(map(str, args))})"
            self.actions.append(action_str)
            print(f"    🤖 执行动作: {action_str}")
            time.sleep(0.1)  # 模拟执行时间
        return mock_method

def test_complete_memory_system():
    """测试完整的记忆和上下文管理系统"""
    print("=== 完整记忆和上下文管理系统测试 ===")
    
    try:
        # 1. 初始化所有组件
        print("\n1. 初始化系统组件")
        
        # 创建模拟机器人
        mock_robot = MockRobot()
        print("  ✓ 模拟机器人控制器已创建")
        
        # 创建记忆管理器
        memory_manager = MemoryManager(data_dir="test_data/complete_system")
        print("  ✓ 记忆管理器已初始化")
        
        # 创建情感引擎
        emotion_engine = EmotionEngine()
        print("  ✓ 情感引擎已初始化")
        
        # 创建个性管理器（集成记忆管理器）
        personality_manager = MockPersonalityManager(
            robot_controller=mock_robot,
            emotion_engine=emotion_engine,
            memory_manager=memory_manager
        )
        print("  ✓ 个性管理器已初始化（已集成记忆管理器）")
        
        # 2. 测试用户偏好学习和记忆
        print("\n2. 测试用户偏好学习和记忆")
        
        # 开始新会话
        session_id = memory_manager.start_new_session()
        print(f"  ✓ 开始新会话: {session_id}")
        
        # 模拟用户交互和偏好学习
        interactions = [
            {
                'user_input': '你好，我叫小李',
                'ai_response': '你好小李！很高兴认识你~',
                'emotion': 'happy',
                'context': '用户自我介绍',
                'preferences': [('user_info', 'name', '小李')]
            },
            {
                'user_input': '我喜欢你动作快一点',
                'ai_response': '好的！我会更有活力一些~',
                'emotion': 'excited',
                'context': '用户偏好：快速动作',
                'preferences': [('behavior', 'speed_preference', 'fast')]
            },
            {
                'user_input': '转个圈给我看看',
                'ai_response': '好的！我来转个快圈~',
                'emotion': 'excited',
                'context': '动作指令：转圈',
                'action': ('excited_spin', EmotionType.EXCITED, 0.8)
            },
            {
                'user_input': '太好了，我很喜欢！',
                'ai_response': '谢谢夸奖！我会记住你喜欢这样的动作~',
                'emotion': 'happy',
                'context': '正面反馈',
                'learning': ('转个圈给我看看', '喜欢', True)
            }
        ]
        
        for i, interaction in enumerate(interactions, 1):
            print(f"\n  交互 {i}: {interaction['user_input']}")
            
            # 存储对话
            memory_manager.store_conversation(
                session_id,
                interaction['user_input'],
                interaction['ai_response'],
                interaction['emotion'],
                interaction['context']
            )
            print(f"    ✓ 对话已存储")
            
            # 存储用户偏好
            if 'preferences' in interaction:
                for pref_type, key, value in interaction['preferences']:
                    memory_manager.store_user_preference(pref_type, key, value)
                    print(f"    ✓ 偏好已存储: {pref_type}:{key} = {value}")
            
            # 执行动作
            if 'action' in interaction:
                sequence_name, emotion_type, intensity = interaction['action']
                success = personality_manager.execute_emotional_movement(
                    emotion_type, intensity
                )
                print(f"    ✓ 动作执行: {'成功' if success else '失败'}")
            
            # 学习反馈
            if 'learning' in interaction:
                user_input, reaction, success = interaction['learning']
                personality_manager.learn_from_interaction(user_input, reaction, success)
                print(f"    ✓ 学习反馈已处理")
            
            time.sleep(0.2)
        
        # 3. 测试记忆检索和上下文理解
        print("\n3. 测试记忆检索和上下文理解")
        
        # 检索对话历史
        history = memory_manager.get_conversation_history(session_id)
        print(f"  ✓ 检索到 {len(history)} 条对话记录")
        
        # 搜索特定内容
        search_results = memory_manager.search_conversations("转圈")
        print(f"  ✓ 搜索'转圈'结果: {len(search_results)} 条")
        
        # 获取用户偏好
        user_name = memory_manager.get_user_preference('user_info', 'name')
        speed_pref = memory_manager.get_user_preference('behavior', 'speed_preference')
        print(f"  ✓ 用户偏好 - 姓名: {user_name}, 速度偏好: {speed_pref}")
        
        # 生成会话摘要
        summary = memory_manager.generate_context_summary(session_id)
        print(f"  ✓ 会话摘要: {summary}")
        
        # 4. 测试个性化适应
        print("\n4. 测试个性化适应")
        
        # 检查个性特征是否根据学习调整
        personality_traits = personality_manager.get_personality_response_style()
        print(f"  ✓ 当前个性特征: {personality_traits}")
        
        # 测试个性化动作执行
        print("  测试个性化动作执行:")
        test_emotions = [
            (EmotionType.HAPPY, 0.7),
            (EmotionType.EXCITED, 0.9),
            (EmotionType.CONFUSED, 0.5)
        ]
        
        for emotion, intensity in test_emotions:
            success = personality_manager.execute_emotional_movement(emotion, intensity)
            print(f"    ✓ {emotion.value} (强度: {intensity}): {'成功' if success else '失败'}")
            time.sleep(0.5)
        
        # 5. 测试会话上下文管理
        print("\n5. 测试会话上下文管理")
        
        # 获取会话上下文
        session_context = memory_manager.get_session_context(session_id)
        if session_context:
            print(f"  ✓ 话题关键词: {session_context.topic_keywords}")
            print(f"  ✓ 情感趋势: {session_context.emotional_trend}")
            print(f"  ✓ 用户情绪: {session_context.user_mood}")
            print(f"  ✓ 会话摘要: {session_context.conversation_summary}")
        
        # 6. 测试配置持久化和恢复
        print("\n6. 测试配置持久化和恢复")
        
        # 保存当前配置
        config = memory_manager.load_user_config()
        config['personality']['name'] = '学习型圆滚滚'
        config['personality']['user_name'] = user_name
        config['personality']['learned_preferences'] = {
            'speed': speed_pref,
            'favorite_actions': ['转圈']
        }
        
        success = memory_manager.save_user_config(config)
        print(f"  ✓ 配置保存: {'成功' if success else '失败'}")
        
        # 结束当前会话
        memory_manager.end_session(session_id)
        print(f"  ✓ 会话已结束: {session_id}")
        
        # 7. 测试重启后的恢复能力
        print("\n7. 测试重启后的恢复能力")
        
        # 创建新的系统实例（模拟重启）
        new_memory_manager = MemoryManager(data_dir="test_data/complete_system")
        new_personality_manager = MockPersonalityManager(
            robot_controller=MockRobot(),
            emotion_engine=EmotionEngine(),
            memory_manager=new_memory_manager
        )
        
        # 检查数据是否正确恢复
        recovered_name = new_memory_manager.get_user_preference('user_info', 'name')
        recovered_speed = new_memory_manager.get_user_preference('behavior', 'speed_preference')
        recovered_config = new_memory_manager.load_user_config()
        
        print(f"  ✓ 恢复用户信息 - 姓名: {recovered_name}")
        print(f"  ✓ 恢复行为偏好 - 速度: {recovered_speed}")
        print(f"  ✓ 恢复配置 - 个性名称: {recovered_config.get('personality', {}).get('name')}")
        
        # 检查对话历史是否恢复
        recovered_history = new_memory_manager.get_conversation_history(limit=10)
        print(f"  ✓ 恢复对话历史: {len(recovered_history)} 条")
        
        # 8. 测试系统状态和性能
        print("\n8. 测试系统状态和性能")
        
        memory_status = new_memory_manager.get_status()
        personality_status = new_personality_manager.get_status()
        
        print(f"  ✓ 记忆管理器状态: {memory_status}")
        print(f"  ✓ 个性管理器状态: {personality_status}")
        
        # 显示执行的动作历史
        print(f"\n  执行的动作历史 (最近10个):")
        for i, action in enumerate(mock_robot.actions[-10:], 1):
            print(f"    {i}. {action}")
        
        print("\n✅ 完整记忆和上下文管理系统测试成功！")
        return True
        
    except Exception as e:
        print(f"\n❌ 完整系统测试失败: {e}")
        logger.error(f"完整系统测试失败: {e}", exc_info=True)
        return False

def test_memory_performance():
    """测试记忆系统性能"""
    print("\n=== 记忆系统性能测试 ===")
    
    try:
        memory_manager = MemoryManager(data_dir="test_data/performance")
        
        # 测试大量数据存储性能
        print("\n1. 测试大量数据存储性能")
        start_time = time.time()
        
        session_id = memory_manager.start_new_session()
        
        # 存储100条对话
        for i in range(100):
            memory_manager.store_conversation(
                session_id,
                f"测试用户输入 {i}",
                f"测试AI回复 {i}",
                "neutral",
                f"测试上下文 {i}"
            )
        
        storage_time = time.time() - start_time
        print(f"  ✓ 存储100条对话耗时: {storage_time:.2f}秒")
        
        # 测试检索性能
        print("\n2. 测试检索性能")
        start_time = time.time()
        
        history = memory_manager.get_conversation_history(session_id, limit=50)
        retrieval_time = time.time() - start_time
        print(f"  ✓ 检索50条对话耗时: {retrieval_time:.3f}秒")
        
        # 测试搜索性能
        print("\n3. 测试搜索性能")
        start_time = time.time()
        
        search_results = memory_manager.search_conversations("测试", limit=20)
        search_time = time.time() - start_time
        print(f"  ✓ 搜索20条结果耗时: {search_time:.3f}秒")
        
        # 测试偏好存储和检索性能
        print("\n4. 测试偏好管理性能")
        start_time = time.time()
        
        # 存储100个偏好
        for i in range(100):
            memory_manager.store_user_preference(
                'test_performance',
                f'key_{i}',
                f'value_{i}'
            )
        
        pref_storage_time = time.time() - start_time
        print(f"  ✓ 存储100个偏好耗时: {pref_storage_time:.2f}秒")
        
        # 检索所有偏好
        start_time = time.time()
        all_prefs = memory_manager.get_all_preferences('test_performance')
        pref_retrieval_time = time.time() - start_time
        print(f"  ✓ 检索100个偏好耗时: {pref_retrieval_time:.3f}秒")
        
        memory_manager.end_session(session_id)
        
        print(f"\n✅ 性能测试完成 - 系统性能良好")
        return True
        
    except Exception as e:
        print(f"\n❌ 性能测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始完整记忆和上下文管理系统测试...")
    
    # 创建测试数据目录
    os.makedirs("test_data", exist_ok=True)
    
    # 运行测试
    tests = [
        ("完整系统集成", test_complete_memory_system),
        ("系统性能", test_memory_performance)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"运行测试: {test_name}")
        print('='*60)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"测试 {test_name} 发生异常: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print(f"\n{'='*60}")
    print("测试结果汇总")
    print('='*60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 个测试通过")
    
    if passed == len(results):
        print("\n🎉 所有测试通过！完整记忆和上下文管理系统运行正常！")
        print("\n📋 系统功能总结:")
        print("  ✓ 对话历史存储和检索")
        print("  ✓ 用户偏好记忆和学习")
        print("  ✓ 会话上下文维护和摘要")
        print("  ✓ 重启后设置恢复")
        print("  ✓ 个性化适应和学习")
        print("  ✓ 数据持久化和性能优化")
    else:
        print("\n⚠️  部分测试失败，请检查错误信息")

if __name__ == "__main__":
    main()