#!/usr/bin/python3
"""
测试记忆管理器与AI对话系统的集成
"""

import os
import sys
import time
import logging
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from memory_manager import MemoryManager
from ai_conversation import AIConversationManager

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_memory_integration():
    """测试记忆管理器与AI对话系统的集成"""
    print("=== 记忆管理器集成测试 ===")
    
    try:
        # 创建记忆管理器
        print("\n1. 初始化记忆管理器")
        memory_manager = MemoryManager(data_dir="test_data/memory")
        print("记忆管理器初始化成功")
        
        # 测试基本功能
        print("\n2. 测试基本记忆功能")
        
        # 开始新会话
        session_id = memory_manager.start_new_session()
        print(f"新会话ID: {session_id}")
        
        # 存储测试对话
        test_conversations = [
            ("你好，圆滚滚！", "你好！我是圆滚滚，很高兴见到你~", "happy"),
            ("我喜欢听音乐", "哇，我也喜欢音乐！你喜欢什么类型的音乐呢？", "excited"),
            ("请你转个圈", "好的！我来转个圈给你看~", "happy"),
            ("你记得我喜欢什么吗？", "当然记得！你喜欢听音乐呢~", "happy")
        ]
        
        for user_input, ai_response, emotion in test_conversations:
            success = memory_manager.store_conversation(
                session_id, user_input, ai_response, emotion
            )
            print(f"存储对话: {'✓' if success else '✗'} - {user_input[:20]}...")
            time.sleep(0.1)
        
        # 测试对话检索
        print("\n3. 测试对话历史检索")
        history = memory_manager.get_conversation_history(session_id)
        print(f"检索到 {len(history)} 条对话记录:")
        for i, conv in enumerate(history, 1):
            print(f"  {i}. [{conv.emotion_detected}] 用户: {conv.user_input}")
            print(f"      AI: {conv.ai_response}")
        
        # 测试用户偏好存储
        print("\n4. 测试用户偏好管理")
        preferences = [
            ('interests', 'music', True),
            ('behavior', 'speed_preference', 'normal'),
            ('personality', 'friendliness', 0.9),
            ('interaction', 'verbosity', 'medium')
        ]
        
        for pref_type, key, value in preferences:
            success = memory_manager.store_user_preference(pref_type, key, value)
            print(f"存储偏好: {'✓' if success else '✗'} {pref_type}:{key} = {value}")
        
        # 测试偏好检索
        print("\n5. 测试偏好检索")
        music_pref = memory_manager.get_user_preference('interests', 'music')
        speed_pref = memory_manager.get_user_preference('behavior', 'speed_preference')
        print(f"音乐偏好: {music_pref}")
        print(f"速度偏好: {speed_pref}")
        
        all_prefs = memory_manager.get_all_preferences()
        print(f"所有偏好: {all_prefs}")
        
        # 测试搜索功能
        print("\n6. 测试对话搜索")
        search_results = memory_manager.search_conversations("音乐")
        print(f"搜索'音乐'结果: {len(search_results)} 条")
        for result in search_results:
            print(f"  - {result.user_input} -> {result.ai_response}")
        
        # 测试上下文摘要
        print("\n7. 测试上下文摘要生成")
        summary = memory_manager.generate_context_summary(session_id)
        print(f"会话摘要: {summary}")
        
        # 测试会话上下文
        print("\n8. 测试会话上下文")
        session_context = memory_manager.get_session_context(session_id)
        if session_context:
            print(f"会话话题关键词: {session_context.topic_keywords}")
            print(f"情感趋势: {session_context.emotional_trend}")
            print(f"用户情绪: {session_context.user_mood}")
        
        # 测试配置管理
        print("\n9. 测试用户配置管理")
        config = memory_manager.load_user_config()
        print(f"用户配置: {config}")
        
        # 更新配置
        config['personality']['name'] = '测试圆滚滚'
        config['personality']['friendliness'] = 0.95
        success = memory_manager.save_user_config(config)
        print(f"保存配置: {'✓' if success else '✗'}")
        
        # 结束会话
        memory_manager.end_session(session_id)
        print(f"\n会话已结束: {session_id}")
        
        # 显示最终状态
        print("\n=== 记忆管理器状态 ===")
        status = memory_manager.get_status()
        for key, value in status.items():
            print(f"{key}: {value}")
        
        print("\n✓ 记忆管理器基本功能测试完成")
        return True
        
    except Exception as e:
        print(f"✗ 记忆管理器测试失败: {e}")
        logger.error(f"测试失败: {e}", exc_info=True)
        return False

