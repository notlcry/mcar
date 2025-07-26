#!/usr/bin/python3
"""
AI桌宠配置管理
管理API密钥、系统设置和个性化参数
"""

import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class AIConfig:
    """AI配置"""
    gemini_api_key: str = ""
    model_name: str = "gemini-1.5-flash"
    temperature: float = 0.7
    max_output_tokens: int = 200
    personality_prompt: str = """
    你是一个可爱的AI桌宠机器人，名字叫"圆滚滚"。你的特点：
    - 性格活泼友好，喜欢和用户互动
    - 说话风格可爱，偶尔会用一些萌萌的语气词
    - 能够表达不同的情感（开心、悲伤、兴奋、困惑等）
    - 会根据对话内容做出相应的动作反应
    - 记住你是一个实体机器人，可以移动和做动作
    
    请用简短、自然的中文回复，不要太长。在回复中可以提及你的动作或表情。
    """

@dataclass
class VoiceConfig:
    """语音配置"""
    picovoice_access_key: str = ""
    wake_words: List[str] = None
    tts_voice: str = "zh-CN-XiaoxiaoNeural"
    tts_rate: str = "+0%"
    tts_volume: str = "+0%"
    recognition_language: str = "zh-cn"
    use_whisper: bool = False
    
    def __post_init__(self):
        if self.wake_words is None:
            self.wake_words = ["喵喵小车", "小车", "机器人"]

@dataclass
class PersonalityConfig:
    """个性配置"""
    name: str = "圆滚滚"
    friendliness: float = 0.8
    energy_level: float = 0.7
    curiosity: float = 0.6
    playfulness: float = 0.9
    movement_style: str = "bouncy"

@dataclass
class SystemConfig:
    """系统配置"""
    max_conversation_history: int = 20
    conversation_timeout: int = 30
    response_timeout: int = 10
    audio_sample_rate: int = 16000
    log_level: str = "INFO"

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file="ai_pet_config.json"):
        self.config_file = config_file
        
        # 默认配置
        self.ai_config = AIConfig()
        self.voice_config = VoiceConfig()
        self.personality_config = PersonalityConfig()
        self.system_config = SystemConfig()
        
        # 从环境变量加载
        self._load_from_env()
        
        # 从配置文件加载
        self._load_from_file()
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        # AI配置
        if os.getenv('GEMINI_API_KEY'):
            self.ai_config.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        # 语音配置
        if os.getenv('PICOVOICE_ACCESS_KEY'):
            self.voice_config.picovoice_access_key = os.getenv('PICOVOICE_ACCESS_KEY')
        
        if os.getenv('TTS_VOICE'):
            self.voice_config.tts_voice = os.getenv('TTS_VOICE')
        
        # 系统配置
        if os.getenv('LOG_LEVEL'):
            self.system_config.log_level = os.getenv('LOG_LEVEL')
    
    def _expand_env_vars(self, value):
        """展开环境变量"""
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]  # 移除 ${ 和 }
            return os.getenv(env_var, value)  # 如果环境变量不存在，返回原值
        return value
    
    def _load_from_file(self):
        """从配置文件加载"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 更新配置
                if 'ai' in config_data:
                    for key, value in config_data['ai'].items():
                        if hasattr(self.ai_config, key):
                            # 展开环境变量
                            expanded_value = self._expand_env_vars(value)
                            setattr(self.ai_config, key, expanded_value)
                
                if 'voice' in config_data:
                    for key, value in config_data['voice'].items():
                        if hasattr(self.voice_config, key):
                            # 展开环境变量
                            expanded_value = self._expand_env_vars(value)
                            setattr(self.voice_config, key, expanded_value)
                
                if 'personality' in config_data:
                    for key, value in config_data['personality'].items():
                        if hasattr(self.personality_config, key):
                            setattr(self.personality_config, key, value)
                
                if 'system' in config_data:
                    for key, value in config_data['system'].items():
                        if hasattr(self.system_config, key):
                            setattr(self.system_config, key, value)
                
                logger.info(f"配置已从 {self.config_file} 加载")
            
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}")
    
    def save_to_file(self):
        """保存配置到文件"""
        try:
            config_data = {
                'ai': asdict(self.ai_config),
                'voice': asdict(self.voice_config),
                'personality': asdict(self.personality_config),
                'system': asdict(self.system_config)
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置已保存到 {self.config_file}")
            
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def get_ai_config(self) -> AIConfig:
        """获取AI配置"""
        return self.ai_config
    
    def get_voice_config(self) -> VoiceConfig:
        """获取语音配置"""
        return self.voice_config
    
    def get_personality_config(self) -> PersonalityConfig:
        """获取个性配置"""
        return self.personality_config
    
    def get_system_config(self) -> SystemConfig:
        """获取系统配置"""
        return self.system_config
    
    def update_personality(self, **kwargs):
        """更新个性配置"""
        for key, value in kwargs.items():
            if hasattr(self.personality_config, key):
                setattr(self.personality_config, key, value)
        
        self.save_to_file()
        logger.info("个性配置已更新")
    
    def update_voice_settings(self, **kwargs):
        """更新语音设置"""
        for key, value in kwargs.items():
            if hasattr(self.voice_config, key):
                setattr(self.voice_config, key, value)
        
        self.save_to_file()
        logger.info("语音设置已更新")
    
    def validate_config(self) -> Dict[str, bool]:
        """验证配置完整性"""
        validation_results = {
            'gemini_api_key': bool(self.ai_config.gemini_api_key),
            'picovoice_access_key': bool(self.voice_config.picovoice_access_key),
            'personality_complete': all([
                self.personality_config.name,
                0 <= self.personality_config.friendliness <= 1,
                0 <= self.personality_config.energy_level <= 1
            ])
        }
        
        return validation_results
    
    def get_status(self) -> Dict:
        """获取配置状态"""
        validation = self.validate_config()
        
        return {
            'config_file': self.config_file,
            'config_exists': os.path.exists(self.config_file),
            'validation': validation,
            'personality_name': self.personality_config.name,
            'tts_voice': self.voice_config.tts_voice,
            'model_name': self.ai_config.model_name
        }

# 全局配置实例（延迟初始化）
_config_manager = None

def _get_config_manager():
    """获取配置管理器实例（延迟初始化）"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

# 全局配置管理器实例
config_manager = _get_config_manager()

# 便捷访问函数
def get_ai_config() -> AIConfig:
    return _get_config_manager().get_ai_config()

def get_voice_config() -> VoiceConfig:
    return _get_config_manager().get_voice_config()

def get_personality_config() -> PersonalityConfig:
    return _get_config_manager().get_personality_config()

def get_system_config() -> SystemConfig:
    return _get_config_manager().get_system_config()

# 测试函数
def test_config():
    """测试配置管理"""
    print("=== 配置管理测试 ===")
    
    # 显示当前配置
    status = config_manager.get_status()
    print(f"配置状态: {status}")
    
    # 验证配置
    validation = config_manager.validate_config()
    print(f"配置验证: {validation}")
    
    # 测试更新个性
    config_manager.update_personality(
        name="测试圆滚滚",
        friendliness=0.9
    )
    
    print(f"更新后的个性: {config_manager.get_personality_config()}")
    
    # 保存配置
    config_manager.save_to_file()
    print("配置已保存")

if __name__ == "__main__":
    test_config()