#!/usr/bin/env python3
# 测试唤醒词检测器修复

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

def test_wake_word_detector():
    print("🔧 测试唤醒词检测器修复")
    print("=" * 40)
    
    try:
        from wake_word_detector import WakeWordDetector
        
        print("1. 测试WakeWordDetector创建...")
        detector = WakeWordDetector()
        print("✅ WakeWordDetector创建成功")
        
        if detector.porcupine:
            print("✅ Porcupine初始化成功")
            print(f"   使用关键词: {detector.keywords}")
            print(f"   帧长度: {detector.porcupine.frame_length}")
            print(f"   采样率: {detector.porcupine.sample_rate}")
        else:
            print("❌ Porcupine初始化失败")
            return False
        
        print("\n2. 测试增强语音控制器...")
        from enhanced_voice_control import EnhancedVoiceController
        
        # 创建模拟机器人
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        mock_robot = MockRobot()
        voice_controller = EnhancedVoiceController(robot=mock_robot)
        print("✅ 增强语音控制器创建成功")
        
        if hasattr(voice_controller, 'wake_word_detector'):
            print("✅ 唤醒词检测器组件存在")
        
        print("\n🎉 唤醒词检测器修复成功！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_wake_word_detector()
    if success:
        print("\n✅ 修复验证成功！现在可以启动AI桌宠系统了")
        print("启动命令: ./start_ai_pet_quiet.sh")
    else:
        print("\n❌ 修复验证失败，需要进一步检查")
    
    sys.exit(0 if success else 1)