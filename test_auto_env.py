#!/usr/bin/env python3
"""
测试自动环境变量加载功能
"""

import os
import sys
sys.path.append('src')

def test_auto_env_loading():
    """测试自动环境变量加载"""
    print("=== 自动环境变量加载测试 ===")
    print()
    
    # 清除现有环境变量（模拟干净环境）
    if 'GEMINI_API_KEY' in os.environ:
        del os.environ['GEMINI_API_KEY']
    if 'PICOVOICE_ACCESS_KEY' in os.environ:
        del os.environ['PICOVOICE_ACCESS_KEY']
    
    print("1. 清除现有环境变量")
    print(f"   GEMINI_API_KEY: {os.getenv('GEMINI_API_KEY', '未设置')}")
    print(f"   PICOVOICE_ACCESS_KEY: {os.getenv('PICOVOICE_ACCESS_KEY', '未设置')}")
    print()
    
    # 导入配置管理器（应该自动加载.ai_pet_env文件）
    print("2. 导入配置管理器（自动加载环境变量文件）")
    from config import ConfigManager
    
    config_manager = ConfigManager('src/ai_pet_config.json')
    
    print("3. 检查环境变量是否自动加载")
    print(f"   GEMINI_API_KEY: {os.getenv('GEMINI_API_KEY', '未设置')}")
    print(f"   PICOVOICE_ACCESS_KEY: {os.getenv('PICOVOICE_ACCESS_KEY', '未设置')}")
    print()
    
    # 检查配置是否正确加载
    ai_config = config_manager.get_ai_config()
    voice_config = config_manager.get_voice_config()
    
    print("4. 检查配置加载结果")
    print(f"   AI API密钥: {ai_config.gemini_api_key}")
    print(f"   语音API密钥: {voice_config.picovoice_access_key}")
    print()
    
    # 验证配置
    validation = config_manager.validate_config()
    print("5. 配置验证结果")
    for key, value in validation.items():
        status = "✅" if value else "❌"
        print(f"   {key}: {status}")
    print()
    
    if validation['gemini_api_key']:
        print("🎉 自动环境变量加载成功！")
        print("用户无需手动设置环境变量，系统会自动从.ai_pet_env文件加载")
    else:
        print("⚠️ 环境变量加载失败，请检查.ai_pet_env文件")
        print("提示：请确保.ai_pet_env文件存在且包含正确的API密钥")

if __name__ == "__main__":
    test_auto_env_loading()