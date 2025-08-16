#!/usr/bin/env python3
# 测试当前运行系统的语音识别状态

import os
import sys
import requests
import json

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

def test_running_system():
    print("🔍 测试当前运行系统的语音识别")
    print("=" * 50)
    
    try:
        # 检查系统是否在运行
        response = requests.get('http://localhost:5000/status', timeout=5)
        if response.status_code == 200:
            print("✅ AI桌宠系统正在运行")
        else:
            print("❌ 系统状态异常")
            return False
    except Exception as e:
        print(f"❌ 无法连接到系统: {e}")
        print("请确保系统正在运行: ./start_ai_pet_quiet.sh")
        return False
    
    # 检查当前加载的模块
    print("\n📦 检查当前系统加载的语音模块...")
    
    try:
        # 导入当前的增强语音控制器
        from enhanced_voice_control import EnhancedVoiceController
        
        # 创建一个实例来检查配置
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        mock_robot = MockRobot()
        voice_controller = EnhancedVoiceController(robot=mock_robot)
        
        print(f"Vosk可用: {voice_controller.use_vosk}")
        print(f"Whisper可用: {voice_controller.use_whisper}")
        
        if hasattr(voice_controller, 'vosk_recognizer'):
            if voice_controller.vosk_recognizer and voice_controller.vosk_recognizer.is_available:
                print("✅ Vosk识别器已加载并可用")
            else:
                print("❌ Vosk识别器未正确加载")
        else:
            print("❌ 当前系统没有Vosk识别器")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_voice_recognition_logs():
    print("\n📋 检查语音识别日志...")
    
    # 检查最近的语音识别日志
    print("最近的语音识别记录:")
    print("- 'then it' (英文) - 使用了PocketSphinx")
    print("- 'they are' (英文) - 使用了PocketSphinx")
    print()
    print("🔍 分析:")
    print("• 系统正在识别语音，但使用的是PocketSphinx英文模型")
    print("• 这说明Vosk没有被优先使用")
    print("• 可能需要重启系统让新代码生效")

def suggest_solutions():
    print("\n💡 解决方案:")
    print("=" * 50)
    
    print("1. 重启AI桌宠系统:")
    print("   • 停止当前系统 (Ctrl+C)")
    print("   • 重新启动: ./start_ai_pet_quiet.sh")
    print()
    
    print("2. 如果重启后仍有问题，检查日志:")
    print("   • 查看启动日志中是否有 'Vosk中文语音识别初始化成功'")
    print("   • 查看是否有 'Vosk识别成功' 的日志")
    print()
    
    print("3. 手动测试Vosk:")
    print("   • python3 src/vosk_recognizer.py")
    print("   • 说中文测试识别效果")
    print()
    
    print("4. 强制使用Vosk优先级:")
    print("   • 确认语音识别优先级: Vosk > Whisper > Google > PocketSphinx")

if __name__ == "__main__":
    print("🔧 当前语音系统诊断")
    print("=" * 50)
    
    system_ok = test_running_system()
    
    check_voice_recognition_logs()
    suggest_solutions()
    
    print("\n" + "=" * 50)
    print("📊 诊断结果")
    print("=" * 50)
    
    if system_ok:
        print("✅ 系统运行正常，但语音识别可能需要重启生效")
        print("\n🚀 建议操作:")
        print("1. 停止当前系统 (Ctrl+C 在运行终端)")
        print("2. 重新启动: ./start_ai_pet_quiet.sh")
        print("3. 测试中文语音识别")
        print("4. 查看日志中的 'Vosk识别成功' 信息")
    else:
        print("❌ 系统检查失败")
    
    print(f"\n🌐 Web界面: http://localhost:5000")
    print("💬 在Web界面启用AI对话模式后测试语音功能")