#!/usr/bin/python3
"""
机器人语音Web控制系统 - 集成语音控制和Web控制
支持通过Web界面和语音命令双重控制机器人
"""

from flask import Flask, render_template, request, jsonify, Response
from markupsafe import escape
from LOBOROBOT import LOBOROBOT
from voice_control import VoiceController
import RPi.GPIO as GPIO
import threading
import time
import os
import cv2
import numpy as np
import io
from picamera import PiCamera
from picamera.array import PiRGBArray
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
clbrobot = LOBOROBOT()  # 实例化机器人对象

# 传感器引脚定义
SensorRight = 16  # 右侧红外避障传感器
SensorLeft = 12   # 左侧红外避障传感器
TRIG = 20         # 超声波触发引脚
ECHO = 21         # 超声波回声引脚

# 全局变量用于控制机器人状态
robot_speed = 50
robot_running = False
last_command = "stop"
last_command_time = 0
auto_obstacle_avoidance = False  # 是否启用自动避障
voice_control_enabled = False    # 是否启用语音控制
voice_controller = None          # 语音控制器实例

sensor_data = {
    "left_ir": False,  # 左侧红外状态，False表示无障碍，True表示有障碍
    "right_ir": False, # 右侧红外状态
    "ultrasonic": 100, # 超声波测距，厘米
    "last_update": 0   # 最后更新时间
}

# 摄像头设置
camera = None
picam = None
camera_enabled = True
camera_resolution = (320, 240)  # 降低分辨率
camera_type = "unknown"  # "picamera" 或 "webcam"

def setup_sensors():
    """初始化传感器"""
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    
    # 设置红外传感器引脚
    GPIO.setup(SensorRight, GPIO.IN)
    GPIO.setup(SensorLeft, GPIO.IN)
    
    # 设置超声波传感器引脚
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)
    
    print("传感器初始化完成")

def ultrasonic_distance():
    """测量超声波距离"""
    GPIO.output(TRIG, 0)
    time.sleep(0.000002)
    
    GPIO.output(TRIG, 1)
    time.sleep(0.00001)
    GPIO.output(TRIG, 0)
    
    start_time = time.time()
    timeout = start_time + 0.05  # 50ms超时
    
    # 等待回波开始
    while GPIO.input(ECHO) == 0:
        if time.time() > timeout:
            return 999  # 超时返回
        pass
    
    time1 = time.time()
    
    # 等待回波结束
    while GPIO.input(ECHO) == 1:
        if time.time() > timeout:
            return 999  # 超时返回
        pass
    
    time2 = time.time()
    
    # 计算距离
    distance = round((time2 - time1) * 340 / 2 * 100)
    return distance

def read_sensors():
    """读取所有传感器数据"""
    global sensor_data
    
    try:
        # 读取红外传感器
        left_status = not GPIO.input(SensorLeft)   # 低电平表示有障碍
        right_status = not GPIO.input(SensorRight) # 低电平表示有障碍
        
        # 读取超声波传感器
        distance = ultrasonic_distance()
        
        # 更新传感器数据
        sensor_data = {
            "left_ir": left_status,
            "right_ir": right_status,
            "ultrasonic": distance,
            "last_update": time.time()
        }
        
        return sensor_data
    except Exception as e:
        print(f"读取传感器错误: {str(e)}")
        return sensor_data

def execute_robot_command(command, duration=0):
    """执行机器人命令的通用函数"""
    global last_command, last_command_time, robot_speed
    
    last_command = command
    last_command_time = time.time()
    
    if duration == 0:
        duration = 0 if command == 'stop' else 0.1  # 默认短时间执行
    
    if command == 'forward':
        clbrobot.t_up(robot_speed, duration)
    elif command == 'backward':
        clbrobot.t_down(robot_speed, duration)
    elif command == 'left':
        clbrobot.turnLeft(robot_speed, duration)
    elif command == 'right':
        clbrobot.turnRight(robot_speed, duration)
    elif command == 'move_left':
        clbrobot.moveLeft(robot_speed, duration)
    elif command == 'move_right':
        clbrobot.moveRight(robot_speed, duration)
    elif command == 'forward_left':
        clbrobot.forward_Left(robot_speed, duration)
    elif command == 'forward_right':
        clbrobot.forward_Right(robot_speed, duration)
    elif command == 'backward_left':
        clbrobot.backward_Left(robot_speed, duration)
    elif command == 'backward_right':
        clbrobot.backward_Right(robot_speed, duration)
    elif command == 'stop':
        clbrobot.t_stop(0)
    
    logger.info(f"执行命令: {command}, 速度: {robot_speed}, 持续时间: {duration}")

def sensor_monitor_thread():
    """传感器监控线程"""
    while True:
        try:
            read_sensors()  # 更新传感器数据
            
            # 如果启用了自动避障
            if auto_obstacle_avoidance and last_command != "stop":
                obstacle_avoidance()
                
            time.sleep(0.1)  # 100ms更新一次
        except Exception as e:
            print(f"传感器监控错误: {str(e)}")
            time.sleep(0.5)

