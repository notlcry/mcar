#!/usr/bin/python3
"""
AI对话管理器 - 集成Google Gemini API进行自然语言对话
支持语音输入、AI回复生成、情感分析和语音合成
"""

import google.generativeai as genai
import threading
import time
import queue
import logging
import json
import os
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import asyncio
from config import get_ai_config, get_personality_config, get_system_config
from emotion_engine import EmotionEngine, EmotionalState
from memory_manager import MemoryManager

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ConversationContext:
    """对话上下文数据模型"""
    session_id: str
    user_input: str
    ai_response: str
    emotion_detected: str
    timestamp: datetime
    conversation_history: List[Dict] = field(default_factory=list)
    personality_traits: Dict[str, float] = field(default_factory=dict)

class AIConversationManager:
    """AI对话管理器 - 处理完整的对话流程"""
    
    def __init__(self, robot_controller=None, expression_controller=None, safety_manager=None):
        """
        初始化AI对话管理器
        Args:
            robot_controller: LOBOROBOT实例
            expression_controller: 表情控制器实例
            safety_manager: 安全管理器实例
        """
        self.robot_controller = robot_controller
        self.expression_controller = expression_controller
        self.safety_manager = safety_manager
        
        # 加载配置
        self.ai_config = get_ai_config()
        self.personality_config = get_personality_config()
        self.system_config = get_system_config()
        
        # 初始化情感引擎
        self.emotion_engine = EmotionEngine()
        
        # 初始化记忆管理器
        self.memory_manager = MemoryManager(
            data_dir="data/memory",
            max_memory_entries=self.system_config.max_conversation_history * 10
        )
        
        # 从记忆管理器加载用户配置
        self.user_config = self.memory_manager.load_user_config()
        
        # 个性化设置（结合用户偏好）
        personality_name = self.user_config.get('personality', {}).get('name', self.personality_config.name)
        self.personality_prompt = self.ai_config.personality_prompt.replace(
            "快快", personality_name
        )
        
        # 根据用户偏好调整个性提示
        self._enhance_personality_prompt()
        
        # Gemini API配置
        self.api_key = self.ai_config.gemini_api_key
        
        # 如果配置中没有API密钥，尝试从环境变量加载
        if not self.api_key:
            self.api_key = os.getenv('GEMINI_API_KEY')
            if self.api_key:
                logger.info("从环境变量加载Gemini API密钥")
            else:
                logger.warning("未找到Gemini API密钥，请在配置中设置")
        
        # 初始化Gemini
        self.model = None
        self.chat_session = None
        self._initialize_gemini()
        
        # 对话状态管理
        self.is_conversation_active = False
        self.current_session_id = None
        self.conversation_history = []
        self.max_history_length = self.system_config.max_conversation_history
        
        # 线程安全的队列
        self.response_queue = queue.Queue()
        self.processing_lock = threading.Lock()
        
    def _initialize_gemini(self):
        """初始化Gemini API"""
        try:
            if self.api_key:
                genai.configure(api_key=self.api_key)
                
                # 配置生成参数
                generation_config = {
                    "temperature": self.ai_config.temperature,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": self.ai_config.max_output_tokens,
                }
                
                # 安全设置
                safety_settings = [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    }
                ]
                
                # 创建模型实例
                try:
                    # 尝试使用system_instruction参数（新版本API）
                    self.model = genai.GenerativeModel(
                        model_name=self.ai_config.model_name,
                        generation_config=generation_config,
                        safety_settings=safety_settings,
                        system_instruction=self.personality_prompt
                    )
                except TypeError:
                    # 如果不支持system_instruction，使用旧版本方式
                    logger.info("使用兼容模式创建Gemini模型")
                    self.model = genai.GenerativeModel(
                        model_name=self.ai_config.model_name,
                        generation_config=generation_config,
                        safety_settings=safety_settings
                    )
                    # 将个性提示保存，在对话时使用
                    self.system_prompt = self.personality_prompt
                
                logger.info(f"Gemini API初始化成功，使用模型: {self.ai_config.model_name}")
                logger.info(f"API密钥: {self.api_key[:20]}..." if self.api_key else "API密钥: 未设置")
                return True
            else:
                logger.error("Gemini API密钥未设置")
                return False
                
        except Exception as e:
            logger.error(f"Gemini API初始化失败: {e}")
            return False
    
    def start_conversation_mode(self):
        """启动对话模式"""
        if not self.model:
            logger.error("Gemini模型未初始化，无法启动对话模式")
            return False
            
        try:
            self.is_conversation_active = True
            
            # 通过记忆管理器开始新会话
            self.current_session_id = self.memory_manager.start_new_session()
            
            # 创建新的聊天会话，包含上下文信息
            chat_history = self._build_chat_history_from_memory()
            
            # 如果使用兼容模式，在历史记录开头添加系统提示
            if hasattr(self, 'system_prompt'):
                system_message = {
                    'role': 'user',
                    'parts': [self.system_prompt]
                }
                system_response = {
                    'role': 'model', 
                    'parts': ['我明白了，我会按照这个角色设定来回复。']
                }
                chat_history = [system_message, system_response] + chat_history
            
            self.chat_session = self.model.start_chat(history=chat_history)
            
            # 清空临时对话历史（使用记忆管理器）
            self.conversation_history = []
            
            logger.info(f"对话模式已启动，会话ID: {self.current_session_id}")
            
            # 如果有表情控制器，显示准备状态
            if self.expression_controller:
                self.expression_controller.show_listening_animation()
                
            return True
            
        except Exception as e:
            logger.error(f"启动对话模式失败: {e}")
            return False
    
    def stop_conversation_mode(self):
        """停止对话模式"""
        self.is_conversation_active = False
        
        # 结束当前会话
        if self.current_session_id:
            self.memory_manager.end_session(self.current_session_id)
        
        self.chat_session = None
        self.current_session_id = None
        
        # 如果有表情控制器，显示空闲状态
        if self.expression_controller:
            self.expression_controller.show_idle_animation()
            
        logger.info("对话模式已停止")
    
    def process_user_input(self, user_text):
        """
        处理用户输入文本
        Args:
            user_text: 用户输入的文本
        Returns:
            ConversationContext: 对话上下文对象
        """
        if not self.is_conversation_active or not self.chat_session:
            logger.warning("对话模式未激活")
            return None
            
        with self.processing_lock:
            try:
                # 显示思考动画
                if self.expression_controller:
                    self.expression_controller.show_thinking_animation()
                
                logger.info(f"处理用户输入: {user_text}")
                
                # 发送消息到Gemini - 带安全管理
                try:
                    response = self.chat_session.send_message(user_text)
                    ai_response = response.text.strip()
                    
                    # 通知安全管理器API调用成功
                    if self.safety_manager:
                        self.safety_manager.handle_api_success()
                    
                    logger.info(f"AI回复: {ai_response}")
                    
                except Exception as api_error:
                    logger.error(f"Gemini API调用失败: {api_error}")
                    
                    # 使用安全管理器处理API失败
                    if self.safety_manager:
                        ai_response = self.safety_manager.handle_api_failure("gemini_api_error", 0)
                        
                        # 如果在离线模式，尝试处理离线命令
                        if self.safety_manager.safety_state.offline_mode_active:
                            offline_response = self.safety_manager.process_offline_command(user_text)
                            if offline_response:
                                ai_response = offline_response
                    else:
                        ai_response = "抱歉，AI服务暂时不可用，请稍后再试。"
                
                # 使用情感引擎分析情感
                emotion_state = self.emotion_engine.analyze_response_emotion(
                    ai_response, 
                    context={'conversation_history': self.conversation_history}
                )
                
                # 更新情感引擎状态
                self.emotion_engine.update_emotional_state(emotion_state)
                
                # 存储对话到记忆管理器
                context_summary = self._generate_context_summary(user_text, ai_response)
                success = self.memory_manager.store_conversation(
                    self.current_session_id,
                    user_text,
                    ai_response,
                    emotion_state.primary_emotion.value,
                    context_summary
                )
                
                if not success:
                    logger.warning("对话存储失败")
                
                # 创建对话上下文
                context = ConversationContext(
                    session_id=self.current_session_id,
                    user_input=user_text,
                    ai_response=ai_response,
                    emotion_detected=emotion_state.primary_emotion.value,
                    timestamp=datetime.now()
                )
                
                # 更新临时对话历史（向后兼容）
                self._update_conversation_history(context)
                
                # 触发情感表达
                if self.expression_controller:
                    self.expression_controller.show_emotion(emotion_state.primary_emotion.value)
                
                # 更新个性上下文
                self.emotion_engine.update_personality_context(self.conversation_history)
                
                return context
                
            except Exception as e:
                logger.error(f"处理用户输入失败: {e}")
                
                # 返回错误响应
                error_context = ConversationContext(
                    session_id=self.current_session_id or "error",
                    user_input=user_text,
                    ai_response="抱歉，我现在有点困惑，请稍后再试试吧~",
                    emotion_detected="confused",
                    timestamp=datetime.now()
                )
                
                return error_context
    
    def get_current_emotion_state(self) -> EmotionalState:
        """获取当前情感状态"""
        return self.emotion_engine.get_current_emotional_state()
    
    def get_movement_emotion(self) -> str:
        """获取当前运动情感模式"""
        return self.emotion_engine.determine_movement_emotion()
    
    def _update_conversation_history(self, context):
        """更新对话历史"""
        self.conversation_history.append({
            'timestamp': context.timestamp.isoformat(),
            'user_input': context.user_input,
            'ai_response': context.ai_response,
            'emotion': context.emotion_detected
        })
        
        # 限制历史长度
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
    
    def get_conversation_history(self):
        """获取对话历史"""
        return self.conversation_history.copy()
    
    def clear_conversation_history(self):
        """清空对话历史"""
        self.conversation_history = []
        if self.chat_session:
            # 重新开始聊天会话
            self.chat_session = self.model.start_chat(history=[])
        logger.info("对话历史已清空")
    
    def is_active(self):
        """检查对话模式是否激活"""
        return self.is_conversation_active
    
    def get_status(self):
        """获取对话管理器状态"""
        emotion_status = self.emotion_engine.get_status()
        memory_status = self.memory_manager.get_status()
        
        return {
            'active': self.is_conversation_active,
            'session_id': self.current_session_id,
            'history_length': len(self.conversation_history),
            'model_available': self.model is not None,
            'api_configured': self.api_key is not None,
            'emotion_engine': emotion_status,
            'memory_manager': memory_status
        }
    
    def _enhance_personality_prompt(self):
        """根据用户偏好增强个性提示"""
        try:
            # 获取用户偏好
            interaction_prefs = self.memory_manager.get_all_preferences('interaction')
            behavior_prefs = self.memory_manager.get_all_preferences('behavior')
            personality_prefs = self.memory_manager.get_all_preferences('personality')
            
            # 构建个性化提示补充
            enhancements = []
            
            # 交互风格调整
            if interaction_prefs.get('verbosity') == 'low':
                enhancements.append("- 回复要简洁明了，不要太啰嗦")
            elif interaction_prefs.get('verbosity') == 'high':
                enhancements.append("- 可以详细一些回复，多聊聊相关话题")
            
            # 行为偏好调整
            if behavior_prefs.get('speed_preference') == 'fast':
                enhancements.append("- 用户喜欢快节奏，回复要活泼一些")
            elif behavior_prefs.get('speed_preference') == 'slow':
                enhancements.append("- 用户喜欢慢节奏，回复要温和一些")
            
            # 个性特征调整
            friendliness = personality_prefs.get('friendliness', 0.8)
            if friendliness > 0.8:
                enhancements.append("- 要特别友好和热情")
            elif friendliness < 0.5:
                enhancements.append("- 保持礼貌但不要过于热情")
            
            # 添加到个性提示
            if enhancements:
                enhancement_text = "\n\n用户偏好调整:\n" + "\n".join(enhancements)
                self.personality_prompt += enhancement_text
                
        except Exception as e:
            logger.error(f"增强个性提示失败: {e}")
    
    def _build_chat_history_from_memory(self) -> List[Dict]:
        """从记忆中构建聊天历史"""
        try:
            # 获取最近的对话历史
            recent_conversations = self.memory_manager.get_conversation_history(limit=10)
            
            # 转换为Gemini聊天历史格式
            chat_history = []
            for conv in recent_conversations[-5:]:  # 只使用最近5轮对话作为上下文
                chat_history.extend([
                    {
                        "role": "user",
                        "parts": [conv.user_input]
                    },
                    {
                        "role": "model", 
                        "parts": [conv.ai_response]
                    }
                ])
            
            return chat_history
            
        except Exception as e:
            logger.error(f"构建聊天历史失败: {e}")
            return []
    
    def _generate_context_summary(self, user_input: str, ai_response: str) -> str:
        """生成对话上下文摘要"""
        try:
            # 简单的关键词提取
            keywords = []
            
            # 从用户输入提取关键词
            user_words = user_input.split()
            for word in user_words:
                if len(word) > 2 and word not in ['我', '你', '的', '了', '是', '在', '有', '和', '就', '都']:
                    keywords.append(word)
            
            # 检测话题类型
            topic_indicators = {
                '音乐': ['音乐', '歌', '唱', '听'],
                '运动': ['运动', '跑', '跳', '球'],
                '游戏': ['游戏', '玩', '娱乐'],
                '学习': ['学', '知识', '了解', '教'],
                '情感': ['开心', '难过', '高兴', '伤心', '喜欢', '讨厌'],
                '动作': ['转', '动', '走', '停', '前进', '后退']
            }
            
            detected_topics = []
            for topic, indicators in topic_indicators.items():
                if any(indicator in user_input for indicator in indicators):
                    detected_topics.append(topic)
            
            # 构建摘要
            summary_parts = []
            if keywords:
                summary_parts.append(f"关键词: {', '.join(keywords[:3])}")
            if detected_topics:
                summary_parts.append(f"话题: {', '.join(detected_topics)}")
            
            return "; ".join(summary_parts) if summary_parts else "一般对话"
            
        except Exception as e:
            logger.error(f"生成上下文摘要失败: {e}")
            return "对话摘要生成失败"
    
    def get_conversation_context(self, query: str = None) -> Dict:
        """获取对话上下文信息"""
        try:
            context_info = {
                'current_session': None,
                'recent_conversations': [],
                'user_preferences': {},
                'session_summary': ""
            }
            
            # 当前会话信息
            if self.current_session_id:
                current_session = self.memory_manager.get_current_session()
                if current_session:
                    context_info['current_session'] = {
                        'session_id': current_session.session_id,
                        'start_time': current_session.start_time.isoformat(),
                        'topic_keywords': current_session.topic_keywords,
                        'user_mood': current_session.user_mood,
                        'conversation_summary': current_session.conversation_summary
                    }
            
            # 最近对话
            recent_convs = self.memory_manager.get_conversation_history(
                self.current_session_id, limit=10
            )
            context_info['recent_conversations'] = [
                {
                    'user_input': conv.user_input,
                    'ai_response': conv.ai_response,
                    'emotion': conv.emotion_detected,
                    'timestamp': conv.timestamp.isoformat()
                }
                for conv in recent_convs
            ]
            
            # 用户偏好
            context_info['user_preferences'] = {
                'personality': self.memory_manager.get_all_preferences('personality'),
                'behavior': self.memory_manager.get_all_preferences('behavior'),
                'interaction': self.memory_manager.get_all_preferences('interaction'),
                'interests': self.memory_manager.get_all_preferences('interests')
            }
            
            # 会话摘要
            if self.current_session_id:
                context_info['session_summary'] = self.memory_manager.generate_context_summary(
                    self.current_session_id
                )
            
            # 如果有查询，搜索相关对话
            if query:
                search_results = self.memory_manager.search_conversations(query, limit=5)
                context_info['search_results'] = [
                    {
                        'user_input': conv.user_input,
                        'ai_response': conv.ai_response,
                        'emotion': conv.emotion_detected,
                        'timestamp': conv.timestamp.isoformat(),
                        'importance_score': conv.importance_score
                    }
                    for conv in search_results
                ]
            
            return context_info
            
        except Exception as e:
            logger.error(f"获取对话上下文失败: {e}")
            return {}
    
    def update_user_preference(self, preference_type: str, key: str, value, confidence: float = 1.0):
        """更新用户偏好"""
        success = self.memory_manager.store_user_preference(
            preference_type, key, value, confidence
        )
        
        if success:
            # 重新加载用户配置
            self.user_config = self.memory_manager.load_user_config()
            # 重新增强个性提示
            self._enhance_personality_prompt()
            logger.info(f"用户偏好已更新: {preference_type}:{key} = {value}")
        
        return success