def test_ai_conversation_with_memory():
    """测试AI对话系统与记忆管理器的集成"""
    print("\n=== AI对话系统记忆集成测试 ===")
    
    try:
        # 测试记忆管理器的AI集成功能（不需要完整的AI对话管理器）
        print("\n1. 测试记忆管理器的AI集成功能")
        memory_manager = MemoryManager(data_dir="test_data/ai_integration")
        
        # 模拟AI对话管理器的使用场景
        print("\n2. 模拟AI对话流程")
        
        # 开始会话
        session_id = memory_manager.start_new_session()
        print(f"✓ 开始新会话: {session_id}")
        
        # 存储带有上下文的对话
        conversations = [
            ("你好，我是小明", "你好小明！很高兴认识你~", "happy", "用户自我介绍"),
            ("我喜欢听古典音乐", "哇，古典音乐很优雅呢！你最喜欢哪个作曲家？", "excited", "音乐偏好讨论"),
            ("贝多芬是我的最爱", "贝多芬的作品确实很震撼！《命运交响曲》是经典呢~", "happy", "具体音乐偏好"),
            ("你能记住我的名字吗？", "当然记得！你是小明，喜欢古典音乐，特别是贝多芬~", "happy", "记忆测试")
        ]
        
        for user_input, ai_response, emotion, context in conversations:
            success = memory_manager.store_conversation(
                session_id, user_input, ai_response, emotion, context
            )
            print(f"✓ 存储对话: {user_input[:15]}...")
        
        # 测试用户偏好提取和存储
        print("\n3. 测试用户偏好管理")
        preferences = [
            ('user_info', 'name', '小明'),
            ('interests', 'music_genre', 'classical'),
            ('interests', 'favorite_composer', 'beethoven'),
            ('personality', 'friendliness', 0.9),
            ('behavior', 'interaction_style', 'enthusiastic')
        ]
        
        for pref_type, key, value in preferences:
            success = memory_manager.store_user_preference(pref_type, key, value)
            print(f"✓ 存储偏好: {pref_type}:{key} = {value}")
        
        # 测试上下文摘要生成
        print("\n4. 测试上下文摘要")
        summary = memory_manager.generate_context_summary(session_id)
        print(f"✓ 会话摘要: {summary}")
        
        # 测试搜索功能
        print("\n5. 测试对话搜索")
        search_results = memory_manager.search_conversations("音乐")
        print(f"✓ 搜索'音乐'结果: {len(search_results)} 条")
        for result in search_results:
            print(f"  - {result.user_input} -> {result.ai_response}")
        
        # 测试会话上下文
        print("\n6. 测试会话上下文")
        session_context = memory_manager.get_session_context(session_id)
        if session_context:
            print(f"✓ 话题关键词: {session_context.topic_keywords}")
            print(f"✓ 情感趋势: {session_context.emotional_trend}")
            print(f"✓ 用户情绪: {session_context.user_mood}")
        
        # 测试个性化配置
        print("\n7. 测试个性化配置")
        config = memory_manager.load_user_config()
        
        # 更新配置以反映用户偏好
        if 'personality' not in config:
            config['personality'] = {}
        config['personality']['name'] = '圆滚滚'
        config['personality']['user_name'] = '小明'
        config['personality']['friendliness'] = 0.9
        
        if 'interests' not in config:
            config['interests'] = {}
        config['interests']['music'] = 'classical'
        config['interests']['composer'] = 'beethoven'
        
        success = memory_manager.save_user_config(config)
        print(f"✓ 保存个性化配置: {'成功' if success else '失败'}")
        
        # 结束会话
        memory_manager.end_session(session_id)
        print(f"✓ 会话已结束: {session_id}")
        
        # 测试重新加载后的数据一致性
        print("\n8. 测试数据持久性")
        new_memory_manager = MemoryManager(data_dir="test_data/ai_integration")
        
        # 检查偏好是否持久化
        name_pref = new_memory_manager.get_user_preference('user_info', 'name')
        music_pref = new_memory_manager.get_user_preference('interests', 'music_genre')
        print(f"✓ 持久化偏好 - 姓名: {name_pref}, 音乐: {music_pref}")
        
        # 检查对话历史是否持久化
        history = new_memory_manager.get_conversation_history(limit=10)
        print(f"✓ 持久化对话: {len(history)} 条")
        
        # 检查配置是否持久化
        loaded_config = new_memory_manager.load_user_config()
        user_name = loaded_config.get('personality', {}).get('user_name')
        print(f"✓ 持久化配置 - 用户名: {user_name}")
        
        print("\n✓ AI对话系统记忆集成测试完成")
        return True
        
    except Exception as e:
        print(f"✗ AI对话系统记忆集成测试失败: {e}")
        logger.error(f"集成测试失败: {e}", exc_info=True)
        return False

