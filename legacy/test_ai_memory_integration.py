#!/usr/bin/python3
"""
AI对话系统与记忆管理器集成演示
展示如何在实际AI对话中使用记忆和上下文管理功能
"""

import os
import sys
import time
import logging
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from memory_manager import MemoryManager

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIConversationWithMemory:
    """带记忆功能的AI对话管理器演示"""
    
    def __init__(self):
        """初始化带记忆功能的AI对话管理器"""
        self.memory_manager = MemoryManager(data_dir="data/ai_memory")
        self.current_session_id = None
        self.conversation_active = False
        
        # 加载用户配置
        self.user_config = self.memory_manager.load_user_config()
        
        print("🧠 AI对话记忆系统已初始化")
        print(f"📋 用户配置: {self.user_config}")
    
    def start_conversation(self):
        """开始对话会话"""
        self.current_session_id = self.memory_manager.start_new_session()
        self.conversation_active = True
        
        # 获取用户信息
        user_name = self.memory_manager.get_user_preference('user_info', 'name', '朋友')
        
        print(f"💬 对话开始 - 会话ID: {self.current_session_id}")
        print(f"👋 你好 {user_name}！我记得你的偏好，让我们继续聊天吧~")
        
        # 显示最近的对话上下文
        recent_conversations = self.memory_manager.get_conversation_history(limit=3)
        if recent_conversations:
            print("\n📚 最近的对话回顾:")
            for conv in recent_conversations[-3:]:
                print(f"  用户: {conv.user_input}")
                print(f"  AI: {conv.ai_response}")
                print(f"  情感: {conv.emotion_detected}")
                print()
    
    def process_user_input(self, user_input: str):
        """处理用户输入并生成回复"""
        if not self.conversation_active:
            return "请先开始对话会话"
        
        print(f"👤 用户: {user_input}")
        
        # 分析用户输入并生成AI回复（这里用简单规则模拟）
        ai_response, emotion = self._generate_ai_response(user_input)
        
        print(f"🤖 AI: {ai_response}")
        print(f"😊 情感: {emotion}")
        
        # 存储对话到记忆系统
        context_summary = self._generate_context_summary(user_input, ai_response)
        success = self.memory_manager.store_conversation(
            self.current_session_id,
            user_input,
            ai_response,
            emotion,
            context_summary
        )
        
        if success:
            print("💾 对话已保存到记忆系统")
        
        # 提取和存储用户偏好
        self._extract_and_store_preferences(user_input)
        
        return ai_response
    
    def _generate_ai_response(self, user_input: str):
        """生成AI回复（简化版本）"""
        user_input_lower = user_input.lower()
        
        # 获取用户偏好来个性化回复
        user_name = self.memory_manager.get_user_preference('user_info', 'name', '朋友')
        speed_pref = self.memory_manager.get_user_preference('behavior', 'speed_preference', 'normal')
        
        # 根据输入内容生成回复
        if any(word in user_input_lower for word in ['你好', 'hello', '嗨']):
            response = f"你好 {user_name}！很高兴又见到你~"
            emotion = "happy"
            
        elif any(word in user_input_lower for word in ['我叫', '我是', '名字']):
            # 提取姓名
            if '我叫' in user_input:
                name = user_input.split('我叫')[1].strip()
            elif '我是' in user_input:
                name = user_input.split('我是')[1].strip()
            else:
                name = user_name
            
            response = f"很高兴认识你，{name}！我会记住你的名字的~"
            emotion = "happy"
            
        elif any(word in user_input_lower for word in ['喜欢', '爱好', '兴趣']):
            response = "哇，告诉我你的兴趣爱好吧！我会记住的~"
            emotion = "excited"
            
        elif any(word in user_input_lower for word in ['音乐', '歌曲', '唱歌']):
            music_pref = self.memory_manager.get_user_preference('interests', 'music_genre')
            if music_pref:
                response = f"我记得你喜欢{music_pref}音乐！要不要聊聊音乐？"
            else:
                response = "音乐真是太棒了！你喜欢什么类型的音乐呢？"
            emotion = "excited"
            
        elif any(word in user_input_lower for word in ['转圈', '转个圈', '旋转']):
            if speed_pref == 'fast':
                response = "好的！我来转个快圈给你看~"
            else:
                response = "好的！我来优雅地转个圈~"
            emotion = "excited"
            
        elif any(word in user_input_lower for word in ['记得', '记住', '还记得']):
            # 搜索相关记忆
            search_query = user_input_lower.replace('记得', '').replace('记住', '').replace('还记得', '').strip()
            if search_query:
                search_results = self.memory_manager.search_conversations(search_query, limit=3)
                if search_results:
                    response = f"当然记得！我们之前聊过：{search_results[0].user_input}"
                else:
                    response = "让我想想...好像没有相关的记忆呢，要不你再提醒我一下？"
            else:
                response = "我的记忆系统很好哦！有什么想让我回忆的吗？"
            emotion = "thinking"
            
        elif any(word in user_input_lower for word in ['快点', '快一点', '活泼']):
            response = "好的！我会更有活力一些~"
            emotion = "excited"
            
        elif any(word in user_input_lower for word in ['慢点', '慢一点', '温柔']):
            response = "好的，我会温柔一些~"
            emotion = "happy"
            
        else:
            # 默认回复，尝试引用之前的对话
            recent_topics = self._get_recent_topics()
            if recent_topics:
                response = f"嗯嗯，我在想...我们之前聊过{recent_topics[0]}，还有什么想聊的吗？"
            else:
                response = "我在认真听呢！请继续说~"
            emotion = "neutral"
        
        return response, emotion
    
    def _generate_context_summary(self, user_input: str, ai_response: str):
        """生成对话上下文摘要"""
        # 简单的关键词提取
        keywords = []
        for word in user_input.split():
            if len(word) > 1 and word not in ['我', '你', '的', '了', '是', '在', '有', '和']:
                keywords.append(word)
        
        if keywords:
            return f"关键词: {', '.join(keywords[:3])}"
        else:
            return "一般对话"
    
    def _extract_and_store_preferences(self, user_input: str):
        """从用户输入中提取并存储偏好"""
        user_input_lower = user_input.lower()
        
        # 提取姓名
        if '我叫' in user_input:
            name = user_input.split('我叫')[1].strip()
            self.memory_manager.store_user_preference('user_info', 'name', name)
            print(f"📝 记住了你的名字: {name}")
        
        elif '我是' in user_input and '我是' != user_input.strip():
            name = user_input.split('我是')[1].strip()
            self.memory_manager.store_user_preference('user_info', 'name', name)
            print(f"📝 记住了你的名字: {name}")
        
        # 提取音乐偏好
        music_types = {
            '古典': 'classical',
            '流行': 'pop', 
            '摇滚': 'rock',
            '爵士': 'jazz',
            '民谣': 'folk'
        }
        
        for chinese, english in music_types.items():
            if chinese in user_input and '音乐' in user_input:
                self.memory_manager.store_user_preference('interests', 'music_genre', chinese)
                print(f"🎵 记住了你的音乐偏好: {chinese}")
                break
        
        # 提取速度偏好
        if any(word in user_input_lower for word in ['快点', '快一点', '活泼']):
            self.memory_manager.store_user_preference('behavior', 'speed_preference', 'fast')
            print("⚡ 记住了你喜欢快节奏")
        
        elif any(word in user_input_lower for word in ['慢点', '慢一点', '温柔']):
            self.memory_manager.store_user_preference('behavior', 'speed_preference', 'slow')
            print("🐌 记住了你喜欢慢节奏")
    
    def _get_recent_topics(self):
        """获取最近的话题"""
        if not self.current_session_id:
            return []
        
        session_context = self.memory_manager.get_session_context(self.current_session_id)
        if session_context and session_context.topic_keywords:
            return session_context.topic_keywords[-3:]  # 最近3个话题
        
        return []
    
    def end_conversation(self):
        """结束对话会话"""
        if self.current_session_id:
            # 生成会话摘要
            summary = self.memory_manager.generate_context_summary(self.current_session_id)
            print(f"📊 会话摘要: {summary}")
            
            # 结束会话
            self.memory_manager.end_session(self.current_session_id)
            print(f"👋 对话结束 - 会话ID: {self.current_session_id}")
            
            self.current_session_id = None
            self.conversation_active = False
    
    def show_memory_status(self):
        """显示记忆系统状态"""
        status = self.memory_manager.get_status()
        print(f"\n🧠 记忆系统状态:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        # 显示用户偏好
        all_prefs = self.memory_manager.get_all_preferences()
        if all_prefs:
            print(f"\n👤 用户偏好:")
            for key, value in all_prefs.items():
                print(f"  {key}: {value}")

def demo_conversation():
    """演示对话功能"""
    print("=== AI对话记忆系统演示 ===")
    
    # 创建AI对话系统
    ai_chat = AIConversationWithMemory()
    
    # 开始对话
    ai_chat.start_conversation()
    
    # 模拟对话序列
    demo_inputs = [
        "你好！",
        "我叫小王",
        "我喜欢听古典音乐",
        "转个圈给我看看",
        "太好了，快一点！",
        "你还记得我的名字吗？",
        "你记得我喜欢什么音乐吗？"
    ]
    
    print(f"\n🎭 开始演示对话...")
    for i, user_input in enumerate(demo_inputs, 1):
        print(f"\n--- 对话轮次 {i} ---")
        ai_chat.process_user_input(user_input)
        time.sleep(1)  # 模拟思考时间
    
    # 显示记忆状态
    ai_chat.show_memory_status()
    
    # 结束对话
    ai_chat.end_conversation()
    
    print(f"\n✅ 演示完成！")

def test_memory_persistence():
    """测试记忆持久化"""
    print(f"\n=== 记忆持久化测试 ===")
    
    # 第一次对话
    print(f"\n1. 第一次对话")
    ai_chat1 = AIConversationWithMemory()
    ai_chat1.start_conversation()
    ai_chat1.process_user_input("我叫测试用户")
    ai_chat1.process_user_input("我喜欢摇滚音乐")
    ai_chat1.end_conversation()
    
    # 第二次对话（模拟重启）
    print(f"\n2. 第二次对话（模拟重启）")
    ai_chat2 = AIConversationWithMemory()
    ai_chat2.start_conversation()
    ai_chat2.process_user_input("你还记得我吗？")
    ai_chat2.process_user_input("我喜欢什么音乐？")
    ai_chat2.end_conversation()
    
    print(f"\n✅ 持久化测试完成！")

def main():
    """主函数"""
    print("开始AI对话记忆系统测试...")
    
    # 创建数据目录
    os.makedirs("data", exist_ok=True)
    
    try:
        # 运行演示
        demo_conversation()
        
        # 测试持久化
        test_memory_persistence()
        
        print(f"\n🎉 所有测试完成！AI对话记忆系统运行正常！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        logger.error(f"测试失败: {e}", exc_info=True)

if __name__ == "__main__":
    main()