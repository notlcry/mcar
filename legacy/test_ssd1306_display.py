#!/usr/bin/env python3
"""
SSD1306 OLED显示模块测试程序
测试显示器的基本功能，包括文本、图形和动画
"""

import time
import datetime
import sys
from PIL import Image, ImageDraw, ImageFont
import threading
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import board
    import digitalio
    import adafruit_ssd1306
    I2C_AVAILABLE = True
    logger.info("✅ Adafruit SSD1306库可用")
except ImportError:
    I2C_AVAILABLE = False
    logger.warning("❌ 未找到Adafruit SSD1306库")

try:
    from luma.core.interface.serial import i2c
    from luma.core.render import canvas
    from luma.oled.device import ssd1306
    LUMA_AVAILABLE = True
    logger.info("✅ Luma OLED库可用")
except ImportError:
    LUMA_AVAILABLE = False
    logger.warning("❌ 未找到Luma OLED库")

class SSD1306Display:
    """SSD1306显示器控制类"""
    
    def __init__(self, width=128, height=64, i2c_address=0x3C):
        """
        初始化显示器
        Args:
            width: 显示器宽度（像素）
            height: 显示器高度（像素）
            i2c_address: I2C地址
        """
        self.width = width
        self.height = height
        self.i2c_address = i2c_address
        self.device = None
        self.interface = None
        self.library_used = None
        
        # 尝试初始化显示器
        self._initialize_display()
    
    def _initialize_display(self):
        """初始化显示器连接"""
        logger.info("🔌 正在初始化SSD1306显示器...")
        
        # 方法1: 尝试使用Luma OLED库
        if LUMA_AVAILABLE:
            try:
                self.interface = i2c(port=1, address=self.i2c_address)
                self.device = ssd1306(self.interface, width=self.width, height=self.height)
                self.library_used = "luma"
                logger.info("✅ 使用Luma OLED库初始化成功")
                return True
            except Exception as e:
                logger.warning(f"❌ Luma OLED库初始化失败: {e}")
        
        # 方法2: 尝试使用Adafruit库
        if I2C_AVAILABLE:
            try:
                i2c_bus = board.I2C()
                self.device = adafruit_ssd1306.SSD1306_I2C(self.width, self.height, i2c_bus, addr=self.i2c_address)
                self.library_used = "adafruit"
                logger.info("✅ 使用Adafruit库初始化成功")
                return True
            except Exception as e:
                logger.warning(f"❌ Adafruit库初始化失败: {e}")
        
        # 如果都失败了
        logger.error("❌ 所有库都初始化失败，可能的原因:")
        logger.error("   1. SSD1306显示器未正确连接")
        logger.error("   2. I2C地址不正确（尝试0x3C或0x3D）")
        logger.error("   3. 需要安装库: pip install adafruit-circuitpython-ssd1306 luma.oled")
        logger.error("   4. 需要启用I2C: sudo raspi-config -> Interface Options -> I2C -> Enable")
        return False
    
    def clear(self):
        """清空显示器"""
        if not self.device:
            return False
        
        try:
            if self.library_used == "luma":
                with canvas(self.device) as draw:
                    draw.rectangle(self.device.bounding_box, outline=0, fill=0)
            elif self.library_used == "adafruit":
                self.device.fill(0)
                self.device.show()
            return True
        except Exception as e:
            logger.error(f"清空显示器失败: {e}")
            return False
    
    def display_text(self, text, x=0, y=0, font_size=12):
        """显示文本"""
        if not self.device:
            return False
        
        try:
            if self.library_used == "luma":
                with canvas(self.device) as draw:
                    try:
                        # 尝试加载中文字体
                        font = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", font_size)
                    except:
                        # 使用默认字体
                        font = ImageFont.load_default()
                    
                    draw.text((x, y), text, font=font, fill=255)
                    
            elif self.library_used == "adafruit":
                image = Image.new('1', (self.width, self.height))
                draw = ImageDraw.Draw(image)
                
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", font_size)
                except:
                    font = ImageFont.load_default()
                
                draw.text((x, y), text, font=font, fill=255)
                self.device.image(image)
                self.device.show()
            
            return True
        except Exception as e:
            logger.error(f"显示文本失败: {e}")
            return False
    
    def display_rectangle(self, x, y, width, height, outline=1, fill=0):
        """显示矩形"""
        if not self.device:
            return False
        
        try:
            if self.library_used == "luma":
                with canvas(self.device) as draw:
                    draw.rectangle([x, y, x + width, y + height], outline=outline, fill=fill)
            elif self.library_used == "adafruit":
                image = Image.new('1', (self.width, self.height))
                draw = ImageDraw.Draw(image)
                draw.rectangle([x, y, x + width, y + height], outline=outline, fill=fill)
                self.device.image(image)
                self.device.show()
            return True
        except Exception as e:
            logger.error(f"显示矩形失败: {e}")
            return False
    
    def display_circle(self, center_x, center_y, radius, outline=1, fill=0):
        """显示圆形"""
        if not self.device:
            return False
        
        try:
            if self.library_used == "luma":
                with canvas(self.device) as draw:
                    draw.ellipse([center_x - radius, center_y - radius, 
                                center_x + radius, center_y + radius], 
                               outline=outline, fill=fill)
            elif self.library_used == "adafruit":
                image = Image.new('1', (self.width, self.height))
                draw = ImageDraw.Draw(image)
                draw.ellipse([center_x - radius, center_y - radius, 
                            center_x + radius, center_y + radius], 
                           outline=outline, fill=fill)
                self.device.image(image)
                self.device.show()
            return True
        except Exception as e:
            logger.error(f"显示圆形失败: {e}")
            return False

