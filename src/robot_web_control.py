from flask import Flask, render_template, request, jsonify, Response
from markupsafe import escape
from LOBOROBOT import LOBOROBOT
import RPi.GPIO as GPIO
import threading
import time
import os
import cv2
import numpy as np
import io
from picamera import PiCamera
from picamera.array import PiRGBArray

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
            print("普通USB摄像头打开失败，尝试使用V4L2...")
            camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
            
        if not camera.isOpened():
            print("所有摄像头尝试均失败")
            return False
            
        # 设置分辨率
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, camera_resolution[0])
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_resolution[1])
        
        # 读取一帧测试摄像头
        ret, test_frame = camera.read()
        if not ret:
            print("无法读取摄像头图像")
            camera.release()
            camera = None
            return False
            
        camera_type = "webcam"
        print(f"普通摄像头初始化成功，分辨率: {test_frame.shape[1]}x{test_frame.shape[0]}")
        return True
    except Exception as e:
        print(f"摄像头初始化失败: {str(e)}")
        if camera:
            camera.release()
            camera = None
        return False

def generate_frames():
    global camera, picam, camera_enabled, camera_type
    consecutive_failures = 0
    max_failures = 5
    
    while camera_enabled:
        try:
            # 根据摄像头类型不同的处理方式
            if camera_type == "picamera" and picam:
                # PiCamera方式 - 使用更简单的捕获方式
                try:
                    # 使用更低质量设置
                    stream = io.BytesIO()
                    picam.capture(stream, format='jpeg', use_video_port=True, quality=30, resize=(320, 240))
                    stream.seek(0)
                    frame_bytes = stream.read()
                    
                    # 生成MJPEG流格式
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    
                    # 速率控制 - 防止过快刷新
                    time.sleep(0.1)
                except Exception as e:
                    print(f"PiCamera捕获错误: {str(e)}")
                    time.sleep(0.5)
                    
            elif camera_type == "webcam" and camera and camera.isOpened():
                # 普通摄像头方式
                success, frame = camera.read()
                if not success:
                    consecutive_failures += 1
                    print(f"无法读取摄像头帧 (失败 {consecutive_failures}/{max_failures})")
                    
                    if consecutive_failures >= max_failures:
                        print("连续多次读取失败，重新初始化摄像头...")
                        camera.release()
                        camera = None
                        initialize_camera()
                        consecutive_failures = 0
                    
                    time.sleep(0.1)
                    continue
                    
                # 重置失败计数
                consecutive_failures = 0
                    
                # 翻转图像
                frame = cv2.flip(frame, 0)  # 垂直翻转
                
                # 调整大小减少带宽
                if frame.shape[1] > 480:
                    scale = 480 / frame.shape[1]
                    width = int(frame.shape[1] * scale)
                    height = int(frame.shape[0] * scale)
                    frame = cv2.resize(frame, (width, height))
                
                # 编码
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                if not ret:
                    print("编码图像失败")
                    time.sleep(0.1)
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
            
    print("视频流已停止")
    
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

# 启动控制线程
control_thread = threading.Thread(target=robot_control_thread)
control_thread.daemon = True
control_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/camera/status', methods=['GET'])
def camera_status():
    global camera_enabled
    return jsonify({
        'enabled': camera_enabled,
        'resolution': camera_resolution
    })

@app.route('/camera/toggle', methods=['POST'])
def toggle_camera():
    global camera_enabled
    camera_enabled = not camera_enabled
    return jsonify({
        'status': 'success',
        'enabled': camera_enabled
    })

@app.route('/control', methods=['POST'])
def control():
    global robot_running, last_command, last_command_time, robot_speed
    command = request.json.get('command')
    duration = request.json.get('duration', 0)  # 可选参数，控制持续时间
    
    last_command = command
    last_command_time = time.time()
    
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
    else:
        return jsonify({'status': 'error', 'message': '未知命令'})
    
    return jsonify({
        'status': 'success', 
        'command': command,
        'speed': robot_speed
    })

@app.route('/speed', methods=['POST'])
def set_speed():
    global robot_speed
    speed = request.json.get('speed')
    if 0 <= speed <= 100:
        robot_speed = speed
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

@app.route('/status', methods=['GET'])
def get_status():
    global camera_type, auto_obstacle_avoidance
    return jsonify({
        'status': 'online',
        'last_command': last_command,
        'speed': robot_speed,
        'uptime': time.time() - start_time,
        'camera_type': camera_type,
        'auto_avoidance': auto_obstacle_avoidance,
        'sensors': sensor_data
    })

# 记录启动时间
start_time = time.time()

if __name__ == '__main__':
    try:
        # 初始化传感器
        setup_sensors()
        
        # 启动传感器监控线程
        sensor_thread = threading.Thread(target=sensor_monitor_thread)
        sensor_thread.daemon = True
        sensor_thread.start()
        
        # 初始化摄像头
        if not initialize_camera():
            print("警告: 摄像头初始化失败，继续运行但无视频流")
        
        print("机器人Web控制服务启动于 http://0.0.0.0:5000")
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        clbrobot.t_stop(0)
        # 释放摄像头资源
        if camera_type == "picamera" and picam:
            picam.close()
        elif camera_type == "webcam" and camera:
            camera.release()
        GPIO.cleanup() 