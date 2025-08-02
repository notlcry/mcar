#!/usr/bin/python3
"""
SSD1306显示控制器 - AI机器人表情和状态显示
集成到语音对话系统，显示AI状态、表情和交互信息
"""

import time
import threading
import queue
import logging
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass
from typing import Optional, Dict, List
import json
import os

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 尝试导入显示器库
try:
    from luma.core.interface.serial import i2c
    from luma.core.render import canvas
    from luma.oled.device import ssd1306
    LUMA_AVAILABLE = True
except ImportError:
    LUMA_AVAILABLE = False

try:
    import board
    import adafruit_ssd1306
    ADAFRUIT_AVAILABLE = True
except ImportError:
    ADAFRUIT_AVAILABLE = False

@dataclass
class DisplayMessage:
    """显示消息数据类"""
    message_type: str  # status, emotion, text, animation
    content: str
    duration: float = 3.0
    priority: int = 1  # 1=低, 2=中, 3=高
    extra_data: Dict = None

class DisplayController:
    """显示控制器 - 管理OLED显示器的所有输出"""
    
    def __init__(self, width=128, height=64, i2c_address=0x3C):
        """
        初始化显示控制器
        Args:
            width: 显示器宽度
            height: 显示器高度  
            i2c_address: I2C地址
        """
        self.width = width
        self.height = height
        self.i2c_address = i2c_address
        
        # 显示器设备
        self.device = None
        self.library_used = None
        
        # 消息队列和控制
        self.message_queue = queue.PriorityQueue()
        self.current_message = None
        self.display_lock = threading.Lock()
        
        # 显示状态
        self.is_active = False
        self.display_thread = None
        
        # 字体配置
        self.fonts = self._load_fonts()
        
        # 表情和图标
        self.expressions = self._init_expressions()
        
        # 初始化显示器
        self._initialize_display()
    
    def _initialize_display(self):
        """初始化显示器"""
        logger.info("🖥️ 初始化SSD1306显示器...")
        
        # 尝试Luma OLED库
        if LUMA_AVAILABLE:
            try:
                interface = i2c(port=1, address=self.i2c_address)
                self.device = ssd1306(interface, width=self.width, height=self.height)
                self.library_used = "luma"
                logger.info("✅ 使用Luma OLED库初始化成功")
                return True
            except Exception as e:
                logger.warning(f"Luma OLED库初始化失败: {e}")
        
        # 尝试Adafruit库
        if ADAFRUIT_AVAILABLE:
            try:
                i2c_bus = board.I2C()
                self.device = adafruit_ssd1306.SSD1306_I2C(
                    self.width, self.height, i2c_bus, addr=self.i2c_address
                )
                self.library_used = "adafruit"
                logger.info("✅ 使用Adafruit库初始化成功")
                return True
            except Exception as e:
                logger.warning(f"Adafruit库初始化失败: {e}")
        
        logger.error("❌ 显示器初始化失败")
        return False
    
    def _load_fonts(self):
        """加载字体"""
        fonts = {}
        
        # 尝试加载不同大小的中文字体
        font_paths = [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/PingFang.ttc",  # macOS
        ]
        
        for size in [8, 10, 12, 14, 16]:
            fonts[f"size_{size}"] = None
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        fonts[f"size_{size}"] = ImageFont.truetype(font_path, size)
                        break
                    except:
                        continue
            
            # 如果没找到字体，使用默认字体
            if fonts[f"size_{size}"] is None:
                fonts[f"size_{size}"] = ImageFont.load_default()
        
        logger.info(f"✅ 字体加载完成")
        return fonts
    
    def _init_expressions(self):
        """初始化表情图标"""
        expressions = {
            'happy': self._create_happy_face,
            'sad': self._create_sad_face,
            'thinking': self._create_thinking_face,
            'confused': self._create_confused_face,
            'excited': self._create_excited_face,
            'sleeping': self._create_sleeping_face,
            'listening': self._create_listening_animation,
            'speaking': self._create_speaking_animation
        }
        return expressions
    
    def start(self):
        """启动显示控制器"""
        if not self.device:
            logger.error("显示器未初始化，无法启动")
            return False
        
        self.is_active = True
        self.display_thread = threading.Thread(target=self._display_worker, daemon=True)
        self.display_thread.start()
        
        # 显示启动画面
        self.show_startup_screen()
        
        logger.info("🚀 显示控制器已启动")
        return True
    
    def stop(self):
        """停止显示控制器"""
        self.is_active = False
        if self.display_thread:
            self.display_thread.join(timeout=2)
        
        # 清空显示器
        self.clear()
        logger.info("🛑 显示控制器已停止")
    
    def _display_worker(self):
        """显示工作线程"""
        while self.is_active:
            try:
                # 获取消息（按优先级排序）
                try:
                    priority, timestamp, message = self.message_queue.get(timeout=0.1)
                    self._process_message(message)
                    self.message_queue.task_done()
                except queue.Empty:
                    # 如果没有消息，显示默认状态
                    self._show_idle_status()
                    time.sleep(1)
                
            except Exception as e:
                logger.error(f"显示工作线程错误: {e}")
                time.sleep(1)
    
    def _process_message(self, message: DisplayMessage):
        """处理显示消息"""
        with self.display_lock:
            self.current_message = message
            
            if message.message_type == "status":
                self._show_status(message.content)
            elif message.message_type == "emotion":
                self._show_emotion(message.content)
            elif message.message_type == "text":
                self._show_text(message.content)
            elif message.message_type == "animation":
                self._show_animation(message.content, message.extra_data)
            elif message.message_type == "user_speech":
                self._show_user_speech(message.content)
            elif message.message_type == "ai_response":
                self._show_ai_response(message.content)
            
            # 显示指定时长
            if message.duration > 0:
                time.sleep(message.duration)
    
    def clear(self):
        """清空显示器"""
        if not self.device:
            return
        
        try:
            if self.library_used == "luma":
                with canvas(self.device) as draw:
                    draw.rectangle(self.device.bounding_box, outline=0, fill=0)
            elif self.library_used == "adafruit":
                self.device.fill(0)
                self.device.show()
        except Exception as e:
            logger.error(f"清空显示器失败: {e}")
    
    def _draw_with_canvas(self, draw_func):
        """使用画布绘制"""
        if not self.device:
            return
        
        try:
            if self.library_used == "luma":
                with canvas(self.device) as draw:
                    draw_func(draw)
            elif self.library_used == "adafruit":
                image = Image.new('1', (self.width, self.height))
                draw = ImageDraw.Draw(image)
                draw_func(draw)
                self.device.image(image)
                self.device.show()
        except Exception as e:
            logger.error(f"绘制失败: {e}")
    
    # ================== 表情绘制函数 ==================
    
    def _create_happy_face(self, draw):
        """绘制开心表情"""
        # 脸部轮廓
        draw.ellipse([30, 10, 98, 78], outline=1, fill=0)
        
        # 眼睛
        draw.ellipse([45, 25, 55, 35], outline=1, fill=1)  # 左眼
        draw.ellipse([73, 25, 83, 35], outline=1, fill=1)  # 右眼
        
        # 笑脸嘴巴
        draw.arc([45, 45, 83, 65], start=0, end=180, fill=1, width=2)
        
        # 腮红
        draw.ellipse([35, 40, 43, 48], outline=1, fill=0)
        draw.ellipse([85, 40, 93, 48], outline=1, fill=0)
    
    def _create_sad_face(self, draw):
        """绘制悲伤表情"""
        # 脸部轮廓
        draw.ellipse([30, 10, 98, 78], outline=1, fill=0)
        
        # 眼睛 (小一点)
        draw.ellipse([47, 27, 53, 33], outline=1, fill=1)
        draw.ellipse([75, 27, 81, 33], outline=1, fill=1)
        
        # 眼泪
        draw.ellipse([45, 35, 47, 42], outline=1, fill=1)
        draw.ellipse([81, 35, 83, 42], outline=1, fill=1)
        
        # 悲伤嘴巴
        draw.arc([45, 55, 83, 70], start=180, end=360, fill=1, width=2)
    
    def _create_thinking_face(self, draw):
        """绘制思考表情"""
        # 脸部轮廓
        draw.ellipse([30, 10, 98, 78], outline=1, fill=0)
        
        # 眼睛 (向上看)
        draw.ellipse([45, 22, 55, 30], outline=1, fill=1)
        draw.ellipse([73, 22, 83, 30], outline=1, fill=1)
        
        # 思考的嘴巴
        draw.ellipse([60, 50, 68, 58], outline=1, fill=0)
        
        # 思考泡泡
        draw.ellipse([85, 5, 95, 15], outline=1, fill=0)
        draw.ellipse([95, 0, 105, 10], outline=1, fill=0)
        draw.ellipse([105, -5, 120, 10], outline=1, fill=0)
    
    def _create_confused_face(self, draw):
        """绘制困惑表情"""
        # 脸部轮廓
        draw.ellipse([30, 10, 98, 78], outline=1, fill=0)
        
        # 眼睛 (不对称)
        draw.ellipse([45, 25, 55, 35], outline=1, fill=1)
        draw.ellipse([73, 22, 83, 32], outline=1, fill=1)
        
        # 困惑的嘴巴 (波浪线)
        draw.line([(45, 55), (50, 50), (55, 55), (60, 50), (65, 55), (70, 50), (75, 55), (80, 50), (83, 55)], fill=1, width=2)
        
        # 问号
        draw.text((100, 15), "?", font=self.fonts['size_14'], fill=1)
    
    def _create_excited_face(self, draw):
        """绘制兴奋表情"""
        # 脸部轮廓
        draw.ellipse([30, 10, 98, 78], outline=1, fill=0)
        
        # 星星眼睛
        self._draw_star(draw, 50, 30, 5)
        self._draw_star(draw, 78, 30, 5)
        
        # 大笑嘴巴
        draw.ellipse([50, 45, 78, 65], outline=1, fill=1)
        draw.ellipse([52, 47, 76, 63], outline=1, fill=0)
        
        # 兴奋线条
        draw.line([(25, 20), (20, 15)], fill=1, width=2)
        draw.line([(25, 35), (20, 40)], fill=1, width=2)
        draw.line([(103, 20), (108, 15)], fill=1, width=2)
        draw.line([(103, 35), (108, 40)], fill=1, width=2)
    
    def _create_sleeping_face(self, draw):
        """绘制睡觉表情"""
        # 脸部轮廓
        draw.ellipse([30, 10, 98, 78], outline=1, fill=0)
        
        # 闭眼
        draw.line([(45, 30), (55, 30)], fill=1, width=3)
        draw.line([(73, 30), (83, 30)], fill=1, width=3)
        
        # 安静的嘴巴
        draw.ellipse([60, 52, 68, 58], outline=1, fill=1)
        
        # ZZZ
        draw.text((100, 10), "Z", font=self.fonts['size_12'], fill=1)
        draw.text((105, 5), "z", font=self.fonts['size_10'], fill=1)
        draw.text((108, 0), "z", font=self.fonts['size_8'], fill=1)
    
    def _draw_star(self, draw, cx, cy, size):
        """绘制星星"""
        points = []
        for i in range(10):
            angle = i * 36 * 3.14159 / 180
            if i % 2 == 0:
                r = size
            else:
                r = size * 0.5
            
            x = cx + r * (angle ** 0.5)  # 简化的星形
            y = cy + r * (angle ** 0.3)
            points.append((x, y))
        
        # 简化为几条线
        draw.line([(cx-size, cy), (cx+size, cy)], fill=1, width=1)
        draw.line([(cx, cy-size), (cx, cy+size)], fill=1, width=1)
        draw.line([(cx-size*0.7, cy-size*0.7), (cx+size*0.7, cy+size*0.7)], fill=1, width=1)
        draw.line([(cx-size*0.7, cy+size*0.7), (cx+size*0.7, cy-size*0.7)], fill=1, width=1)
    
    def _create_listening_animation(self, draw):
        """绘制监听动画"""
        # 简单的脸部
        draw.ellipse([30, 10, 98, 78], outline=1, fill=0)
        draw.ellipse([45, 25, 55, 35], outline=1, fill=1)
        draw.ellipse([73, 25, 83, 35], outline=1, fill=1)
        draw.ellipse([60, 52, 68, 58], outline=1, fill=0)
        
        # 声波动画 (简化)
        import math
        t = time.time()
        for i in range(3):
            r = 40 + i * 10 + int(10 * math.sin(t * 3 + i))
            draw.ellipse([64-r//2, 44-r//2, 64+r//2, 44+r//2], outline=1, fill=0)
    
    def _create_speaking_animation(self, draw):
        """绘制说话动画"""
        # 脸部
        draw.ellipse([30, 10, 98, 78], outline=1, fill=0)
        draw.ellipse([45, 25, 55, 35], outline=1, fill=1)
        draw.ellipse([73, 25, 83, 35], outline=1, fill=1)
        
        # 动态嘴巴
        import math
        t = time.time()
        mouth_height = int(5 + 3 * math.sin(t * 8))
        draw.ellipse([55, 50, 73, 50 + mouth_height], outline=1, fill=1)
        
        # 声音符号
        draw.text((100, 40), "♪", font=self.fonts['size_14'], fill=1)
    
    # ================== 显示功能函数 ==================
    
    def show_startup_screen(self):
        """显示启动画面"""
        def draw_startup(draw):
            # 标题
            draw.text((25, 5), "快快 AI 机器人", font=self.fonts['size_12'], fill=1)
            
            # 版本信息
            draw.text((35, 25), "系统启动中...", font=self.fonts['size_10'], fill=1)
            
            # 进度条
            draw.rectangle([20, 45, 108, 55], outline=1, fill=0)
            
            # 动态进度
            for i in range(0, 88, 8):
                draw.rectangle([20, 45, 20 + i, 55], outline=0, fill=1)
                time.sleep(0.1)
        
        self._draw_with_canvas(draw_startup)
        time.sleep(1)
    
    def _show_status(self, status):
        """显示系统状态"""
        def draw_status(draw):
            draw.text((10, 5), f"状态: {status}", font=self.fonts['size_10'], fill=1)
            draw.text((10, 20), f"时间: {datetime.now().strftime('%H:%M:%S')}", 
                     font=self.fonts['size_8'], fill=1)
            
            # 状态指示器
            if status == "等待中":
                draw.ellipse([100, 5, 110, 15], outline=1, fill=0)
            elif status == "监听中":
                draw.ellipse([100, 5, 110, 15], outline=1, fill=1)
            elif status == "思考中":
                self._draw_thinking_indicator(draw, 105, 10)
        
        self._draw_with_canvas(draw_status)
    
    def _show_emotion(self, emotion):
        """显示表情"""
        if emotion in self.expressions:
            self._draw_with_canvas(self.expressions[emotion])
        else:
            # 默认表情
            self._draw_with_canvas(self._create_happy_face)
    
    def _show_text(self, text):
        """显示文本"""
        def draw_text(draw):
            lines = self._wrap_text(text, 16)  # 每行约16个字符
            y_offset = 5
            
            for line in lines[:4]:  # 最多4行
                draw.text((2, y_offset), line, font=self.fonts['size_10'], fill=1)
                y_offset += 15
        
        self._draw_with_canvas(draw_text)
    
    def _show_user_speech(self, text):
        """显示用户语音"""
        def draw_user_speech(draw):
            # 用户图标
            draw.text((2, 2), "用户:", font=self.fonts['size_10'], fill=1)
            
            # 语音文本
            lines = self._wrap_text(text, 14)
            y_offset = 18
            
            for line in lines[:3]:
                draw.text((2, y_offset), line, font=self.fonts['size_10'], fill=1)
                y_offset += 15
            
            # 监听图标
            draw.ellipse([110, 2, 125, 17], outline=1, fill=0)
            draw.text((113, 4), "♪", font=self.fonts['size_8'], fill=1)
        
        self._draw_with_canvas(draw_user_speech)
    
    def _show_ai_response(self, text):
        """显示AI回复"""
        def draw_ai_response(draw):
            # AI图标
            draw.text((2, 2), "快快:", font=self.fonts['size_10'], fill=1)
            
            # 回复文本
            lines = self._wrap_text(text, 14)
            y_offset = 18
            
            for line in lines[:3]:
                draw.text((2, y_offset), line, font=self.fonts['size_10'], fill=1)
                y_offset += 15
            
            # 说话图标
            draw.ellipse([110, 2, 125, 17], outline=1, fill=1)
        
        self._draw_with_canvas(draw_ai_response)
    
    def _show_animation(self, animation_type, extra_data=None):
        """显示动画"""
        if animation_type == "listening":
            for _ in range(10):
                self._draw_with_canvas(self._create_listening_animation)
                time.sleep(0.2)
        elif animation_type == "speaking":
            duration = extra_data.get('duration', 3) if extra_data else 3
            end_time = time.time() + duration
            while time.time() < end_time:
                self._draw_with_canvas(self._create_speaking_animation)
                time.sleep(0.2)
    
    def _show_idle_status(self):
        """显示空闲状态"""
        def draw_idle(draw):
            # 简单的时钟显示
            current_time = datetime.now().strftime("%H:%M")
            draw.text((45, 25), current_time, font=self.fonts['size_16'], fill=1)
            draw.text((35, 45), "快快待机中", font=self.fonts['size_10'], fill=1)
        
        self._draw_with_canvas(draw_idle)
    
    def _wrap_text(self, text, max_chars):
        """文本换行"""
        lines = []
        current_line = ""
        
        for char in text:
            if len(current_line) >= max_chars:
                lines.append(current_line)
                current_line = char
            else:
                current_line += char
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def _draw_thinking_indicator(self, draw, x, y):
        """绘制思考指示器"""
        import math
        t = time.time()
        for i in range(3):
            offset = int(2 * math.sin(t * 2 + i * 0.5))
            draw.ellipse([x + i * 6, y + offset, x + i * 6 + 3, y + offset + 3], 
                        outline=1, fill=1)
    
    # ================== 公共接口函数 ==================
    
    def add_message(self, message_type: str, content: str, 
                   duration: float = 3.0, priority: int = 1, extra_data: Dict = None):
        """添加显示消息"""
        message = DisplayMessage(
            message_type=message_type,
            content=content,
            duration=duration,
            priority=priority,
            extra_data=extra_data or {}
        )
        
        # 使用负优先级以实现高优先级先处理
        timestamp = time.time()
        self.message_queue.put((-priority, timestamp, message))
    
    def show_system_status(self, status: str, duration: float = 2.0):
        """显示系统状态"""
        self.add_message("status", status, duration, priority=2)
    
    def show_emotion(self, emotion: str, duration: float = 3.0):
        """显示表情"""
        self.add_message("emotion", emotion, duration, priority=1)
    
    def show_user_speech(self, text: str, duration: float = 3.0):
        """显示用户语音"""
        self.add_message("user_speech", text, duration, priority=2)
    
    def show_ai_response(self, text: str, duration: float = 5.0):
        """显示AI回复"""
        self.add_message("ai_response", text, duration, priority=2)
    
    def show_listening_animation(self, duration: float = 3.0):
        """显示监听动画"""
        self.add_message("animation", "listening", duration, priority=3)
    
    def show_speaking_animation(self, duration: float = 3.0):
        """显示说话动画"""
        extra_data = {"duration": duration}
        self.add_message("animation", "speaking", duration, priority=3, extra_data=extra_data)
    
    def is_available(self):
        """检查显示器是否可用"""
        return self.device is not None

# 测试函数
def test_display_controller():
    """测试显示控制器"""
    print("🧪 测试显示控制器...")
    
    controller = DisplayController()
    
    if not controller.is_available():
        print("❌ 显示器不可用")
        return False
    
    # 启动控制器
    controller.start()
    
    try:
        # 测试各种显示
        print("测试系统状态...")
        controller.show_system_status("系统启动")
        time.sleep(3)
        
        print("测试表情...")
        emotions = ['happy', 'sad', 'thinking', 'excited']
        for emotion in emotions:
            controller.show_emotion(emotion)
            time.sleep(2)
        
        print("测试用户语音显示...")
        controller.show_user_speech("你好快快，今天天气怎么样？")
        time.sleep(3)
        
        print("测试AI回复显示...")
        controller.show_ai_response("今天天气很好呢！快快很开心~")
        time.sleep(3)
        
        print("测试监听动画...")
        controller.show_listening_animation(3)
        
        print("测试说话动画...")
        controller.show_speaking_animation(3)
        
        print("✅ 所有测试完成")
        
    finally:
        controller.stop()
    
    return True

if __name__ == "__main__":
    test_display_controller()