def test_basic_functionality(display):
    """测试基本功能"""
    print("\n📋 测试1: 基本功能测试")
    
    # 清空显示器
    print("   清空显示器...")
    if display.clear():
        print("   ✅ 清空成功")
        time.sleep(1)
    else:
        print("   ❌ 清空失败")
        return False
    
    # 显示文本
    print("   显示文本...")
    if display.display_text("Hello SSD1306!", 0, 0):
        print("   ✅ 文本显示成功")
        time.sleep(2)
    else:
        print("   ❌ 文本显示失败")
        return False
    
    # 显示中文
    print("   显示中文...")
    if display.display_text("你好，快快！", 0, 20):
        print("   ✅ 中文显示成功")
        time.sleep(2)
    else:
        print("   ❌ 中文显示失败")
        return False
    
    return True

def test_graphics(display):
    """测试图形显示"""
    print("\n🎨 测试2: 图形显示测试")
    
    # 清空显示器
    display.clear()
    time.sleep(0.5)
    
    # 显示矩形
    print("   显示矩形...")
    if display.display_rectangle(10, 10, 30, 20, outline=1):
        print("   ✅ 矩形显示成功")
        time.sleep(1)
    else:
        print("   ❌ 矩形显示失败")
        return False
    
    # 显示填充矩形
    print("   显示填充矩形...")
    if display.display_rectangle(50, 10, 30, 20, outline=1, fill=1):
        print("   ✅ 填充矩形显示成功")
        time.sleep(1)
    else:
        print("   ❌ 填充矩形显示失败")
        return False
    
    # 显示圆形
    print("   显示圆形...")
    if display.display_circle(30, 50, 10, outline=1):
        print("   ✅ 圆形显示成功")
        time.sleep(1)
    else:
        print("   ❌ 圆形显示失败")
        return False
    
    # 显示填充圆形
    print("   显示填充圆形...")
    if display.display_circle(70, 50, 10, outline=1, fill=1):
        print("   ✅ 填充圆形显示成功")
        time.sleep(2)
    else:
        print("   ❌ 填充圆形显示失败")
        return False
    
    return True

def test_animations(display):
    """测试动画效果"""
    print("\n🎬 测试3: 动画效果测试")
    
    # 滚动文本动画
    print("   滚动文本...")
    text = "快快AI机器人系统"
    for i in range(128, -len(text)*8, -2):
        display.clear()
        display.display_text(text, i, 30)
        time.sleep(0.05)
    
    print("   ✅ 滚动文本完成")
    
    # 弹跳球动画
    print("   弹跳球动画...")
    ball_x, ball_y = 20, 20
    dx, dy = 2, 1
    
    for _ in range(50):
        display.clear()
        display.display_circle(ball_x, ball_y, 5, outline=1, fill=1)
        
        ball_x += dx
        ball_y += dy
        
        # 边界反弹
        if ball_x <= 5 or ball_x >= 123:
            dx = -dx
        if ball_y <= 5 or ball_y >= 59:
            dy = -dy
        
        time.sleep(0.1)
    
    print("   ✅ 弹跳球动画完成")
    return True

def test_real_time_display(display):
    """测试实时显示"""
    print("\n⏰ 测试4: 实时显示测试")
    
    print("   显示实时时间（10秒）...")
    start_time = time.time()
    
    while time.time() - start_time < 10:
        display.clear()
        
        # 显示当前时间
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        display.display_text(f"时间: {current_time}", 0, 0)
        
        # 显示日期
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        display.display_text(f"日期: {current_date}", 0, 20)
        
        # 显示运行状态
        display.display_text("快快系统运行中...", 0, 40)
        
        time.sleep(1)
    
    print("   ✅ 实时显示完成")
    return True

