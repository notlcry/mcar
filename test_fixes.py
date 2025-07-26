#!/usr/bin/env python3
# 测试修复结果

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

def test_gemini_fix():
    """测试Gemini修复"""
    print("🤖 测试Gemini初始化修复...")
    
    try:
        from ai_conversation import AIConversationManager
        
        # 创建AI对话管理器
        ai_manager = AIConversationManager()
        
        if ai_manager.model:
            print("✅ Gemini初始化成功")
            
            # 测试简单对话
            response = ai_manager.model.generate_content("请简单回复'修复成功'")
            print(f"   测试回复: {response.text}")
            return True
            
        else:
            print("❌ Gemini初始化失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_wake_word_logs():
    """测试唤醒词日志"""
    print("🎤 测试唤醒词日志...")
    
    try:
        from enhanced_voice_control import EnhancedVoiceController
        
        # 创建语音控制器
        voice_controller = EnhancedVoiceController()
        
        # 模拟唤醒词检测
        print("   模拟唤醒词检测...")
        voice_controller.conversation_mode = True
        voice_controller._on_wake_word_detected(0)
        
        print("✅ 唤醒词日志测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 唤醒词日志测试失败: {e}")
        return False

if __name__ == "__main__":
    print("====================================")
    print("🧪 测试修复结果")
    print("====================================")
    
    gemini_ok = test_gemini_fix()
    print()
    wake_word_ok = test_wake_word_logs()
    
    print("\n====================================")
    if gemini_ok and wake_word_ok:
        print("✅ 所有修复测试通过！")
        print("\n🚀 现在可以启动系统:")
        print("   cd src && python3 robot_voice_web_control.py")
        print("\n🎤 使用说明:")
        print("   • 说 'kk' 或 'picovoice' 唤醒系统")
        print("   • 查看日志中的唤醒提示")
        print("   • 与AI进行对话")
    else:
        print("❌ 部分测试失败，请检查错误信息")
    print("====================================")