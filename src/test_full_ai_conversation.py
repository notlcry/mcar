#!/usr/bin/python3
"""
测试完整的AI对话功能（包括情感分析）
"""

import sys
import os
import time

# 确保在正确的目录下运行
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.append(script_dir)

from ai_conversation import AIConversationManager

def test_full_conversation():
    """测试完整的AI对话功能"""
    print("=== 测试完整AI对话功能 ===")
    
    # 创建AI对话管理器
    ai_manager = AIConversationManager()
    
    # 检查API配置
    status = ai_manager.get_status()
    if not status['api_configured']:
        print("❌ API未配置，无法进行对话测试")
        return False
    
    if not status['model_available']:
        print("❌ 模型不可用，无法进行对话测试")
        return False
    
    print("✅ API配置正常，开始对话测试")
    
    # 启动对话模式
    if not ai_manager.start_conversation_mode():
        print("❌ 启动对话模式失败")
        return False
    
    print("✅ 对话模式启动成功")
    
    # 测试对话
    test_inputs = [
        "你好，圆滚滚！",
        "你今天心情怎么样？",
        "你能做什么有趣的动作吗？",
        "我今天很开心！",
        "谢谢你陪我聊天"
    ]
    
    print("\n开始对话测试:")
    print("=" * 50)
    
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n【轮次 {i}】")
        print(f"用户: {user_input}")
        
        try:
            # 处理用户输入
            context = ai_manager.process_user_input(user_input)
            
            if context:
                print(f"AI回复: {context.ai_response}")
                print(f"检测情感: {context.emotion_detected}")
                
                # 获取详细的情感状态
                emotion_state = ai_manager.get_current_emotion_state()
                print(f"情感强度: {emotion_state.intensity:.2f}")
                print(f"运动模式: {emotion_state.movement_pattern}")
                
                # 获取推荐运动
                movement = ai_manager.get_movement_emotion()
                print(f"推荐运动: {movement}")
                
                if emotion_state.triggers:
                    print(f"情感触发词: {emotion_state.triggers}")
                
            else:
                print("❌ 处理失败")
            
            # 短暂延迟，避免API调用过快
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ 处理异常: {e}")
            break
    
    # 显示对话历史
    print(f"\n{'='*50}")
    print("=== 对话历史 ===")
    history = ai_manager.get_conversation_history()
    for i, item in enumerate(history, 1):
        print(f"{i}. [{item['emotion']}] 用户: {item['user_input']}")
        print(f"   AI: {item['ai_response']}")
    
    # 显示情感历史
    print(f"\n=== 情感历史 ===")
    emotion_history = ai_manager.emotion_engine.get_emotion_history()
    for i, state in enumerate(emotion_history, 1):
        print(f"{i}. {state.primary_emotion.value} (强度: {state.intensity:.2f}) - {state.movement_pattern}")
    
    # 显示最终状态
    print(f"\n=== 最终状态 ===")
    final_status = ai_manager.get_status()
    print(f"对话轮次: {final_status['history_length']}")
    print(f"当前情感: {final_status['emotion_engine']['current_emotion']}")
    print(f"情感强度: {final_status['emotion_engine']['intensity']:.2f}")
    print(f"衰减率: {final_status['emotion_engine']['decay_rate']}")
    
    # 停止对话模式
    ai_manager.stop_conversation_mode()
    print("\n✅ 对话模式已停止")
    
    return True

def test_emotion_analysis_only():
    """仅测试情感分析功能（不需要API调用）"""
    print("\n=== 测试情感分析功能 ===")
    
    ai_manager = AIConversationManager()
    
    # 测试不同类型的AI回复
    test_responses = [
        "哈哈，很高兴见到你！我感到很开心！",
        "哇！这个问题太有趣了！我超级兴奋！",
        "嗯...让我仔细想想这个复杂的问题...",
        "什么？我不太理解你的意思，有点困惑",
        "今天天气不错，我的心情还可以",
        "太棒了！我们一起做个有趣的动作吧！"
    ]
    
    print("测试各种AI回复的情感分析:")
    
    for i, response in enumerate(test_responses, 1):
        print(f"\n{i}. AI回复: {response}")
        
        # 直接使用情感引擎分析
        emotion_state = ai_manager.emotion_engine.analyze_response_emotion(response)
        ai_manager.emotion_engine.update_emotional_state(emotion_state)
        
        print(f"   检测情感: {emotion_state.primary_emotion.value}")
        print(f"   情感强度: {emotion_state.intensity:.2f}")
        print(f"   运动模式: {emotion_state.movement_pattern}")
        print(f"   触发词: {emotion_state.triggers}")
        
        # 获取推荐运动
        movement = ai_manager.get_movement_emotion()
        print(f"   推荐运动: {movement}")
    
    return True

def main():
    """主函数"""
    print("AI对话系统完整测试")
    print("=" * 60)
    
    # 首先测试情感分析（不需要API）
    emotion_success = test_emotion_analysis_only()
    
    # 然后测试完整对话（需要API）
    conversation_success = test_full_conversation()
    
    print(f"\n{'='*60}")
    print("测试结果:")
    print(f"情感分析测试: {'✅ 通过' if emotion_success else '❌ 失败'}")
    print(f"完整对话测试: {'✅ 通过' if conversation_success else '❌ 失败'}")
    
    if emotion_success and conversation_success:
        print("\n🎉 所有测试通过！AI对话系统工作正常。")
        return True
    else:
        print("\n⚠ 部分测试失败，请检查配置和网络连接。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)