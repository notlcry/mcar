#!/usr/bin/python3
"""
测试API配置是否正确
"""

import sys
import os

# 确保在正确的目录下运行
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# 添加src目录到路径
sys.path.append(script_dir)

from config import get_ai_config

def test_api_config():
    """测试API配置"""
    print("=== 测试API配置 ===")
    print(f"当前工作目录: {os.getcwd()}")
    
    ai_config = get_ai_config()
    
    print(f"Gemini API Key: {'已设置' if ai_config.gemini_api_key else '未设置'}")
    print(f"模型名称: {ai_config.model_name}")
    print(f"温度参数: {ai_config.temperature}")
    print(f"最大输出长度: {ai_config.max_output_tokens}")
    
    if ai_config.gemini_api_key:
        # 隐藏大部分API key，只显示前几位和后几位
        masked_key = ai_config.gemini_api_key[:8] + "..." + ai_config.gemini_api_key[-4:]
        print(f"API Key (部分): {masked_key}")
        print("✅ API配置完成，可以使用AI对话功能")
        return True
    else:
        print("❌ 请设置Gemini API Key")
        print("方式1: export GEMINI_API_KEY='your_key'")
        print("方式2: 编辑 ai_pet_config.json 文件")
        return False

if __name__ == "__main__":
    success = test_api_config()
    sys.exit(0 if success else 1)