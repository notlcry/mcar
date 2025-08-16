#!/usr/bin/env python3
# 快速测试修复结果

import os
import sys

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
sys.path.insert(0, 'src')

print("====================================")
print("🧪 快速测试修复结果")
print("====================================")

print("🔑 环境变量检查:")
print(f"   GEMINI_API_KEY: {'已设置' if os.getenv('GEMINI_API_KEY') else '未设置'}")
print(f"   PICOVOICE_ACCESS_KEY: {'已设置' if os.getenv('PICOVOICE_ACCESS_KEY') else '未设置'}")

print("\n🤖 测试Gemini初始化:")
try:
    from ai_conversation import AIConversationManager
    
    ai_manager = AIConversationManager()
    
    if ai_manager.model:
        print("✅ Gemini初始化成功")
        
        # 测试简单对话
        response = ai_manager.model.generate_content("请简单回复'测试成功'")
        print(f"   测试回复: {response.text}")
    else:
        print("❌ Gemini初始化失败")
        
except Exception as e:
    print(f"❌ 测试失败: {e}")

print("\n====================================")
print("✅ 测试完成")
print("====================================")
print("\n🚀 如果测试通过，可以启动系统:")
print("   cd src && python3 robot_voice_web_control.py")
print("\n🎤 使用说明:")
print("   • 说 'kk' 或 'picovoice' 唤醒系统")
print("   • 查看终端日志中的唤醒提示")
print("   • 与AI进行语音对话")