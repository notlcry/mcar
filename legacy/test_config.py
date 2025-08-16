#!/usr/bin/env python3
"""
配置系统测试脚本
"""

import os
import sys
sys.path.append('src')

def test_config_system():
    """测试配置系统"""
    print("=== AI桌宠配置系统测试 ===")
    print()
    
    # 设置测试环境变量
    os.environ['GEMINI_API_KEY'] = 'test_gemini_key_123456'
    os.environ['PICOVOICE_ACCESS_KEY'] = 'test_picovoice_key_789'
    
    try:
        # 导入配置管理器
        from config import ConfigManager
        
        # 创建配置管理器实例
        config_manager = ConfigManager('src/ai_pet_config.json')
        
        print("✅ 配置管理器初始化成功")
        print()
        
        # 测试AI配置
        ai_config = config_manager.get_ai_config()
        print("AI配置:")
        print(f"  API密钥: {ai_config.gemini_api_key}")
        print(f"  模型: {ai_config.model_name}")
        print(f"  温度: {ai_config.temperature}")
        print(f"  最大输出: {ai_config.max_output_tokens}")
        print()
        
        # 测试语音配置
        voice_config = config_manager.get_voice_config()
        print("语音配置:")
        print(f"  Picovoice密钥: {voice_config.picovoice_access_key}")
        print(f"  TTS语音: {voice_config.tts_voice}")
        print(f"  唤醒词: {voice_config.wake_words}")
        print(f"  识别语言: {voice_config.recognition_language}")
        print()
        
        # 测试个性配置
        personality_config = config_manager.get_personality_config()
        print("个性配置:")
        print(f"  名字: {personality_config.name}")
        print(f"  友好度: {personality_config.friendliness}")
        print(f"  活跃度: {personality_config.energy_level}")
        print(f"  好奇心: {personality_config.curiosity}")
        print(f"  顽皮度: {personality_config.playfulness}")
        print()
        
        # 测试系统配置
        system_config = config_manager.get_system_config()
        print("系统配置:")
        print(f"  最大对话历史: {system_config.max_conversation_history}")
        print(f"  对话超时: {system_config.conversation_timeout}")
        print(f"  响应超时: {system_config.response_timeout}")
        print(f"  日志级别: {system_config.log_level}")
        print()
        
        # 验证配置
        validation = config_manager.validate_config()
        print("配置验证:")
        for key, value in validation.items():
            status = "✅" if value else "❌"
            print(f"  {key}: {status}")
        print()
        
        # 测试状态
        status = config_manager.get_status()
        print("系统状态:")
        print(f"  配置文件: {status['config_file']}")
        print(f"  文件存在: {status['config_exists']}")
        print(f"  个性名字: {status['personality_name']}")
        print(f"  TTS语音: {status['tts_voice']}")
        print(f"  AI模型: {status['model_name']}")
        print()
        
        # 测试环境变量展开
        print("环境变量展开测试:")
        test_manager = ConfigManager('src/ai_pet_config.json')
        expanded_key = test_manager._expand_env_vars('${GEMINI_API_KEY}')
        print(f"  ${{GEMINI_API_KEY}} -> {expanded_key}")
        
        non_env_value = test_manager._expand_env_vars('normal_string')
        print(f"  normal_string -> {non_env_value}")
        print()
        
        print("🎉 所有测试通过！配置系统工作正常")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_config_system()