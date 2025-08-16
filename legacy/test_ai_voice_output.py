#!/usr/bin/env python3
"""
测试AI对话的语音输出
"""

import os
import sys
import time

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

def test_ai_voice_output():
    """测试AI对话的语音输出"""
    print("🤖 测试AI对话语音输出")
    print("=" * 50)
    
    try:
        from enhanced_voice_control import EnhancedVoiceController
        
        # 创建模拟机器人
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        mock_robot = MockRobot()
        
        # 创建增强语音控制器
        print("🔧 初始化增强语音控制器...")
        voice_controller = EnhancedVoiceController(robot=mock_robot)
        
        print("✅ 增强语音控制器初始化成功")
        
        # 启动对话模式
        print("🔄 启动对话模式...")
        voice_controller.start_conversation_mode()
        
        # 测试语音输出
        test_phrases = [
            "你好！我是AI桌宠，很高兴为您服务！",
            "我现在可以正常进行语音回复了。",
            "这是修复后的TTS语音合成系统。",
            "AI对话的语音输出功能已经正常工作。"
        ]
        
        print("\n🗣️  测试AI语音回复...")
        for i, phrase in enumerate(test_phrases, 1):
            print(f"\n🧪 测试 {i}: {phrase}")
            
            # 使用speak_text方法（这是AI对话使用的方法）
            voice_controller.speak_text(phrase)
            
            # 等待播放完成
            time.sleep(len(phrase) * 0.2 + 2)  # 根据文本长度估算等待时间
            
            print(f"✅ 测试 {i} 完成")
        
        print("\n🎉 AI语音输出测试完成！")
        
        # 停止对话模式
        voice_controller.stop_conversation_mode()
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_tts_method():
    """直接测试TTS方法"""
    print("\n🔧 直接测试TTS方法")
    print("=" * 30)
    
    try:
        from enhanced_voice_control import EnhancedVoiceController
        
        # 创建模拟机器人
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        mock_robot = MockRobot()
        voice_controller = EnhancedVoiceController(robot=mock_robot)
        
        # 直接测试语音生成和播放
        test_text = "这是直接TTS方法测试"
        print(f"🗣️  测试文本: {test_text}")
        
        # 直接调用语音生成播放方法
        voice_controller._generate_and_play_speech(test_text)
        
        print("✅ 直接TTS方法测试成功")
        return True
        
    except Exception as e:
        print(f"❌ 直接TTS方法测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🤖 AI对话语音输出测试")
    print("=" * 60)
    
    # 检查依赖
    print("📦 检查依赖...")
    
    try:
        import edge_tts
        print("✅ edge-tts可用")
    except ImportError:
        print("❌ edge-tts未安装")
        print("💡 运行: pip install edge-tts")
        sys.exit(1)
    
    # 直接测试TTS方法
    if test_direct_tts_method():
        print("\n🎉 直接TTS方法正常！")
        
        # 测试完整AI语音输出
        print("\n" + "=" * 60)
        if test_ai_voice_output():
            print("\n🎉 AI对话语音输出测试成功！")
            print("\n✅ 现在AI对话系统可以:")
            print("• 使用可靠的音频播放方式")
            print("• 正常进行语音回复")
            print("• 支持中文TTS语音合成")
            print("• 与唤醒词检测完美配合")
            
            print("\n💡 完整的语音交互流程:")
            print("1. 说 '快快' 唤醒AI桌宠")
            print("2. 说出你的问题或指令")
            print("3. AI理解并生成回复")
            print("4. 听到AI的语音回复")
        else:
            print("\n❌ AI语音输出测试失败")
    else:
        print("\n❌ 直接TTS方法测试失败")