#!/usr/bin/python3
"""
调试配置加载问题
"""

import sys
import os
import json

# 添加src目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import ConfigManager, get_ai_config

def debug_config_loading():
    """调试配置加载过程"""
    print("=== 调试配置加载 ===")
    
    # 检查当前工作目录
    print(f"当前工作目录: {os.getcwd()}")
    
    # 检查配置文件路径
    config_file = "ai_pet_config.json"
    full_path = os.path.join(os.getcwd(), "src", config_file)
    
    print(f"查找配置文件: {config_file}")
    print(f"完整路径: {full_path}")
    print(f"文件存在: {os.path.exists(config_file)}")
    print(f"完整路径存在: {os.path.exists(full_path)}")
    
    # 尝试直接读取配置文件
    if os.path.exists(config_file):
        print("\n=== 直接读取配置文件 ===")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            print("配置文件读取成功")
            if 'ai' in config_data and 'gemini_api_key' in config_data['ai']:
                api_key = config_data['ai']['gemini_api_key']
                if api_key:
                    masked_key = api_key[:8] + "..." + api_key[-4:]
                    print(f"API Key (从文件): {masked_key}")
                else:
                    print("API Key 为空")
            else:
                print("配置文件中没有找到 ai.gemini_api_key")
        except Exception as e:
            print(f"读取配置文件失败: {e}")
    
    # 测试ConfigManager
    print("\n=== 测试ConfigManager ===")
    try:
        # 切换到src目录
        original_cwd = os.getcwd()
        src_dir = os.path.join(original_cwd, "src")
        if os.path.exists(src_dir):
            os.chdir(src_dir)
            print(f"切换到目录: {os.getcwd()}")
        
        config_manager = ConfigManager()
        ai_config = config_manager.get_ai_config()
        
        print(f"ConfigManager API Key: {'已设置' if ai_config.gemini_api_key else '未设置'}")
        if ai_config.gemini_api_key:
            masked_key = ai_config.gemini_api_key[:8] + "..." + ai_config.gemini_api_key[-4:]
            print(f"API Key (ConfigManager): {masked_key}")
        
        # 恢复原目录
        os.chdir(original_cwd)
        
    except Exception as e:
        print(f"ConfigManager 测试失败: {e}")
        # 恢复原目录
        os.chdir(original_cwd)
    
    # 测试便捷函数
    print("\n=== 测试便捷函数 ===")
    try:
        # 再次切换到src目录测试
        os.chdir(src_dir)
        ai_config = get_ai_config()
        print(f"便捷函数 API Key: {'已设置' if ai_config.gemini_api_key else '未设置'}")
        if ai_config.gemini_api_key:
            masked_key = ai_config.gemini_api_key[:8] + "..." + ai_config.gemini_api_key[-4:]
            print(f"API Key (便捷函数): {masked_key}")
        
        # 恢复原目录
        os.chdir(original_cwd)
        
    except Exception as e:
        print(f"便捷函数测试失败: {e}")
        os.chdir(original_cwd)

if __name__ == "__main__":
    debug_config_loading()