def obstacle_avoidance():
    """自动避障算法"""
    global last_command
    
    # 读取传感器数据
    left_ir = sensor_data["left_ir"]
    right_ir = sensor_data["right_ir"]
    distance = sensor_data["ultrasonic"]
    
    # 避障逻辑
    if distance < 30 or left_ir or right_ir:
        # 有障碍物
        if distance < 30:
            # 超声波检测到前方障碍物
            clbrobot.t_stop(0.1)
            clbrobot.t_down(40, 0.5)  # 后退
            
            if left_ir:
                clbrobot.turnRight(40, 0.5)  # 右转
            elif right_ir:
                clbrobot.turnLeft(40, 0.5)  # 左转
            else:
                clbrobot.turnRight(40, 0.7)  # 默认右转
                
            last_command = "obstacle_avoiding"
            
        elif left_ir and not right_ir:
            # 左侧有障碍
            clbrobot.turnRight(40, 0.3)
            last_command = "obstacle_avoiding"
            
        elif right_ir and not left_ir:
            # 右侧有障碍
            clbrobot.turnLeft(40, 0.3)
            last_command = "obstacle_avoiding"
            
        elif left_ir and right_ir:
            # 两侧都有障碍
            clbrobot.t_down(40, 0.5)
            clbrobot.turnRight(40, 0.7)
            last_command = "obstacle_avoiding"

def initialize_camera():
    global camera, picam, camera_type
    
    # 首先尝试使用PiCamera
    try:
        print("尝试初始化树莓派官方摄像头(PiCamera)...")
        picam = PiCamera()
        picam.resolution = camera_resolution
        picam.framerate = 15  # 降低帧率
        picam.vflip = True  # 垂直翻转图像
        picam.hflip = True  # 水平翻转图像
        # 给摄像头更多的初始化时间
        time.sleep(2)
        camera_type = "picamera"
        print(f"树莓派官方摄像头初始化成功，分辨率: {camera_resolution[0]}x{camera_resolution[1]}")
        return True
    except Exception as e:
        print(f"树莓派官方摄像头初始化失败: {str(e)}")
        if picam:
            picam.close()
            picam = None
            
    # 如果PiCamera失败，尝试普通USB摄像头
    try:
        print("尝试初始化普通USB摄像头...")
        camera = cv2.VideoCapture(0)
        
        if not camera.isOpened():
            print("无法打开USB摄像头")
            return False
            
        # 设置摄像头属性
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, camera_resolution[0])
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_resolution[1])
        camera.set(cv2.CAP_PROP_FPS, 15)
        
        camera_type = "webcam"
        print(f"USB摄像头初始化成功，分辨率: {camera_resolution[0]}x{camera_resolution[1]}")
        return True
        
    except Exception as e:
        print(f"USB摄像头初始化失败: {str(e)}")
        if camera:
            camera.release()
            camera = None
        return False

def generate_frames():
    """生成视频流帧"""
    global camera, picam, camera_type, camera_enabled
    
    while True:
        try:
            if not camera_enabled:
                time.sleep(0.1)
                continue
                
            frame = None
            
            if camera_type == "picamera" and picam:
                # 使用PiCamera
                rawCapture = PiRGBArray(picam, size=camera_resolution)
                picam.capture(rawCapture, format="rgb")
                frame = rawCapture.array
                rawCapture.truncate(0)
                
                # 转换为BGR格式用于OpenCV
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
            elif camera_type == "webcam" and camera:
                # 使用USB摄像头
                ret, frame = camera.read()
                if not ret:
                    print("无法读取摄像头帧")
                    time.sleep(1)
                    continue
            
            if frame is not None:
                # 编码为JPEG
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if not ret:
                    continue
                    
                frame_bytes = buffer.tobytes()
                
                # 生成MJPEG流格式
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                # 如果摄像头尚未初始化或发生错误
                print("摄像头未初始化，尝试重新初始化...")
                initialize_camera()
                time.sleep(1)
                
        except Exception as e:
            print(f"视频流错误: {str(e)}")
            time.sleep(1)
            try:
                # 重新初始化
                if camera_type == "picamera" and picam:
                    picam.close()
                    picam = None
                elif camera_type == "webcam" and camera:
                    camera.release()
                    camera = None
                initialize_camera()
            except:
                pass

def robot_control_thread():
    global robot_running, last_command, last_command_time
    while True:
        current_time = time.time()
        
        # 安全机制：如果5秒内没有接收到新命令，机器人停止
        if current_time - last_command_time > 5 and last_command != "stop":
            clbrobot.t_stop(0)
            last_command = "stop"
            print("安全停止: 5秒内无新命令")
        
        time.sleep(0.1)

# Web路由
@app.route('/')
def index():
    return render_template('voice_index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/control', methods=['POST'])
