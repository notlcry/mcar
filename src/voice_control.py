#!/usr/bin/python3
"""
语音控制模块 - 通过语音命令控制机器人移动
支持中文语音识别：向前、向后、左转、右转、停止等命令
"""

import speech_recognition as sr
import pyaudio
import threading
import time
import queue
import logging
from LOBOROBOT import LOBOROBOT

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VoiceController:
    def __init__(self, robot=None):
        """
        初始化语音控制器
        Args:
            robot: LOBOROBOT实例，如果为None则创建新实例
        """
        self.robot = robot if robot else LOBOROBOT()
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_listening = False
        self.command_queue = queue.Queue()
        self.default_speed = 50
        self.command_duration = 1.0  # 默认命令持续时间（秒）
        
        # 语音命令映射
        self.command_mapping = {
            # 基本移动命令
            '向前': 'forward',
            '前进': 'forward', 
            '往前': 'forward',
            '前': 'forward',
            
            '向后': 'backward',
            '后退': 'backward',
            '往后': 'backward',
            '后': 'backward',
            
            '左转': 'left',
            '向左': 'left',
            '往左': 'left',
            '左': 'left',
            
            '右转': 'right',
            '向右': 'right',
            '往右': 'right',
            '右': 'right',
            
            '停止': 'stop',
            '停': 'stop',
            '暂停': 'stop',
            
            # 侧移命令
            '左移': 'move_left',
            '向左移动': 'move_left',
            
            '右移': 'move_right',
            '向右移动': 'move_right',
            
            # 速度控制
            '快一点': 'speed_up',
            '快点': 'speed_up',
            '加速': 'speed_up',
            
            '慢一点': 'slow_down',
            '慢点': 'slow_down',
            '减速': 'slow_down',
        }
        
        # 初始化麦克风
        self.init_microphone()
        
    def init_microphone(self):
        """初始化麦克风"""
        try:
            # 检测可用的麦克风设备
            mic_list = sr.Microphone.list_microphone_names()
            logger.info(f"检测到的麦克风设备: {mic_list}")
            
            # 使用默认麦克风
            self.microphone = sr.Microphone()
            
            # 调整环境噪音
            logger.info("正在调整环境噪音...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            logger.info("麦克风初始化完成")
            
        except Exception as e:
            logger.error(f"麦克风初始化失败: {e}")
            self.microphone = None
    
    def listen_continuously(self):
        """持续监听语音命令"""
        if not self.microphone:
            logger.error("麦克风未初始化，无法开始语音识别")
            return
            
        self.is_listening = True
        logger.info("开始语音识别监听...")
        
        # 设置识别器参数
        self.recognizer.energy_threshold = 300  # 降低能量阈值以提高灵敏度
        self.recognizer.pause_threshold = 0.8   # 暂停阈值
        self.recognizer.timeout = 1             # 超时设置
        
        while self.is_listening:
            try:
                with self.microphone as source:
                    logger.debug("正在监听...")
                    # 监听音频，设置超时和短语时间限制
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                
                # 在后台线程中进行识别
                threading.Thread(target=self._process_audio, args=(audio,), daemon=True).start()
                
            except sr.WaitTimeoutError:
                # 超时是正常的，继续监听
                pass
            except Exception as e:
                logger.error(f"监听错误: {e}")
                time.sleep(1)
    
    def _process_audio(self, audio):
        """处理音频数据"""
        try:
            # 使用离线识别（CMU Sphinx）
            text = self.recognizer.recognize_sphinx(audio, language='zh-cn')
            logger.info(f"识别到语音: '{text}'")
            
            # 处理识别到的文本
            self._process_voice_command(text)
            
        except sr.UnknownValueError:
            logger.debug("无法理解音频")
        except sr.RequestError as e:
            logger.error(f"语音识别服务错误: {e}")
        except Exception as e:
            logger.error(f"音频处理错误: {e}")
    
    def _process_voice_command(self, text):
        """处理语音命令"""
        text = text.strip().lower()
        
        # 查找匹配的命令
        command = None
        for voice_cmd, robot_cmd in self.command_mapping.items():
            if voice_cmd in text:
                command = robot_cmd
                break
        
        if command:
            logger.info(f"执行命令: {command}")
            self.command_queue.put(command)
        else:
            logger.debug(f"未识别的命令: '{text}'")
    
    def execute_commands(self):
        """执行命令队列中的命令"""
        while True:
            try:
                # 获取命令，如果队列为空则等待
                command = self.command_queue.get(timeout=1)
                self._execute_robot_command(command)
                self.command_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"命令执行错误: {e}")
    
    def _execute_robot_command(self, command):
        """执行具体的机器人命令"""
        try:
            if command == 'forward':
                self.robot.t_up(self.default_speed, self.command_duration)
                
            elif command == 'backward':
                self.robot.t_down(self.default_speed, self.command_duration)
                
            elif command == 'left':
                self.robot.turnLeft(self.default_speed, self.command_duration)
                
            elif command == 'right':
                self.robot.turnRight(self.default_speed, self.command_duration)
                
            elif command == 'move_left':
                self.robot.moveLeft(self.default_speed, self.command_duration)
                
            elif command == 'move_right':
                self.robot.moveRight(self.default_speed, self.command_duration)
                
            elif command == 'stop':
                self.robot.t_stop(0)
                
            elif command == 'speed_up':
                self.default_speed = min(100, self.default_speed + 10)
                logger.info(f"速度调整为: {self.default_speed}")
                
            elif command == 'slow_down':
                self.default_speed = max(10, self.default_speed - 10)
                logger.info(f"速度调整为: {self.default_speed}")
                
            logger.info(f"命令 '{command}' 执行完成")
            
        except Exception as e:
            logger.error(f"机器人命令执行失败: {e}")
    
    def start(self):
        """启动语音控制"""
        if not self.microphone:
            logger.error("麦克风未就绪，无法启动语音控制")
            return False
            
        logger.info("启动语音控制系统...")
        
        # 启动命令执行线程
        command_thread = threading.Thread(target=self.execute_commands, daemon=True)
        command_thread.start()
        
        # 启动语音监听线程
        listen_thread = threading.Thread(target=self.listen_continuously, daemon=True)
        listen_thread.start()
        
        logger.info("语音控制系统已启动")
        return True
    
    def stop(self):
        """停止语音控制"""
        logger.info("停止语音控制系统...")
        self.is_listening = False
        
        # 停止机器人
        self.robot.t_stop(0)
    
    def set_speed(self, speed):
        """设置默认速度"""
        if 0 <= speed <= 100:
            self.default_speed = speed
            logger.info(f"默认速度设置为: {speed}")
        else:
            logger.warning(f"无效的速度值: {speed}")
    
    def set_duration(self, duration):
        """设置命令持续时间"""
        if duration > 0:
            self.command_duration = duration
            logger.info(f"命令持续时间设置为: {duration}秒")
        else:
            logger.warning(f"无效的持续时间: {duration}")


def main():
    """主函数 - 独立运行语音控制"""
    print("====== 语音控制系统 ======")
    print("支持的命令:")
    print("- 移动: 向前/前进, 向后/后退, 左转, 右转")
    print("- 侧移: 左移, 右移") 
    print("- 控制: 停止, 快一点, 慢一点")
    print("- 按 Ctrl+C 退出")
    print("=" * 30)
    
    # 创建语音控制器
    voice_controller = VoiceController()
    
    try:
        # 启动语音控制
        if voice_controller.start():
            # 保持程序运行
            while True:
                time.sleep(1)
        else:
            print("语音控制启动失败")
            
    except KeyboardInterrupt:
        print("\n正在退出...")
        voice_controller.stop()
        print("语音控制系统已停止")

if __name__ == "__main__":
    main() 