#!/usr/bin/env python3
"""
调试显示器问题
检查显示器连接和驱动状态
"""

import sys
import subprocess
import time
import os

sys.path.insert(0, 'src')

def check_i2c_connection():
    """检查I2C连接"""
    print("🔍 检查I2C连接...")
    
    try:
        result = subprocess.run(['i2cdetect', '-y', '1'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ I2C扫描结果:")
            print(result.stdout)
            
            # 检查SSD1306设备
            output = result.stdout.lower()
            if '3c' in output:
                print("✅ 发现SSD1306设备 (地址: 0x3C)")
                return 0x3C
            elif '3d' in output:
                print("✅ 发现SSD1306设备 (地址: 0x3D)")  
                return 0x3D
            else:
                print("❌ 未发现SSD1306设备")
                print("💡 请检查硬件连接:")
                print("   VCC -> 3.3V")
                print("   GND -> GND")
                print("   SCL -> GPIO 3")
                print("   SDA -> GPIO 2")
                return None
        else:
            print(f"❌ I2C扫描失败: {result.stderr}")
            return None
            
    except FileNotFoundError:
        print("❌ 未找到i2cdetect命令")
        print("💡 安装: sudo apt install i2c-tools")
        return None
    except Exception as e:
        print(f"❌ I2C检查失败: {e}")
        return None

def test_display_driver():
    """测试显示驱动"""
    print("\n🧪 测试显示驱动...")
    
    try:
        from src.display_controller import DisplayController
        
        print("✅ 显示控制器模块导入成功")
        
        display = DisplayController()
        print(f"显示控制器创建: {'✅' if display else '❌'}")
        
        if display.is_available():
            print("✅ 显示器可用")
            
            # 测试启动
            if display.start():
                print("✅ 显示控制器启动成功")
                
                # 测试基本显示
                display.show_system_status("测试显示", 3.0)
                print("✅ 测试消息已发送到显示器")
                time.sleep(4)
                
                display.stop()
                print("✅ 显示控制器已停止")
                return True
            else:
                print("❌ 显示控制器启动失败")
                return False
        else:
            print("❌ 显示器不可用")
            return False
            
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("💡 请检查依赖:")
        print("   pip install adafruit-circuitpython-ssd1306 luma.oled")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_dependencies():
    """检查依赖"""
    print("\n📦 检查依赖...")
    
    required_packages = [
        ("PIL", "Pillow"),
        ("luma.oled", "luma-oled"), 
        ("adafruit_ssd1306", "adafruit-circuitpython-ssd1306"),
        ("board", "adafruit-blinka")
    ]
    
    missing_packages = []
    
    for package, install_name in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (安装: pip install {install_name})")
            missing_packages.append(install_name)
    
    if missing_packages:
        print(f"\n💡 缺少依赖，请安装:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    else:
        print("✅ 所有依赖都已安装")
        return True

def check_system_integration():
    """检查系统集成"""
    print("\n🔗 检查系统集成...")
    
    try:
        from src.enhanced_voice_control import EnhancedVoiceController
        
        # 创建模拟机器人
        class MockRobot:
            def t_stop(self, duration=0): pass
        
        print("创建语音控制器...")
        controller = EnhancedVoiceController(robot=MockRobot(), test_mode=True)
        
        print(f"显示控制器集成: {'✅' if controller.display_controller else '❌'}")
        
        if controller.display_controller:
            print("✅ 显示控制器已集成到语音控制器")
            
            # 测试集成功能
            if controller.display_controller.is_available():
                print("✅ 集成的显示器可用")
                return True
            else:
                print("❌ 集成的显示器不可用")
                return False
        else:
            print("❌ 显示控制器未集成")
            return False
            
    except Exception as e:
        print(f"❌ 系统集成检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_logs():
    """检查最近的日志"""
    print("\n📋 分析问题...")
    
    # 基于用户提供的日志进行分析
    print("根据您的日志分析:")
    print("✅ AI语音控制器正常启动")
    print("✅ Vosk中文识别可用")
    print("✅ AI对话功能正常")
    print("✅ 情感分析正常工作")
    print("❌ 没有看到显示控制器初始化日志")
    print("")
    print("🔍 可能的问题:")
    print("1. 显示控制器模块导入失败")
    print("2. I2C设备未正确连接")
    print("3. 显示驱动库未安装")
    print("4. 权限问题")

def main():
    """主调试函数"""
    print("🐛 显示器调试工具")
    print("诊断OLED显示器无显示问题")
    print("=" * 50)
    
    # 按步骤检查
    steps = [
        ("检查依赖包", check_dependencies),
        ("检查I2C连接", check_i2c_connection), 
        ("测试显示驱动", test_display_driver),
        ("检查系统集成", check_system_integration),
        ("分析日志", check_logs)
    ]
    
    results = {}
    
    for step_name, step_func in steps:
        print(f"\n{'='*20} {step_name} {'='*20}")
        try:
            if step_name == "检查I2C连接":
                result = step_func()
                results[step_name] = result is not None
            else:
                result = step_func()
                results[step_name] = result
        except Exception as e:
            print(f"❌ {step_name} 执行失败: {e}")
            results[step_name] = False
    
    # 汇总结果
    print(f"\n{'='*20} 诊断结果 {'='*20}")
    for step, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {step}")
    
    # 提供解决建议
    print(f"\n💡 解决建议:")
    
    if not results.get("检查依赖包", False):
        print("1. 首先安装缺失的依赖包")
        print("   pip install adafruit-circuitpython-ssd1306 luma.oled")
    
    if not results.get("检查I2C连接", False):
        print("2. 检查硬件连接和I2C配置")
        print("   - 确认SSD1306正确连接到树莓派")
        print("   - 启用I2C: sudo raspi-config -> Interface Options -> I2C")
        print("   - 重启系统")
    
    if not results.get("测试显示驱动", False):
        print("3. 显示驱动问题")
        print("   - 检查设备权限: sudo usermod -a -G i2c $USER")
        print("   - 尝试不同的I2C地址 (0x3C 或 0x3D)")
    
    if not results.get("检查系统集成", False):
        print("4. 系统集成问题")
        print("   - 检查显示控制器是否正确导入")
        print("   - 确认enhanced_voice_control.py的修改")

if __name__ == "__main__":
    main()