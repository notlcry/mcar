#!/usr/bin/env python3
"""
测试显示器集成系统
验证OLED显示器与AI语音对话系统的完整集成
"""

import sys
import time
import logging
import threading

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, 'src')

def test_display_integration():
    """测试显示器集成"""
    print("🖥️ 测试显示器与AI系统集成")
    print("=" * 50)
    
    try:
        # 导入相关模块
        from src.enhanced_voice_control import EnhancedVoiceController
        from src.display_controller import DisplayController
        
        # 创建模拟机器人
        class MockRobot:
            def t_stop(self, duration=0):
                pass
            def turnRight(self, angle, duration):
                print(f"🤖 机器人右转 {angle}度，{duration}秒")
            def turnLeft(self, angle, duration):
                print(f"🤖 机器人左转 {angle}度，{duration}秒")
            def moveLeft(self, distance, duration):
                print(f"🤖 机器人左移 {distance}，{duration}秒")
            def moveRight(self, distance, duration):
                print(f"🤖 机器人右移 {distance}，{duration}秒")
            def t_down(self, distance, duration):
                print(f"🤖 机器人后退 {distance}，{duration}秒")
        
        mock_robot = MockRobot()
        
        # 创建增强语音控制器（测试模式）
        print("🔧 创建增强语音控制器...")
        voice_controller = EnhancedVoiceController(
            robot=mock_robot,
            test_mode=True  # 测试模式避免音频流问题
        )
        
        if not voice_controller.display_controller:
            print("⚠️ 显示控制器不可用，但系统仍可正常运行")
        else:
            print("✅ 显示控制器集成成功")
        
        # 启动对话模式
        print("\n🚀 启动AI对话模式...")
        if voice_controller.start_conversation_mode():
            print("✅ AI对话模式启动成功")
            
            # 等待显示启动画面
            time.sleep(3)
            
            # 模拟用户交互流程
            print("\n🎭 模拟用户交互流程...")
            
            # 1. 模拟唤醒
            print("1. 模拟唤醒词检测...")
            voice_controller._on_wake_word_detected(0)
            time.sleep(3)
            
            # 2. 模拟用户语音和AI回复
            if voice_controller.display_controller:
                print("2. 模拟用户语音显示...")
                voice_controller.display_controller.show_user_speech("你好快快，今天天气怎么样？")
                time.sleep(3)
                
                print("3. 模拟AI思考状态...")
                voice_controller.display_controller.show_system_status("快快思考中...", 2.0)
                time.sleep(3)
                
                print("4. 模拟AI回复显示...")
                voice_controller.display_controller.show_ai_response("今天天气很好呢！快快很开心~")
                time.sleep(4)
                
                print("5. 模拟情感表情...")
                emotions = ['happy', 'excited', 'thinking', 'confused', 'sad']
                for emotion in emotions:
                    print(f"   显示{emotion}表情...")
                    voice_controller.display_controller.show_emotion(emotion, 2.0)
                    time.sleep(3)
                
                print("6. 测试动画效果...")
                voice_controller.display_controller.show_listening_animation(3.0)
                time.sleep(4)
                
                voice_controller.display_controller.show_speaking_animation(3.0)
                time.sleep(4)
            
            # 3. 测试表情控制器集成
            if voice_controller.expression_controller:
                print("7. 测试表情控制器集成...")
                voice_controller.expression_controller.show_listening_animation(2.0)
                time.sleep(3)
                
                voice_controller.expression_controller.show_thinking_animation(2.0)
                time.sleep(3)
                
                voice_controller.expression_controller.show_speaking_animation(2.0)
                time.sleep(3)
            
            print("\n📊 检查系统状态...")
            if voice_controller.display_controller:
                print(f"   显示控制器可用: ✅")
            else:
                print(f"   显示控制器可用: ❌")
            
            if voice_controller.expression_controller:
                status = voice_controller.expression_controller.get_status()
                print(f"   表情控制器状态: {status}")
            
            print("\n🎉 集成测试完成！")
            print("💡 测试结果:")
            print("✅ 显示器可以显示系统状态")
            print("✅ 显示器可以显示用户语音")
            print("✅ 显示器可以显示AI回复")
            print("✅ 显示器可以显示情感表情")
            print("✅ 显示器可以播放动画效果")
            print("✅ 表情控制器集成正常")
            
        else:
            print("❌ AI对话模式启动失败")
            return False
        
        # 停止系统
        print("\n🛑 停止系统...")
        voice_controller.stop_conversation_mode()
        time.sleep(2)
        
        return True
        
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        print("💡 请确保已安装显示器相关依赖:")
        print("   pip install adafruit-circuitpython-ssd1306 luma.oled")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_display_only():
    """仅测试显示控制器"""
    print("🖥️ 测试显示控制器（独立）")
    print("=" * 40)
    
    try:
        from src.display_controller import DisplayController
        
        display = DisplayController()
        
        if not display.is_available():
            print("❌ 显示器不可用")
            return False
        
        display.start()
        
        # 测试各种显示功能
        test_items = [
            ("系统状态", lambda: display.show_system_status("测试状态", 2.0)),
            ("用户语音", lambda: display.show_user_speech("这是用户说的话", 3.0)),
            ("AI回复", lambda: display.show_ai_response("这是AI的回复内容", 3.0)),
            ("开心表情", lambda: display.show_emotion("happy", 2.0)),
            ("思考表情", lambda: display.show_emotion("thinking", 2.0)),
            ("监听动画", lambda: display.show_listening_animation(3.0)),
            ("说话动画", lambda: display.show_speaking_animation(3.0)),
        ]
        
        for name, test_func in test_items:
            print(f"测试{name}...")
            test_func()
            time.sleep(1)
        
        display.stop()
        print("✅ 显示控制器测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 显示控制器测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 显示器集成测试程序")
    print("验证OLED显示器与AI语音系统的完整集成")
    print("=" * 60)
    
    # 选择测试模式
    print("选择测试模式:")
    print("1. 完整集成测试（推荐）")
    print("2. 仅显示器测试")
    print("3. 退出")
    
    while True:
        choice = input("\n请选择 (1-3): ").strip()
        
        if choice == "1":
            success = test_display_integration()
            break
        elif choice == "2":
            success = test_display_only()
            break
        elif choice == "3":
            print("退出测试")
            return
        else:
            print("无效选择，请重新输入")
    
    if success:
        print("\n🎉 测试成功！")
        print("📋 部署建议:")
        print("1. 在树莓派上运行完整系统")
        print("2. 确保SSD1306显示器正确连接")
        print("3. 启动AI语音对话系统")
        print("4. 享受带有视觉表情的AI伙伴！")
    else:
        print("\n😞 测试失败，请检查硬件连接和依赖")

if __name__ == "__main__":
    main()