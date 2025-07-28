#!/usr/bin/python3
"""
记忆管理器 - 实现对话历史存储、用户偏好记忆和上下文管理
支持持久化存储、会话摘要和重启后恢复功能
"""

import json
import os
import sqlite3
import threading
import time
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
import hashlib

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ConversationEntry:
    """对话条目数据模型"""
    timestamp: datetime
    session_id: str
    user_input: str
    ai_response: str
    emotion_detected: str
    context_summary: str = ""
    importance_score: float = 0.5  # 重要性评分 0.0-1.0
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationEntry':
        """从字典创建实例"""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

@dataclass
class UserPreference:
    """用户偏好数据模型"""
    preference_type: str  # 偏好类型：personality, voice, behavior等
    key: str             # 偏好键
    value: Any           # 偏好值
    confidence: float = 1.0  # 置信度 0.0-1.0
    last_updated: datetime = field(default_factory=datetime.now)
    usage_count: int = 0  # 使用次数
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'preference_type': self.preference_type,
            'key': self.key,
            'value': self.value,
            'confidence': self.confidence,
            'last_updated': self.last_updated.isoformat(),
            'usage_count': self.usage_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UserPreference':
        """从字典创建实例"""
        data = data.copy()
        data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)

@dataclass
class SessionContext:
    """会话上下文数据模型"""
    session_id: str
    start_time: datetime
    last_activity: datetime
    topic_keywords: List[str] = field(default_factory=list)
    emotional_trend: List[str] = field(default_factory=list)
    user_mood: str = "neutral"
    conversation_summary: str = ""
    active: bool = True
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'topic_keywords': self.topic_keywords,
            'emotional_trend': self.emotional_trend,
            'user_mood': self.user_mood,
            'conversation_summary': self.conversation_summary,
            'active': self.active
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SessionContext':
        """从字典创建实例"""
        data = data.copy()
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        return cls(**data)

