#!/usr/bin/env python3
# 快速测试AI对话功能

import os
import sys
sys.path.insert(0, 'src')

def test_gemini_direct():
    """直接测试Gemini API"""
    try:
        import google.generativeai as genai
        
        # 加载环境变量
        with open('.ai_pet_env', 'r') as f:
            for line in f:
                if line.startswith('export ') and '=' in line:
                    line = line.replace('export ', '').strip()
                    key, value = line.split('=', 1)
                    value = value.strip('"')
                    os.environ[key] = value
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ GEMINI_API_KEY未设置")
            return False
        
        print("🤖 测试Gemini API直连...")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        response = model.generate_content("请简单回复'测试成功'")
        print(f"✅ Gemini API正常: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Gemini API异常: {e}")
        return False

def test_ai_conversation_module():
    """测试AI对话模块"""
    try:
        from ai_conversation import AIConversationManager
        
        print("🧠 测试AI对话模块...")
        ai_manager = AIConversationManager()
        
        response = ai_manager.get_ai_response("你好，请简单回复")
        print(f"✅ AI对话模块正常: {response[:50]}...")
        return True
        
    except Exception as e:
        print(f"❌ AI对话模块异常: {e}")
        return False

def main():
    print("🔍 快速AI对话诊断...")
    print("=" * 40)
    
    gemini_ok = test_gemini_direct()
    ai_module_ok = test_ai_conversation_module()
    
    print("=" * 40)
    if gemini_ok and ai_module_ok:
        print("✅ AI功能正常，Web接口可能需要更长超时时间")
        print("💡 建议直接通过Web界面测试AI对话")
    elif gemini_ok:
        print("⚠️ Gemini API正常，但AI模块有问题")
    else:
        print("❌ Gemini API配置有问题")

if __name__ == "__main__":
    main()