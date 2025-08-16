#!/usr/bin/env python3
# 测试语音识别日志

import os
import sys
import logging

# 设置日志格式，与系统一致
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

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

def test_voice_controller_logs():
    print("🔍 测试增强语音控制器日志")
    print("=" * 50)
    
    try:
        from enhanced_voice_control import EnhancedVoiceController
        
        # 创建模拟机器人
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        mock_robot = MockRobot()
        
        print("创建增强语音控制器（观察日志输出）...")
        print("-" * 50)
        
        # 这里应该会输出详细的初始化日志
        voice_controller = EnhancedVoiceController(robot=mock_robot)
        
        print("-" * 50)
        print("✅ 增强语音控制器创建完成")
        
        # 显示状态
        print(f"\n📊 状态总结:")
        print(f"   Vosk可用: {voice_controller.use_vosk}")
        print(f"   Whisper可用: {voice_controller.use_whisper}")
        
        if hasattr(voice_controller, 'vosk_recognizer') and voice_controller.vosk_recognizer:
            print(f"   Vosk识别器状态: {voice_controller.vosk_recognizer.is_available}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_vosk_recognizer_logs():
    print("\n🔍 测试Vosk识别器日志")
    print("=" * 50)
    
    try:
        from vosk_recognizer import VoskRecognizer
        
        print("创建Vosk识别器（观察日志输出）...")
        print("-" * 50)
        
        # 这里应该会输出Vosk初始化日志
        vosk_rec = VoskRecognizer()
        
        print("-" * 50)
        print(f"✅ Vosk识别器创建完成，可用: {vosk_rec.is_available}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 语音识别日志测试")
    print("=" * 50)
    
    print("这个测试会显示系统启动时的详细日志")
    print("请观察是否有以下关键日志:")
    print("• 🎤 正在初始化Vosk中文语音识别...")
    print("• 🎉 Vosk中文语音识别初始化成功！")
    print("• 📊 语音识别引擎状态")
    print()
    
    vosk_ok = test_vosk_recognizer_logs()
    controller_ok = test_voice_controller_logs()
    
    print("\n" + "=" * 50)
    print("📋 测试结果")
    print("=" * 50)
    
    if vosk_ok and controller_ok:
        print("✅ 日志系统正常")
        print("\n💡 现在重启AI桌宠系统，你应该能看到:")
        print("1. 启动时的详细语音引擎状态")
        print("2. 语音识别时每个引擎的尝试过程")
        print("3. 明确显示使用了哪个识别引擎")
        print("\n🚀 重启命令:")
        print("   停止当前系统 (Ctrl+C)")
        print("   ./start_ai_pet_quiet.sh")
    else:
        print("❌ 日志系统有问题")
    
    print(f"\n🌐 Web界面: http://localhost:5000")