def control():
    command = request.json.get('command')
    duration = request.json.get('duration', 0)  # 可选参数，控制持续时间
    
    try:
        execute_robot_command(command, duration)
        return jsonify({
            'status': 'success', 
            'command': command,
            'speed': robot_speed
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/speed', methods=['POST'])
def set_speed():
    global robot_speed, voice_controller
    speed = request.json.get('speed')
    if 0 <= speed <= 100:
        robot_speed = speed
        # 同步语音控制器的速度
        if voice_controller:
            voice_controller.set_speed(speed)
        return jsonify({'status': 'success', 'speed': speed})
    return jsonify({'status': 'error', 'message': '无效的速度值'})

@app.route('/sensors')
def get_sensors():
    """获取传感器数据"""
    sensor_info = read_sensors()
    return jsonify(sensor_info)

@app.route('/obstacle_avoidance', methods=['POST'])
def toggle_obstacle_avoidance():
    """切换自动避障状态"""
    global auto_obstacle_avoidance
    auto_obstacle_avoidance = not auto_obstacle_avoidance
    return jsonify({
        'status': 'success',
        'enabled': auto_obstacle_avoidance
    })

@app.route('/voice_control', methods=['POST'])
def toggle_voice_control():
    """切换语音控制状态"""
    global voice_control_enabled, voice_controller
    
    try:
        if voice_control_enabled:
            # 停止语音控制
            if voice_controller:
                voice_controller.stop()
            voice_control_enabled = False
            logger.info("语音控制已停止")
        else:
            # 启动语音控制
            if not voice_controller:
                # 创建语音控制器，共享机器人实例
                voice_controller = VoiceController(robot=clbrobot)
                # 使用自定义的命令执行函数
                voice_controller._execute_robot_command = lambda cmd: execute_robot_command(cmd, 1.0)
            
            if voice_controller.start():
                voice_control_enabled = True
                logger.info("语音控制已启动")
            else:
                return jsonify({
                    'status': 'error',
                    'message': '语音控制启动失败，请检查麦克风连接'
                })
        
        return jsonify({
            'status': 'success',
            'enabled': voice_control_enabled
        })
        
    except Exception as e:
        logger.error(f"语音控制切换错误: {e}")
        return jsonify({
            'status': 'error',
            'message': f'语音控制切换失败: {str(e)}'
        })

@app.route('/voice_commands')
def get_voice_commands():
    """获取支持的语音命令列表"""
    commands = {
        '移动命令': ['向前', '前进', '向后', '后退', '左转', '右转'],
        '侧移命令': ['左移', '右移'],
        '控制命令': ['停止', '快一点', '慢一点']
    }
    return jsonify(commands)

@app.route('/camera/status', methods=['GET'])
def camera_status():
    global camera_enabled
    return jsonify({
        'enabled': camera_enabled,
        'resolution': camera_resolution,
        'type': camera_type
    })

@app.route('/camera/toggle', methods=['POST'])
def toggle_camera():
    global camera_enabled
    camera_enabled = not camera_enabled
    return jsonify({
        'status': 'success',
        'enabled': camera_enabled
    })

@app.route('/camera/restart', methods=['POST'])
def restart_camera():
    global camera, picam, camera_type
    try:
        # 关闭现有摄像头
        if camera_type == "picamera" and picam:
            picam.close()
            picam = None
        elif camera_type == "webcam" and camera:
            camera.release()
            camera = None
            
        # 重新初始化
        success = initialize_camera()
        return jsonify({
            'status': 'success' if success else 'failed',
            'message': '摄像头重启' + ('成功' if success else '失败'),
            'camera_type': camera_type
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'摄像头重启出错: {str(e)}'
        })

@app.route('/status', methods=['GET'])
def get_status():
    global camera_type, auto_obstacle_avoidance, voice_control_enabled
    return jsonify({
        'status': 'online',
        'last_command': last_command,
        'speed': robot_speed,
        'uptime': time.time() - start_time,
        'camera_type': camera_type,
        'auto_avoidance': auto_obstacle_avoidance,
        'voice_control': voice_control_enabled,
        'sensors': sensor_data
    })

# 记录启动时间
start_time = time.time()

if __name__ == '__main__':
    try:
        # 启动控制线程
        control_thread = threading.Thread(target=robot_control_thread)
        control_thread.daemon = True
        control_thread.start()
        
        # 初始化传感器
        setup_sensors()
        
        # 启动传感器监控线程
        sensor_thread = threading.Thread(target=sensor_monitor_thread)
        sensor_thread.daemon = True
        sensor_thread.start()
        
        # 初始化摄像头
        if not initialize_camera():
            print("警告: 摄像头初始化失败，继续运行但无视频流")
        
        print("机器人语音Web控制服务启动于 http://0.0.0.0:5000")
        print("支持的语音命令: 向前、向后、左转、右转、停止、快一点、慢一点等")
        
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        print("\n正在关闭...")
        clbrobot.t_stop(0)
        
        # 停止语音控制
        if voice_controller:
            voice_controller.stop()
            
        # 释放摄像头资源
        if camera_type == "picamera" and picam:
            picam.close()
        elif camera_type == "webcam" and camera:
            camera.release()
            
        GPIO.cleanup()
        print("系统已关闭") 