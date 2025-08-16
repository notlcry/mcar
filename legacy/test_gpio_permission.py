#!/usr/bin/env python3
"""
GPIO权限测试程序
用于检查是否能正常访问GPIO引脚
"""

import sys

def test_gpio_permission():
    print("🧪 测试GPIO权限...")
    
    try:
        import RPi.GPIO as GPIO
        print("✅ RPi.GPIO库导入成功")
    except ImportError as e:
        print(f"❌ RPi.GPIO库导入失败: {e}")
        print("💡 安装方法: sudo apt install python3-rpi.gpio")
        return False
    
    try:
        # 测试GPIO初始化
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        print("✅ GPIO模式设置成功")
        
        # 测试设置传感器引脚
        SensorLeft = 12
        SensorRight = 16
        TRIG = 20
        ECHO = 21
        
        GPIO.setup(SensorLeft, GPIO.IN)
        GPIO.setup(SensorRight, GPIO.IN) 
        GPIO.setup(TRIG, GPIO.OUT)
        GPIO.setup(ECHO, GPIO.IN)
        print("✅ 传感器引脚设置成功")
        
        # 测试读取GPIO
        left_val = GPIO.input(SensorLeft)
        right_val = GPIO.input(SensorRight)
        echo_val = GPIO.input(ECHO)
        print(f"✅ GPIO读取成功: 左侧={left_val}, 右侧={right_val}, 回声={echo_val}")
        
        # 测试GPIO输出
        GPIO.output(TRIG, GPIO.LOW)
        GPIO.output(TRIG, GPIO.HIGH) 
        GPIO.output(TRIG, GPIO.LOW)
        print("✅ GPIO输出测试成功")
        
        GPIO.cleanup()
        print("✅ GPIO清理完成")
        
        print("\n🎉 GPIO权限测试通过！传感器应该能正常工作")
        return True
        
    except Exception as e:
        print(f"❌ GPIO操作失败: {e}")
        print("\n💡 可能的解决方案:")
        print("1. 使用sudo运行: sudo python3 test_gpio_permission.py")
        print("2. 添加用户到gpio组: sudo usermod -a -G gpio $USER")
        print("3. 重启系统使组权限生效")
        print("4. 检查GPIO引脚是否被其他程序占用")
        return False

if __name__ == "__main__":
    print("🔌 GPIO权限检查工具")
    print("=" * 40)
    
    if test_gpio_permission():
        print("\n✅ 可以使用普通权限运行机器人程序")
    else:
        print("\n⚠️ 需要sudo权限或修复GPIO配置")
        print("建议运行: sudo ./start_ai_pet_quiet.sh")