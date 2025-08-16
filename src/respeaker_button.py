#!/usr/bin/python3
"""
ReSpeaker板载按钮控制模块
ReSpeaker 2-Mics Pi HAT的按钮通常连接到GPIO17
"""

import RPi.GPIO as GPIO
import threading
import time
import logging
from typing import Callable, Optional

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ReSpeakerButton:
    """ReSpeaker板载按钮控制器"""
    
    def __init__(self, button_pin=17, debounce_time=0.2):
        """
        初始化ReSpeaker按钮
        Args:
            button_pin: 按钮GPIO引脚 (默认17)
            debounce_time: 防抖时间 (秒)
        """
        self.button_pin = button_pin
        self.debounce_time = debounce_time
        self.last_press_time = 0
        self.is_listening = False
        self.press_callback = None
        
        # 初始化GPIO
        self._setup_gpio()
        
    def _setup_gpio(self):
        """设置GPIO配置"""
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            
            # 设置按钮引脚为输入，启用内部上拉电阻
            GPIO.setup(self.button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            logger.info(f"🔘 ReSpeaker按钮已配置 (GPIO{self.button_pin})")
            return True
            
        except Exception as e:
            logger.error(f"GPIO设置失败: {e}")
            return False
    
    def set_callback(self, callback: Callable[[], None]):
        """
        设置按钮按下时的回调函数
        Args:
            callback: 按钮按下时调用的函数
        """
        self.press_callback = callback
        logger.info("🔘 按钮回调函数已设置")
    
    def start_listening(self):
        """开始监听按钮按下事件"""
        if self.is_listening:
            logger.warning("按钮监听已经在运行")
            return False
        
        try:
            # 使用GPIO事件检测（下降沿，按钮按下）
            GPIO.add_event_detect(
                self.button_pin, 
                GPIO.FALLING, 
                callback=self._button_pressed, 
                bouncetime=int(self.debounce_time * 1000)  # 毫秒
            )
            
            self.is_listening = True
            logger.info("🔘 ReSpeaker按钮监听已启动")
            return True
            
        except Exception as e:
            logger.error(f"按钮监听启动失败: {e}")
            return False
    
    def stop_listening(self):
        """停止监听按钮按下事件"""
        if not self.is_listening:
            return
        
        try:
            GPIO.remove_event_detect(self.button_pin)
            self.is_listening = False
            logger.info("🔘 ReSpeaker按钮监听已停止")
            
        except Exception as e:
            logger.error(f"停止按钮监听失败: {e}")
    
    def _button_pressed(self, channel):
        """按钮按下事件处理"""
        current_time = time.time()
        
        # 防抖处理
        if current_time - self.last_press_time < self.debounce_time:
            return
        
        self.last_press_time = current_time
        
        logger.info("🔘 检测到ReSpeaker按钮按下")
        
        # 调用回调函数
        if self.press_callback:
            try:
                # 在新线程中执行回调，避免阻塞GPIO事件
                threading.Thread(
                    target=self.press_callback, 
                    daemon=True
                ).start()
            except Exception as e:
                logger.error(f"按钮回调执行失败: {e}")
    
    def test_button(self, duration=10):
        """
        测试按钮功能
        Args:
            duration: 测试持续时间（秒）
        """
        print(f"🔘 ReSpeaker按钮测试开始 ({duration}秒)")
        print("💡 请按下ReSpeaker板载按钮进行测试")
        
        def test_callback():
            print("✅ 按钮按下检测成功！")
        
        self.set_callback(test_callback)
        
        if self.start_listening():
            try:
                time.sleep(duration)
            except KeyboardInterrupt:
                print("\n测试被用户中断")
            finally:
                self.stop_listening()
                print("🔘 按钮测试结束")
        else:
            print("❌ 按钮测试启动失败")
    
    def cleanup(self):
        """清理GPIO资源"""
        try:
            self.stop_listening()
            # 注意：不要调用GPIO.cleanup()，因为其他模块可能还在使用GPIO
            logger.info("🔘 按钮控制器已清理")
        except Exception as e:
            logger.error(f"按钮清理失败: {e}")
    
    def __del__(self):
        """析构函数"""
        try:
            self.cleanup()
        except:
            pass

def test_respeaker_button():
    """测试ReSpeaker按钮功能"""
    print("🤖 ReSpeaker按钮测试程序")
    print("=" * 30)
    
    # 测试不同的可能引脚（扩展范围）
    possible_pins = [2, 3, 4, 5, 6, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
    
    for pin in possible_pins:
        print(f"\n🔍 测试GPIO{pin}...")
        
        try:
            button = ReSpeakerButton(button_pin=pin)
            
            # 短时间测试
            print(f"💡 请按下按钮测试GPIO{pin} (5秒)")
            
            button_pressed = False
            
            def test_callback():
                nonlocal button_pressed
                button_pressed = True
                print(f"✅ GPIO{pin} 按钮响应正常！")
            
            button.set_callback(test_callback)
            
            if button.start_listening():
                start_time = time.time()
                while time.time() - start_time < 5:
                    if button_pressed:
                        print(f"🎉 找到ReSpeaker按钮: GPIO{pin}")
                        button.cleanup()
                        return pin
                    time.sleep(0.1)
                
                button.cleanup()
                print(f"⏳ GPIO{pin} 超时，无按钮响应")
            else:
                print(f"❌ GPIO{pin} 初始化失败")
                
        except Exception as e:
            print(f"❌ GPIO{pin} 测试错误: {e}")
    
    print("\n❌ 未找到可用的ReSpeaker按钮")
    return None

if __name__ == "__main__":
    # 首先尝试自动检测按钮
    detected_pin = test_respeaker_button()
    
    if detected_pin:
        print(f"\n🔘 使用检测到的按钮 GPIO{detected_pin} 进行完整测试")
        button = ReSpeakerButton(button_pin=detected_pin)
        button.test_button(15)
    else:
        print("\n🔘 使用默认GPIO17进行测试")
        button = ReSpeakerButton()
        button.test_button(15)