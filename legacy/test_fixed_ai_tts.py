#!/usr/bin/env python3
"""
测试修复后的AI TTS功能
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

def test_enhanced_voice_tts():
    """测试增强语音控制器的TTS功能"""
    print("🤖 测试修复后的AI TTS功能")
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
        
        # 直接测试语音生成播放方法
        test_phrases = [
            "你好！我是AI桌宠，修复后的语音测试。",
            "现在应该能听到清晰的中文语音了。",
            "TTS系统已经正常工作！"
        ]
        
        print("\n🗣️  测试修复后的TTS...")
        for i, phrase in enumerate(test_phrases, 1):
            print(f"\n🧪 测试 {i}: {phrase}")
            
            # 直接调用语音生成播放方法
            voice_controller._generate_and_play_speech(phrase)
            
            print(f"✅ 测试 {i} 完成")
            time.sleep(1)  # 短暂间隔
        
        print("\n🎉 修复后的AI TTS测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_complete_ai_voice_system():
    """测试完整的AI语音系统"""
    print("\n🎤 测试完整的AI语音系统")
    print("=" * 50)
    
    try:
        from wake_word_detector import WakeWordDetector
        from enhanced_voice_control import EnhancedVoiceController
        
        # 创建模拟机器人
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        mock_robot = MockRobot()
        
        # 创建增强语音控制器
        print("🔧 初始化系统...")
        voice_controller = EnhancedVoiceController(robot=mock_robot)
        
        # 启动对话模式
        voice_controller.start_conversation_mode()
        
        print("✅ AI语音系统初始化成功")
        print("\n🎙️  现在可以:")
        print("• 说 '快快' 唤醒AI桌宠")
        print("• 听到清晰的中文语音回复")
        print("• 进行完整的语音对话")
        
        print("\n💡 系统已准备就绪，按Ctrl+C退出")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 停止系统...")
            voice_controller.stop_conversation_mode()
            print("✅ 系统已停止")
        
        return True
        
    except Exception as e:
        print(f"❌ 系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🤖 修复后的AI TTS系统测试")
    print("=" * 60)
    
    # 先测试TTS功能
    if test_enhanced_voice_tts():
        print("\n🎉 TTS功能正常！")
        
        # 询问是否测试完整系统
        print("\n" + "=" * 60)
        print("🎤 是否测试完整的AI语音系统？")
        print("💡 这将启动唤醒词检测，你可以说 '快快' 进行测试")
        
        response = input("输入 'y' 开始测试，或按Enter跳过: ").strip().lower()
        
        if response == 'y':
            test_complete_ai_voice_system()
        else:
            print("✅ TTS测试完成，跳过完整系统测试")
    else:
        print("\n❌ TTS功能仍有问题")