# 测试函数
def test_ai_conversation():
    """测试AI对话功能"""
    print("=== AI对话管理器测试 ===")
    
    # 创建对话管理器
    ai_manager = AIConversationManager()
    
    if not ai_manager.model:
        print("错误: Gemini API未正确配置")
        print("请设置环境变量: export GEMINI_API_KEY='your_api_key'")
        return
    
    # 启动对话模式
    if ai_manager.start_conversation_mode():
        print("对话模式启动成功")
        
        # 测试对话
        test_inputs = [
            "你好，快快！",
            "你能做什么动作？",
            "我今天很开心！",
            "你会转圈吗？"
        ]
        
        for user_input in test_inputs:
            print(f"\n用户: {user_input}")
            context = ai_manager.process_user_input(user_input)
            
            if context:
                print(f"AI回复: {context.ai_response}")
                print(f"检测情感: {context.emotion_detected}")
            else:
                print("处理失败")
            
            time.sleep(1)  # 避免API调用过快
        
        # 显示对话历史
        print("\n=== 对话历史 ===")
        history = ai_manager.get_conversation_history()
        for i, item in enumerate(history, 1):
            print(f"{i}. [{item['emotion']}] 用户: {item['user_input']}")
            print(f"   AI: {item['ai_response']}")
        
        # 停止对话模式
        ai_manager.stop_conversation_mode()
        print("\n对话模式已停止")
    else:
        print("对话模式启动失败")

if __name__ == "__main__":
    test_ai_conversation()