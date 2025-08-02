#!/usr/bin/env python3
"""
红外避障传感器测试程序
用于验证红外传感器是否正常工作
"""

import RPi.GPIO as GPIO
import time
import sys

# 传感器引脚定义
SensorRight = 16  # 右侧红外避障传感器
SensorLeft = 12   # 左侧红外避障传感器
TRIG = 20         # 超声波触发引脚
ECHO = 21         # 超声波回声引脚

def setup_gpio():
    """设置GPIO引脚"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # 设置红外传感器引脚为输入
    GPIO.setup(SensorRight, GPIO.IN)
    GPIO.setup(SensorLeft, GPIO.IN)
    
    # 设置超声波传感器引脚
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)
    
    print("✅ GPIO引脚设置完成")

def read_infrared_sensors():
    """读取红外传感器"""
    try:
        # 读取红外传感器（低电平表示有障碍）
        left_raw = GPIO.input(SensorLeft)
        right_raw = GPIO.input(SensorRight)
        
        # 转换为障碍检测结果
        left_obstacle = not left_raw  # 低电平=有障碍
        right_obstacle = not right_raw  # 低电平=有障碍
        
        return {
            'left_raw': left_raw,
            'right_raw': right_raw,
            'left_obstacle': left_obstacle,
            'right_obstacle': right_obstacle
        }
    except Exception as e:
        print(f"❌ 读取红外传感器错误: {e}")
        return None

def read_ultrasonic():
    """读取超声波距离"""
    try:
        # 触发超声波
        GPIO.output(TRIG, GPIO.LOW)
        time.sleep(0.000002)
        GPIO.output(TRIG, GPIO.HIGH)
        time.sleep(0.00001)
        GPIO.output(TRIG, GPIO.LOW)
        
        # 测量回声时间
        start_time = time.time()
        timeout = start_time + 0.1  # 100ms超时
        
        while GPIO.input(ECHO) == 0 and time.time() < timeout:
            start_time = time.time()
        
        while GPIO.input(ECHO) == 1 and time.time() < timeout:
            end_time = time.time()
        
        if time.time() >= timeout:
            return -1  # 超时
        
        # 计算距离
        duration = end_time - start_time
        distance = duration * 34300 / 2  # 声速34300cm/s
        
        return round(distance, 1)
    except Exception as e:
        print(f"❌ 读取超声波错误: {e}")
        return -1

def test_sensors():
    """测试传感器功能"""
    print("🧪 红外避障传感器测试")
    print("=" * 50)
    print("说明:")
    print("  - 左侧传感器引脚: GPIO12")
    print("  - 右侧传感器引脚: GPIO16")
    print("  - 超声波传感器: GPIO20(TRIG), GPIO21(ECHO)")
    print("  - 红外传感器低电平(0)表示检测到障碍")
    print("  - 红外传感器高电平(1)表示无障碍")
    print()
    print("请在传感器前放置/移除障碍物进行测试...")
    print("按 Ctrl+C 退出")
    print()
    
    try:
        while True:
            # 读取红外传感器
            ir_data = read_infrared_sensors()
            
            # 读取超声波
            distance = read_ultrasonic()
            
            if ir_data:
                # 显示传感器状态
                left_status = "🔴 有障碍" if ir_data['left_obstacle'] else "🟢 无障碍"
                right_status = "🔴 有障碍" if ir_data['right_obstacle'] else "🟢 无障碍"
                
                print(f"\\r左侧: {left_status} (GPIO:{ir_data['left_raw']}) | "
                      f"右侧: {right_status} (GPIO:{ir_data['right_raw']}) | "
                      f"距离: {distance if distance > 0 else '超时'}cm", end="", flush=True)
            
            time.sleep(0.2)
            
    except KeyboardInterrupt:
        print("\\n\\n✅ 测试结束")
    except Exception as e:
        print(f"\\n❌ 测试错误: {e}")
    finally:
        GPIO.cleanup()
        print("🧹 GPIO清理完成")

def main():
    """主函数"""
    try:
        setup_gpio()
        test_sensors()
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        print("💡 请确保:")
        print("  1. 以root权限运行 (sudo)")
        print("  2. 传感器正确连接")
        print("  3. 没有其他程序占用GPIO")
        sys.exit(1)

if __name__ == "__main__":
    main()