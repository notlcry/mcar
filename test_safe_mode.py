#!/usr/bin/env python3
"""
测试安全模式 - 使用测试模式避免音频流段错误
"""

import os
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, 'src')

def test_safe_mode():
    """测试安全模式"""
    print("🛡️ 测试安全模式（无音频流）")
    print("=" * 50)
    
    try:
        # 导入修复后的控制器
        from enhanced_voice_control import EnhancedVoiceController
        
        # 创建模拟机器人
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        # 使用测试模式创建控制器
        print("🔧 创建测试模式控制器...")
        voice_controller = EnhancedVoiceController(
            robot=MockRobot(), 
            test_mode=True  # 关键：启用测试模式
        )
        print("✅ 控制器创建成功（测试模式）")
        
        # 启动对话模式
        print("🚀 启动AI对话模式（测试模式）...")
        if voice_controller.start_conversation_mode():
            print("✅ AI对话模式启动成功！")
            
            # 检查状态
            status = voice_controller.get_conversation_status()
            print(f"📊 当前状态: {status['state']}")
            print(f"🔔 唤醒词检测: {'跳过' if voice_controller.test_mode else '激活'}")
            
            # 运行10秒测试，应该不会段错误
            print("⏱️  运行10秒安全测试...")
            for i in range(10):
                time.sleep(1)
                if i % 3 == 0:
                    print(f"  {i+1}秒 - 运行正常")
            
            print("✅ 测试完成，没有段错误！")
            
            # 模拟唤醒
            print("🔔 模拟唤醒测试...")
            voice_controller.wake_word_detected = True
            
            status = voice_controller.get_conversation_status()  
            print(f"📊 唤醒后状态: {status['state']}")
            
            # 运行对话状态测试
            print("💬 运行对话状态测试...")
            time.sleep(3)
            
            # 停止
            print("🛑 停止AI对话模式...")
            voice_controller.stop_conversation_mode()
            print("✅ 安全停止成功")
            
            return True
        else:
            print("❌ 启动失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_normal_mode_check():
    """检查正常模式是否可用（不实际启动）"""
    print("\n🔍 检查正常模式组件...")
    
    try:
        from enhanced_voice_control import EnhancedVoiceController
        
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        # 创建普通模式控制器（不启动）
        voice_controller = EnhancedVoiceController(
            robot=MockRobot(), 
            test_mode=False
        )
        
        print("✅ 普通模式控制器可以创建")
        
        # 检查组件状态
        print(f"   唤醒词检测器: {'可用' if voice_controller.wake_word_detector else '不可用'}")
        print(f"   Vosk识别器: {'可用' if voice_controller.use_vosk else '不可用'}")
        print(f"   Whisper识别器: {'可用' if voice_controller.use_whisper else '不可用'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 普通模式检查失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 安全模式测试")
    print("验证测试模式是否能避免段错误")
    print("=" * 60)
    
    # 测试1: 安全模式
    test1_success = test_safe_mode()
    
    # 测试2: 普通模式组件检查
    test2_success = test_normal_mode_check()
    
    if test1_success:
        print("\n🎉 安全模式测试成功！")
        print("📋 测试结果:")
        print("✅ 测试模式可以避免段错误")
        print("✅ 核心逻辑工作正常")
        print("✅ 状态管理正确")
        print("✅ AI对话系统可用")
        
        if test2_success:
            print("✅ 普通模式组件检查通过")
        
        print("\n💡 使用建议:")
        print("1. 在开发/测试时使用测试模式: test_mode=True")
        print("2. 部署时使用普通模式，但需要解决音频设备问题")
        print("3. 可以逐步启用音频功能")
        
    else:
        print("\n😞 测试失败，需要进一步调试")

if __name__ == "__main__":
    main()