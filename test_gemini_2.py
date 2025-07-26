#!/usr/bin/env python3
# 快速测试Gemini 2.0模型

import os
import google.generativeai as genai

# 加载环境变量
def load_env():
    try:
        with open('.ai_pet_env', 'r') as f:
            for line in f:
                if line.startswith('export ') and '=' in line:
                    line = line.replace('export ', '').strip()
                    key, value = line.split('=', 1)
                    value = value.strip('"')
                    os.environ[key] = value
    except:
        pass

load_env()

def test_gemini_2():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY未设置")
        return False
    
    print(f"🔑 API Key: {api_key[:20]}...")
    
    genai.configure(api_key=api_key)
    
    # 测试Gemini 2.0模型
    models_to_test = [
        'gemini-2.0-flash-exp',
        'gemini-1.5-flash',
        'gemini-1.5-pro'
    ]
    
    for model_name in models_to_test:
        try:
            print(f"\n🧪 测试 {model_name}...")
            model = genai.GenerativeModel(model_name)
            
            response = model.generate_content("请用中文回复'测试成功'")
            
            print(f"✅ {model_name} - 工作正常")
            print(f"   回复: {response.text}")
            return True
            
        except Exception as e:
            print(f"❌ {model_name} - 失败: {str(e)[:100]}...")
            continue
    
    print("❌ 所有模型都测试失败")
    return False

if __name__ == "__main__":
    print("====================================")
    print("🚀 Gemini 2.0 快速测试")
    print("====================================")
    
    if test_gemini_2():
        print("\n✅ Gemini API配置正确，可以启动系统！")
        print("启动命令: cd src && python3 robot_voice_web_control.py")
    else:
        print("\n❌ Gemini API配置有问题，请检查API密钥")