class MemoryManager:
    """记忆管理器 - 处理对话历史、用户偏好和上下文管理"""
    
    def __init__(self, data_dir: str = "data", max_memory_entries: int = 1000):
        """
        初始化记忆管理器
        Args:
            data_dir: 数据存储目录
            max_memory_entries: 最大内存条目数
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # 数据库文件路径
        self.db_path = self.data_dir / "memory.db"
        self.config_path = self.data_dir / "user_config.json"
        
        # 内存缓存
        self.conversation_cache: List[ConversationEntry] = []
        self.preference_cache: Dict[str, UserPreference] = {}
        self.session_cache: Dict[str, SessionContext] = {}
        self.current_session: Optional[SessionContext] = None
        
        # 配置参数
        self.max_memory_entries = max_memory_entries
        self.max_cache_size = 100  # 内存缓存最大条目数
        self.session_timeout = timedelta(minutes=30)  # 会话超时时间
        self.summary_threshold = 50  # 触发摘要的对话条目数
        
        # 线程锁
        self.db_lock = threading.Lock()
        self.cache_lock = threading.Lock()
        
        # 初始化数据库和加载数据
        self._initialize_database()
        self._load_user_preferences()
        self._load_recent_conversations()
        
        logger.info("记忆管理器初始化完成")
    
    def _initialize_database(self):
        """初始化SQLite数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建对话历史表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        user_input TEXT NOT NULL,
                        ai_response TEXT NOT NULL,
                        emotion_detected TEXT NOT NULL,
                        context_summary TEXT DEFAULT '',
                        importance_score REAL DEFAULT 0.5,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建用户偏好表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        preference_type TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        confidence REAL DEFAULT 1.0,
                        last_updated TEXT NOT NULL,
                        usage_count INTEGER DEFAULT 0,
                        UNIQUE(preference_type, key)
                    )
                ''')
                
                # 创建会话上下文表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS session_contexts (
                        session_id TEXT PRIMARY KEY,
                        start_time TEXT NOT NULL,
                        last_activity TEXT NOT NULL,
                        topic_keywords TEXT DEFAULT '[]',
                        emotional_trend TEXT DEFAULT '[]',
                        user_mood TEXT DEFAULT 'neutral',
                        conversation_summary TEXT DEFAULT '',
                        active INTEGER DEFAULT 1
                    )
                ''')
                
                # 创建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_preferences_type ON user_preferences(preference_type)')
                
                conn.commit()
                logger.info("数据库初始化完成")
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def _load_user_preferences(self):
        """从数据库加载用户偏好到缓存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM user_preferences')
                rows = cursor.fetchall()
                
                with self.cache_lock:
                    self.preference_cache.clear()
                    for row in rows:
                        pref = UserPreference(
                            preference_type=row[1],
                            key=row[2],
                            value=json.loads(row[3]),
                            confidence=row[4],
                            last_updated=datetime.fromisoformat(row[5]),
                            usage_count=row[6]
                        )
                        cache_key = f"{pref.preference_type}:{pref.key}"
                        self.preference_cache[cache_key] = pref
                
                logger.info(f"已加载 {len(self.preference_cache)} 个用户偏好")
                
        except Exception as e:
            logger.error(f"加载用户偏好失败: {e}")
    
    def _load_recent_conversations(self):
        """从数据库加载最近的对话到缓存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM conversations 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (self.max_cache_size,))
                rows = cursor.fetchall()
                
                with self.cache_lock:
                    self.conversation_cache.clear()
                    for row in rows:
                        entry = ConversationEntry(
                            timestamp=datetime.fromisoformat(row[1]),
                            session_id=row[2],
                            user_input=row[3],
                            ai_response=row[4],
                            emotion_detected=row[5],
                            context_summary=row[6] or "",
                            importance_score=row[7]
                        )
                        self.conversation_cache.append(entry)
                    
                    # 按时间顺序排序
                    self.conversation_cache.sort(key=lambda x: x.timestamp)
                
                logger.info(f"已加载 {len(self.conversation_cache)} 条最近对话")
                
        except Exception as e:
            logger.error(f"加载对话历史失败: {e}") 
   
    def start_new_session(self, session_id: Optional[str] = None) -> str:
        """
        开始新的对话会话
        Args:
            session_id: 可选的会话ID，如果不提供则自动生成
        Returns:
            str: 会话ID
        """
        if session_id is None:
            session_id = f"session_{int(time.time())}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
        
        # 结束当前会话
        if self.current_session:
            self.end_session(self.current_session.session_id)
        
        # 创建新会话
        now = datetime.now()
        session = SessionContext(
            session_id=session_id,
            start_time=now,
            last_activity=now
        )
        
        with self.cache_lock:
            self.session_cache[session_id] = session
            self.current_session = session
        
        # 保存到数据库
        self._save_session_to_db(session)
        
        logger.info(f"开始新会话: {session_id}")
        return session_id
    
    def end_session(self, session_id: str):
        """结束指定会话"""
        with self.cache_lock:
            if session_id in self.session_cache:
                session = self.session_cache[session_id]
                session.active = False
                session.last_activity = datetime.now()
                
                # 生成会话摘要
                if len(session.topic_keywords) > 0:
                    session.conversation_summary = self._generate_session_summary(session_id)
                
                # 更新数据库
                self._save_session_to_db(session)
                
                if self.current_session and self.current_session.session_id == session_id:
                    self.current_session = None
                
                logger.info(f"会话已结束: {session_id}")
    
    def store_conversation(self, session_id: str, user_input: str, ai_response: str, 
                          emotion_detected: str, context_summary: str = "") -> bool:
        """
        存储对话条目
        Args:
            session_id: 会话ID
            user_input: 用户输入
            ai_response: AI回复
            emotion_detected: 检测到的情感
            context_summary: 上下文摘要
        Returns:
            bool: 是否成功存储
        """
        try:
            # 创建对话条目
            entry = ConversationEntry(
                timestamp=datetime.now(),
                session_id=session_id,
                user_input=user_input,
                ai_response=ai_response,
                emotion_detected=emotion_detected,
                context_summary=context_summary,
                importance_score=self._calculate_importance_score(user_input, ai_response, emotion_detected)
            )
            
            # 添加到缓存
            with self.cache_lock:
                self.conversation_cache.append(entry)
                
                # 限制缓存大小
                if len(self.conversation_cache) > self.max_cache_size:
                    self.conversation_cache = self.conversation_cache[-self.max_cache_size:]
            
            # 保存到数据库
            self._save_conversation_to_db(entry)
            
            # 更新会话上下文
            self._update_session_context(session_id, user_input, ai_response, emotion_detected)
            
            # 提取用户偏好
            self._extract_user_preferences(user_input, ai_response)
            
            # 检查是否需要生成摘要
            self._check_and_generate_summary(session_id)
            
            logger.debug(f"对话已存储: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"存储对话失败: {e}")
            return False
    
    def get_conversation_history(self, session_id: Optional[str] = None, 
                               limit: int = 50) -> List[ConversationEntry]:
        """
        获取对话历史
        Args:
            session_id: 可选的会话ID，如果不提供则返回所有会话
            limit: 返回条目数限制
        Returns:
            List[ConversationEntry]: 对话历史列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if session_id:
                    cursor.execute('''
                        SELECT * FROM conversations 
                        WHERE session_id = ? 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (session_id, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM conversations 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (limit,))
                
                rows = cursor.fetchall()
                
                conversations = []
                for row in rows:
                    entry = ConversationEntry(
                        timestamp=datetime.fromisoformat(row[1]),
                        session_id=row[2],
                        user_input=row[3],
                        ai_response=row[4],
                        emotion_detected=row[5],
                        context_summary=row[6] or "",
                        importance_score=row[7]
                    )
                    conversations.append(entry)
                
                # 按时间顺序排序（最早的在前）
                conversations.reverse()
                return conversations
                
        except Exception as e:
            logger.error(f"获取对话历史失败: {e}")
            return []
    
    def search_conversations(self, query: str, limit: int = 20) -> List[ConversationEntry]:
        """
        搜索对话历史
        Args:
            query: 搜索查询
            limit: 返回条目数限制
        Returns:
            List[ConversationEntry]: 匹配的对话列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM conversations 
                    WHERE user_input LIKE ? OR ai_response LIKE ? OR context_summary LIKE ?
                    ORDER BY importance_score DESC, timestamp DESC
                    LIMIT ?
                ''', (f'%{query}%', f'%{query}%', f'%{query}%', limit))
                
                rows = cursor.fetchall()
                
                conversations = []
                for row in rows:
                    entry = ConversationEntry(
                        timestamp=datetime.fromisoformat(row[1]),
                        session_id=row[2],
                        user_input=row[3],
                        ai_response=row[4],
                        emotion_detected=row[5],
                        context_summary=row[6] or "",
                        importance_score=row[7]
                    )
                    conversations.append(entry)
                
                return conversations
                
        except Exception as e:
            logger.error(f"搜索对话失败: {e}")
            return []
    
    def store_user_preference(self, preference_type: str, key: str, value: Any, 
                            confidence: float = 1.0) -> bool:
        """
        存储用户偏好
        Args:
            preference_type: 偏好类型
            key: 偏好键
            value: 偏好值
            confidence: 置信度
        Returns:
            bool: 是否成功存储
        """
        try:
            cache_key = f"{preference_type}:{key}"
            
            # 更新或创建偏好
            with self.cache_lock:
                if cache_key in self.preference_cache:
                    pref = self.preference_cache[cache_key]
                    pref.value = value
                    pref.confidence = max(pref.confidence, confidence)
                    pref.last_updated = datetime.now()
                    pref.usage_count += 1
                else:
                    pref = UserPreference(
                        preference_type=preference_type,
                        key=key,
                        value=value,
                        confidence=confidence
                    )
                    self.preference_cache[cache_key] = pref
            
            # 保存到数据库
            self._save_preference_to_db(pref)
            
            logger.debug(f"用户偏好已存储: {preference_type}:{key} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"存储用户偏好失败: {e}")
            return False
    
    def get_user_preference(self, preference_type: str, key: str, default: Any = None) -> Any:
        """
        获取用户偏好
        Args:
            preference_type: 偏好类型
            key: 偏好键
            default: 默认值
        Returns:
            Any: 偏好值
        """
        cache_key = f"{preference_type}:{key}"
        
        with self.cache_lock:
            if cache_key in self.preference_cache:
                pref = self.preference_cache[cache_key]
                pref.usage_count += 1
                # 异步更新数据库中的使用次数
                threading.Thread(target=self._update_preference_usage, args=(pref,)).start()
                return pref.value
        
        return default
    
    def get_all_preferences(self, preference_type: Optional[str] = None) -> Dict[str, Any]:
        """
        获取所有用户偏好
        Args:
            preference_type: 可选的偏好类型过滤
        Returns:
            Dict[str, Any]: 偏好字典
        """
        preferences = {}
        
        with self.cache_lock:
            for cache_key, pref in self.preference_cache.items():
                if preference_type is None or pref.preference_type == preference_type:
                    preferences[pref.key] = pref.value
        
        return preferences
    
    def get_session_context(self, session_id: str) -> Optional[SessionContext]:
        """获取会话上下文"""
        with self.cache_lock:
            return self.session_cache.get(session_id)
    
    def get_current_session(self) -> Optional[SessionContext]:
        """获取当前会话上下文"""
        return self.current_session
    
    def generate_context_summary(self, session_id: str, max_length: int = 200) -> str:
        """
        生成会话上下文摘要
        Args:
            session_id: 会话ID
            max_length: 最大摘要长度
        Returns:
            str: 上下文摘要
        """
        try:
            conversations = self.get_conversation_history(session_id, limit=20)
            if not conversations:
                return ""
            
            # 提取关键信息
            topics = []
            emotions = []
            key_phrases = []
            
            for conv in conversations:
                # 提取话题关键词
                user_words = conv.user_input.split()
                ai_words = conv.ai_response.split()
                
                # 简单的关键词提取（可以后续优化为更复杂的NLP）
                for word in user_words + ai_words:
                    if len(word) > 2 and word not in ['我', '你', '的', '了', '是', '在', '有', '和', '就', '都']:
                        if word not in key_phrases:
                            key_phrases.append(word)
                
                emotions.append(conv.emotion_detected)
            
            # 统计最常见的情感
            emotion_counts = {}
            for emotion in emotions:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            dominant_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "neutral"
            
            # 生成摘要
            summary_parts = []
            
            if key_phrases:
                top_phrases = key_phrases[:5]  # 取前5个关键词
                summary_parts.append(f"主要话题: {', '.join(top_phrases)}")
            
            summary_parts.append(f"主导情感: {dominant_emotion}")
            summary_parts.append(f"对话轮次: {len(conversations)}")
            
            summary = "; ".join(summary_parts)
            
            # 限制长度
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."
            
            return summary
            
        except Exception as e:
            logger.error(f"生成上下文摘要失败: {e}")
            return ""
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """
        清理旧数据
        Args:
            days_to_keep: 保留天数
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 删除旧对话（保留重要对话）
                cursor.execute('''
                    DELETE FROM conversations 
                    WHERE timestamp < ? AND importance_score < 0.7
                ''', (cutoff_date.isoformat(),))
                
                # 删除旧会话
                cursor.execute('''
                    DELETE FROM session_contexts 
                    WHERE last_activity < ? AND active = 0
                ''', (cutoff_date.isoformat(),))
                
                conn.commit()
                
                deleted_conversations = cursor.rowcount
                logger.info(f"已清理 {deleted_conversations} 条旧对话记录")
                
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
    
    def export_user_data(self, output_path: str) -> bool:
        """
        导出用户数据
        Args:
            output_path: 输出文件路径
        Returns:
            bool: 是否成功导出
        """
        try:
            export_data = {
                'conversations': [],
                'preferences': [],
                'sessions': [],
                'export_time': datetime.now().isoformat()
            }
            
            # 导出对话历史
            conversations = self.get_conversation_history(limit=1000)
            export_data['conversations'] = [conv.to_dict() for conv in conversations]
            
            # 导出用户偏好
            with self.cache_lock:
                export_data['preferences'] = [pref.to_dict() for pref in self.preference_cache.values()]
            
            # 导出会话信息
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM session_contexts')
                rows = cursor.fetchall()
                
                for row in rows:
                    session_data = {
                        'session_id': row[0],
                        'start_time': row[1],
                        'last_activity': row[2],
                        'topic_keywords': json.loads(row[3]),
                        'emotional_trend': json.loads(row[4]),
                        'user_mood': row[5],
                        'conversation_summary': row[6],
                        'active': bool(row[7])
                    }
                    export_data['sessions'].append(session_data)
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"用户数据已导出到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出用户数据失败: {e}")
            return False
    
    def load_user_config(self) -> Dict[str, Any]:
        """加载用户配置"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info("用户配置已加载")
                return config
            else:
                # 返回默认配置
                default_config = {
                    'personality': {
                        'name': '快快',
                        'friendliness': 0.8,
                        'energy_level': 0.7,
                        'curiosity': 0.6,
                        'playfulness': 0.9
                    },
                    'voice_preferences': {
                        'voice': 'zh-CN-XiaoxiaoNeural',
                        'rate': '+0%',
                        'volume': '+0%'
                    },
                    'behavior_preferences': {
                        'movement_style': 'bouncy',
                        'response_style': 'friendly',
                        'interaction_frequency': 'normal'
                    }
                }
                self.save_user_config(default_config)
                return default_config
                
        except Exception as e:
            logger.error(f"加载用户配置失败: {e}")
            return {}
    
    def save_user_config(self, config: Dict[str, Any]) -> bool:
        """保存用户配置"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info("用户配置已保存")
            return True
        except Exception as e:
            logger.error(f"保存用户配置失败: {e}")
            return False 
   
    # 私有辅助方法
    
    def _save_conversation_to_db(self, entry: ConversationEntry):
        """保存对话条目到数据库"""
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO conversations 
                        (timestamp, session_id, user_input, ai_response, emotion_detected, 
                         context_summary, importance_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        entry.timestamp.isoformat(),
                        entry.session_id,
                        entry.user_input,
                        entry.ai_response,
                        entry.emotion_detected,
                        entry.context_summary,
                        entry.importance_score
                    ))
                    conn.commit()
        except Exception as e:
            logger.error(f"保存对话到数据库失败: {e}")
    
    def _save_preference_to_db(self, pref: UserPreference):
        """保存用户偏好到数据库"""
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_preferences 
                        (preference_type, key, value, confidence, last_updated, usage_count)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        pref.preference_type,
                        pref.key,
                        json.dumps(pref.value),
                        pref.confidence,
                        pref.last_updated.isoformat(),
                        pref.usage_count
                    ))
                    conn.commit()
        except Exception as e:
            logger.error(f"保存偏好到数据库失败: {e}")
    
    def _save_session_to_db(self, session: SessionContext):
        """保存会话上下文到数据库"""
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO session_contexts 
                        (session_id, start_time, last_activity, topic_keywords, 
                         emotional_trend, user_mood, conversation_summary, active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        session.session_id,
                        session.start_time.isoformat(),
                        session.last_activity.isoformat(),
                        json.dumps(session.topic_keywords),
                        json.dumps(session.emotional_trend),
                        session.user_mood,
                        session.conversation_summary,
                        int(session.active)
                    ))
                    conn.commit()
        except Exception as e:
            logger.error(f"保存会话到数据库失败: {e}")
    
    def _update_session_context(self, session_id: str, user_input: str, 
                              ai_response: str, emotion: str):
        """更新会话上下文"""
        with self.cache_lock:
            if session_id not in self.session_cache:
                return
            
            session = self.session_cache[session_id]
            session.last_activity = datetime.now()
            
            # 提取关键词
            words = (user_input + " " + ai_response).split()
            keywords = [word for word in words if len(word) > 2 and 
                       word not in ['我', '你', '的', '了', '是', '在', '有', '和', '就', '都']]
            
            # 更新话题关键词（保持最近的10个）
            for keyword in keywords[:3]:  # 每次最多添加3个关键词
                if keyword not in session.topic_keywords:
                    session.topic_keywords.append(keyword)
            
            if len(session.topic_keywords) > 10:
                session.topic_keywords = session.topic_keywords[-10:]
            
            # 更新情感趋势（保持最近的20个）
            session.emotional_trend.append(emotion)
            if len(session.emotional_trend) > 20:
                session.emotional_trend = session.emotional_trend[-20:]
            
            # 更新用户情绪（基于最近的情感趋势）
            recent_emotions = session.emotional_trend[-5:]  # 最近5次情感
            emotion_counts = {}
            for e in recent_emotions:
                emotion_counts[e] = emotion_counts.get(e, 0) + 1
            
            if emotion_counts:
                session.user_mood = max(emotion_counts, key=emotion_counts.get)
    
    def _extract_user_preferences(self, user_input: str, ai_response: str):
        """从对话中提取用户偏好"""
        user_input_lower = user_input.lower()
        
        # 检测个性偏好
        if any(word in user_input_lower for word in ['喜欢', '爱', '偏爱']):
            if '音乐' in user_input_lower:
                self.store_user_preference('interests', 'music', True, 0.7)
            elif '运动' in user_input_lower:
                self.store_user_preference('interests', 'sports', True, 0.7)
            elif '游戏' in user_input_lower:
                self.store_user_preference('interests', 'games', True, 0.7)
        
        # 检测行为偏好
        if any(word in user_input_lower for word in ['快点', '快一点', '慢点', '慢一点']):
            if '快' in user_input_lower:
                self.store_user_preference('behavior', 'speed_preference', 'fast', 0.6)
            else:
                self.store_user_preference('behavior', 'speed_preference', 'slow', 0.6)
        
        # 检测交互风格偏好
        if any(word in user_input_lower for word in ['安静', '话少', '不要说太多']):
            self.store_user_preference('interaction', 'verbosity', 'low', 0.8)
        elif any(word in user_input_lower for word in ['多说', '详细', '多聊']):
            self.store_user_preference('interaction', 'verbosity', 'high', 0.8)
    
    def _calculate_importance_score(self, user_input: str, ai_response: str, emotion: str) -> float:
        """计算对话重要性评分"""
        score = 0.5  # 基础分数
        
        # 情感强度影响
        emotion_weights = {
            'happy': 0.7,
            'excited': 0.8,
            'sad': 0.9,
            'angry': 0.9,
            'surprised': 0.8,
            'confused': 0.6,
            'thinking': 0.5,
            'neutral': 0.4
        }
        score += emotion_weights.get(emotion, 0.5) * 0.3
        
        # 对话长度影响
        total_length = len(user_input) + len(ai_response)
        if total_length > 100:
            score += 0.2
        elif total_length > 50:
            score += 0.1
        
        # 关键词影响
        important_keywords = ['记住', '重要', '喜欢', '不喜欢', '偏好', '设置', '配置']
        for keyword in important_keywords:
            if keyword in user_input:
                score += 0.2
                break
        
        return min(1.0, score)
    
    def _check_and_generate_summary(self, session_id: str):
        """检查是否需要生成摘要"""
        conversations = self.get_conversation_history(session_id)
        
        if len(conversations) >= self.summary_threshold:
            # 生成摘要并更新会话
            summary = self.generate_context_summary(session_id)
            
            with self.cache_lock:
                if session_id in self.session_cache:
                    self.session_cache[session_id].conversation_summary = summary
                    self._save_session_to_db(self.session_cache[session_id])
    
    def _generate_session_summary(self, session_id: str) -> str:
        """生成会话摘要"""
        return self.generate_context_summary(session_id)
    
    def _update_preference_usage(self, pref: UserPreference):
        """更新偏好使用次数"""
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE user_preferences 
                        SET usage_count = ? 
                        WHERE preference_type = ? AND key = ?
                    ''', (pref.usage_count, pref.preference_type, pref.key))
                    conn.commit()
        except Exception as e:
            logger.error(f"更新偏好使用次数失败: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取记忆管理器状态"""
        with self.cache_lock:
            return {
                'conversation_cache_size': len(self.conversation_cache),
                'preference_cache_size': len(self.preference_cache),
                'session_cache_size': len(self.session_cache),
                'current_session_id': self.current_session.session_id if self.current_session else None,
                'database_path': str(self.db_path),
                'config_path': str(self.config_path),
                'max_memory_entries': self.max_memory_entries,
                'session_timeout_minutes': self.session_timeout.total_seconds() / 60
            }

# 测试函数
def test_memory_manager():
    """测试记忆管理器功能"""
    print("=== 记忆管理器测试 ===")
    
    # 创建测试实例
    memory_manager = MemoryManager(data_dir="test_data")
    
    # 测试会话管理
    print("\n1. 测试会话管理")
    session_id = memory_manager.start_new_session()
    print(f"新会话ID: {session_id}")
    
    # 测试对话存储
    print("\n2. 测试对话存储")
    test_conversations = [
        ("你好，快快！", "你好！我是快快，很高兴见到你~", "happy"),
        ("你能做什么？", "我可以和你聊天，还能做各种动作呢！", "excited"),
        ("我喜欢音乐", "哇，我也喜欢音乐！你喜欢什么类型的音乐呢？", "happy"),
        ("转个圈给我看看", "好的！我来转个圈~", "excited")
    ]
    
    for user_input, ai_response, emotion in test_conversations:
        success = memory_manager.store_conversation(
            session_id, user_input, ai_response, emotion
        )
        print(f"存储对话: {'成功' if success else '失败'} - {user_input[:20]}...")
    
    # 测试对话历史检索
    print("\n3. 测试对话历史检索")
    history = memory_manager.get_conversation_history(session_id)
    print(f"检索到 {len(history)} 条对话记录")
    for i, conv in enumerate(history, 1):
        print(f"  {i}. [{conv.emotion_detected}] 用户: {conv.user_input}")
        print(f"      AI: {conv.ai_response}")
    
    # 测试用户偏好
    print("\n4. 测试用户偏好")
    memory_manager.store_user_preference('interests', 'music', True)
    memory_manager.store_user_preference('behavior', 'speed_preference', 'fast')
    memory_manager.store_user_preference('personality', 'friendliness', 0.9)
    
    music_pref = memory_manager.get_user_preference('interests', 'music')
    speed_pref = memory_manager.get_user_preference('behavior', 'speed_preference')
    print(f"音乐偏好: {music_pref}")
    print(f"速度偏好: {speed_pref}")
    
    all_prefs = memory_manager.get_all_preferences()
    print(f"所有偏好: {all_prefs}")
    
    # 测试搜索功能
    print("\n5. 测试搜索功能")
    search_results = memory_manager.search_conversations("音乐")
    print(f"搜索'音乐'结果: {len(search_results)} 条")
    for result in search_results:
        print(f"  - {result.user_input} -> {result.ai_response}")
    
    # 测试上下文摘要
    print("\n6. 测试上下文摘要")
    summary = memory_manager.generate_context_summary(session_id)
    print(f"会话摘要: {summary}")
    
    # 测试配置管理
    print("\n7. 测试配置管理")
    config = memory_manager.load_user_config()
    print(f"用户配置: {config}")
    
    # 结束会话
    memory_manager.end_session(session_id)
    print(f"\n会话已结束: {session_id}")
    
    # 显示状态
    print("\n=== 管理器状态 ===")
    status = memory_manager.get_status()
    for key, value in status.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    test_memory_manager()