def test_system_info_display(display):
    """测试系统信息显示"""
    print("\n💻 测试5: 系统信息显示")
    
    try:
        import psutil
        
        display.clear()
        
        # 显示CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        display.display_text(f"CPU: {cpu_percent:.1f}%", 0, 0)
        
        # 显示内存使用率
        memory = psutil.virtual_memory()
        display.display_text(f"内存: {memory.percent:.1f}%", 0, 15)
        
        # 显示磁盘使用率
        disk = psutil.disk_usage('/')
        display.display_text(f"磁盘: {disk.percent:.1f}%", 0, 30)
        
        # 显示温度（如果可用）
        try:
            temps = psutil.sensors_temperatures()
            if 'cpu_thermal' in temps:
                temp = temps['cpu_thermal'][0].current
                display.display_text(f"温度: {temp:.1f}°C", 0, 45)
        except:
            display.display_text("温度: N/A", 0, 45)
        
        time.sleep(3)
        print("   ✅ 系统信息显示成功")
        return True
        
    except ImportError:
        print("   ⚠️ 需要安装psutil: pip install psutil")
        return False
    except Exception as e:
        print(f"   ❌ 系统信息显示失败: {e}")
        return False

def check_i2c_devices():
    """检查I2C设备"""
    print("🔍 检查I2C设备...")
    
    try:
        import subprocess
        result = subprocess.run(['i2cdetect', '-y', '1'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("   I2C设备扫描结果:")
            print(result.stdout)
            
            # 检查常见的SSD1306地址
            output = result.stdout
            if '3c' in output.lower():
                print("   ✅ 发现SSD1306设备 (地址: 0x3C)")
                return 0x3C
            elif '3d' in output.lower():
                print("   ✅ 发现SSD1306设备 (地址: 0x3D)")
                return 0x3D
            else:
                print("   ⚠️ 未发现SSD1306设备")
                return None
        else:
            print("   ❌ I2C扫描失败")
            return None
            
    except FileNotFoundError:
        print("   ⚠️ 未找到i2cdetect命令，请安装: sudo apt install i2c-tools")
        return None
    except Exception as e:
        print(f"   ❌ I2C检查失败: {e}")
        return None

def main():
    """主测试函数"""
    print("🖥️ SSD1306 OLED显示模块测试程序")
    print("=" * 50)
    
    # 检查I2C设备
    detected_address = check_i2c_devices()
    
    # 初始化显示器
    if detected_address:
        display = SSD1306Display(i2c_address=detected_address)
    else:
        print("尝试使用默认地址...")
        display = SSD1306Display()
    
    if not display.device:
        print("\n❌ 显示器初始化失败")
        print("\n🔧 排查建议:")
        print("1. 检查硬件连接:")
        print("   - VCC -> 3.3V 或 5V")
        print("   - GND -> GND")
        print("   - SCL -> GPIO 3 (SCL)")
        print("   - SDA -> GPIO 2 (SDA)")
        print("2. 启用I2C: sudo raspi-config -> Interface Options -> I2C")
        print("3. 安装依赖: pip install adafruit-circuitpython-ssd1306 luma.oled")
        print("4. 重启系统后再试")
        return False
    
    print(f"\n✅ 显示器初始化成功 (使用: {display.library_used})")
    
    # 运行测试
    tests = [
        ("基本功能", test_basic_functionality),
        ("图形显示", test_graphics),
        ("动画效果", test_animations),
        ("实时显示", test_real_time_display),
        ("系统信息", test_system_info_display)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func(display):
                passed_tests += 1
        except KeyboardInterrupt:
            print(f"\n⚠️ 用户中断测试")
            break
        except Exception as e:
            print(f"   ❌ 测试异常: {e}")
    
    # 显示最终结果
    display.clear()
    display.display_text("测试完成!", 30, 20)
    display.display_text(f"{passed_tests}/{total_tests} 通过", 25, 40)
    
    print(f"\n🎯 测试结果: {passed_tests}/{total_tests} 通过")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过！SSD1306显示器工作正常")
        print("💡 现在可以集成到AI机器人系统中了")
    else:
        print("⚠️ 部分测试失败，请检查硬件连接和驱动")
    
    time.sleep(3)
    display.clear()
    return passed_tests == total_tests

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 测试被用户中断")
    except Exception as e:
        print(f"\n💥 测试程序异常: {e}")
        import traceback
        traceback.print_exc()