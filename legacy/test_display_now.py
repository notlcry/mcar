#!/usr/bin/env python3
"""
快速测试显示器是否正在工作
用于验证OLED显示器是否真的显示内容
"""

import sys
import time
sys.path.insert(0, 'src')

def test_display_quick():
    """快速测试显示器"""
    print("🧪 快速测试OLED显示器")
    print("请观察OLED屏幕是否有内容显示")
    print("=" * 40)
    
    try:
        from src.display_controller import DisplayController
        
        print("1. 创建显示控制器...")
        display = DisplayController()
        
        if not display.is_available():
            print("❌ 显示器不可用")
            return False
        
        print("2. 启动显示控制器...")
        display.start()
        
        print("3. 清空屏幕...")
        display.clear()
        time.sleep(1)
        
        print("4. 显示测试文本...")
        display.add_message("text", "快快测试\n显示器工作\n请查看屏幕", 3.0, priority=3)
        time.sleep(4)
        
        print("5. 显示系统状态...")
        display.show_system_status("系统正常", 2.0)
        time.sleep(3)
        
        print("6. 显示开心表情...")
        display.show_emotion("happy", 3.0)
        time.sleep(4)
        
        print("7. 显示说话动画...")
        display.show_speaking_animation(3.0)
        time.sleep(4)
        
        print("8. 显示AI回复...")
        display.show_ai_response("这是AI的回复测试", 3.0)
        time.sleep(4)
        
        print("9. 清空并停止...")
        display.clear()
        display.stop()
        
        print("✅ 测试完成")
        print("\n❓ 问题: 您看到OLED屏幕上有内容显示吗？")
        print("   如果没有，可能的原因:")
        print("   1. 硬件连接问题")
        print("   2. I2C地址不正确")
        print("   3. 显示器队列处理问题")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_basic_display():
    """测试基础显示功能"""
    print("\n🧪 测试基础显示功能")
    print("=" * 30)
    
    try:
        # 直接使用显示库测试
        from luma.core.interface.serial import i2c
        from luma.core.render import canvas
        from luma.oled.device import ssd1306
        from PIL import ImageFont
        
        print("1. 直接初始化显示器...")
        interface = i2c(port=1, address=0x3C)
        device = ssd1306(interface, width=128, height=64)
        
        print("2. 绘制简单内容...")
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline=0, fill=0)
            draw.text((10, 10), "HELLO", fill=255)
            draw.text((10, 30), "快快测试", fill=255)
            draw.rectangle([10, 50, 50, 60], outline=1, fill=1)
        
        print("✅ 基础显示测试完成")
        print("❓ 您现在看到屏幕上有 'HELLO' 和 '快快测试' 吗？")
        
        time.sleep(5)
        
        # 清空屏幕
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline=0, fill=0)
        
        return True
        
    except Exception as e:
        print(f"❌ 基础测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试"""
    print("🖥️ OLED显示器工作状态测试")
    print("=" * 50)
    
    # 先测试基础显示
    print("首先测试基础显示功能...")
    basic_result = test_basic_display()
    
    input("\n按回车键继续高级测试...")
    
    # 再测试集成显示
    print("\n然后测试集成显示控制器...")
    advanced_result = test_display_quick()
    
    print(f"\n📋 测试结果:")
    print(f"   基础显示: {'✅' if basic_result else '❌'}")
    print(f"   集成显示: {'✅' if advanced_result else '❌'}")
    
    if basic_result and advanced_result:
        print("\n🎉 显示器工作正常！")
        print("如果您没有看到内容，请检查:")
        print("1. 硬件连接是否正确")
        print("2. 显示器是否损坏")
        print("3. I2C地址是否正确")
    elif basic_result and not advanced_result:
        print("\n⚠️ 基础显示正常，但集成显示有问题")
        print("可能是显示控制器的队列或消息处理有问题")
    else:
        print("\n❌ 显示器可能有硬件问题")
        print("请检查连接和硬件状态")

if __name__ == "__main__":
    main()