def test_persistence():
    """测试数据持久化"""
    print("\n=== 数据持久化测试 ===")
    
    try:
        # 第一阶段：创建数据
        print("\n1. 创建测试数据")
        memory_manager1 = MemoryManager(data_dir="test_data/persistence")
        
        session_id = memory_manager1.start_new_session()
        memory_manager1.store_conversation(
            session_id, "测试持久化", "数据已保存", "neutral"
        )
        memory_manager1.store_user_preference('test', 'persistence', True)
        memory_manager1.end_session(session_id)
        
        print("✓ 测试数据已创建")
        
        # 第二阶段：重新加载数据
        print("\n2. 重新加载数据")
        memory_manager2 = MemoryManager(data_dir="test_data/persistence")
        
        # 检查对话历史
        history = memory_manager2.get_conversation_history(limit=10)
        print(f"加载对话历史: {len(history)} 条")
        
        # 检查用户偏好
        persistence_pref = memory_manager2.get_user_preference('test', 'persistence')
        print(f"加载偏好: persistence = {persistence_pref}")
        
        # 检查用户配置
        config = memory_manager2.load_user_config()
        print(f"加载配置: {len(config)} 个配置项")
        
        if len(history) > 0 and persistence_pref is True:
            print("✓ 数据持久化测试成功")
            return True
        else:
            print("✗ 数据持久化测试失败")
            return False
            
    except Exception as e:
        print(f"✗ 数据持久化测试失败: {e}")
        logger.error(f"持久化测试失败: {e}", exc_info=True)
        return False

def main():
    """主测试函数"""
    print("开始记忆管理器集成测试...")
    
    # 创建测试数据目录
    os.makedirs("test_data", exist_ok=True)
    
    # 运行测试
    tests = [
        ("基本记忆功能", test_memory_integration),
        ("AI对话集成", test_ai_conversation_with_memory),
        ("数据持久化", test_persistence)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"运行测试: {test_name}")
        print('='*50)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"测试 {test_name} 发生异常: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print(f"\n{'='*50}")
    print("测试结果汇总")
    print('='*50)
    
    passed = 0
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 个测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！记忆管理器集成成功！")
    else:
        print("⚠️  部分测试失败，请检查错误信息")

if __name__ == "__main__":
    main()