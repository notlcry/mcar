#!/usr/bin/python3
"""
机器人语音Web控制系统 - 集成语音控制和Web控制
支持通过Web界面和语音命令双重控制机器人
"""

from flask import Flask, render_template, request, jsonify, Response
from markupsafe import escape
from LOBOROBOT import LOBOROBOT
from voice_control import VoiceController
from enhanced_voice_control import EnhancedVoiceController
from ai_conversation import AIConversationManager
from emotion_engine import EmotionEngine
from personality_manager import PersonalityManager
from safety_manager import SafetyManager
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
import random

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
ai_conversation_enabled = False  # 是否启用AI对话模式
voice_controller = None          # 语音控制器实例
enhanced_voice_controller = None # 增强语音控制器实例
ai_conversation_manager = None   # AI对话管理器实例
emotion_engine = None            # 情感引擎实例
personality_manager = None       # 个性管理器实例
safety_manager = None            # 安全管理器实例

# 会话状态管理
current_session_id = None        # 当前会话ID
session_start_time = None        # 会话开始时间
conversation_context = {}        # 对话上下文缓存
session_history = {}             # 会话历史记录
active_sessions = {}             # 活跃会话管理

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

def execute_robot_command(command, duration=0, emotion_context=None, session_id=None):
    """执行机器人命令的通用函数，支持情感上下文和会话跟踪"""
    global last_command, last_command_time, robot_speed, personality_manager, safety_manager
    
    # 安全检查 - 障碍物避让系统优先级高于个性化动作
    if safety_manager and not safety_manager.check_movement_safety(command, emotion_context):
        logger.warning(f"安全检查失败，拒绝执行命令: {command}")
        return
    
    last_command = command
    last_command_time = time.time()
    
    if duration == 0:
        duration = 0 if command == 'stop' else 0.1  # 默认短时间执行
    
    # 记录命令到会话历史
    if session_id and session_id in active_sessions:
        active_sessions[session_id]['commands'].append({
            'command': command,
            'timestamp': time.time(),
            'emotion_context': emotion_context,
            'duration': duration
        })
    
    # 如果有个性管理器且提供了情感上下文，使用个性化执行
    if personality_manager and emotion_context:
        try:
            # 将Web命令转换为对话命令格式
            command_mapping = {
                'forward': '前进',
                'backward': '后退', 
                'left': '左转',
                'right': '右转',
                'move_left': '左移',
                'move_right': '右移',
                'stop': '停止'
            }
            
            if command in command_mapping:
                # 如果emotion_context是字符串，需要转换为EmotionType
                if isinstance(emotion_context, str):
                    from emotion_engine import EmotionType
                    emotion_map = {
                        'happy': EmotionType.HAPPY,
                        'excited': EmotionType.EXCITED,
                        'sad': EmotionType.SAD,
                        'confused': EmotionType.CONFUSED,
                        'thinking': EmotionType.THINKING,
                        'angry': EmotionType.ANGRY,
                        'surprised': EmotionType.SURPRISED,
                        'neutral': EmotionType.NEUTRAL
                    }
                    emotion_context = emotion_map.get(emotion_context, EmotionType.NEUTRAL)
                
                personality_manager.handle_conversation_command(
                    command_mapping[command], 
                    emotion_context
                )
                logger.info(f"执行个性化命令: {command} (情感: {emotion_context.value}) [会话: {session_id}]")
                return
        except Exception as e:
            logger.warning(f"个性化命令执行失败，回退到基础命令: {e}")
    
    # 基础命令执行
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
    
    logger.info(f"执行命令: {command}, 速度: {robot_speed}, 持续时间: {duration} [会话: {session_id}]")

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
    global last_command, safety_manager
    
    # 读取传感器数据
    left_ir = sensor_data["left_ir"]
    right_ir = sensor_data["right_ir"]
    distance = sensor_data["ultrasonic"]
    
    # 更新安全管理器的障碍物状态
    obstacle_detected = distance < 30 or left_ir or right_ir
    if safety_manager:
        safety_manager.update_obstacle_status(obstacle_detected)
    
    # 避障逻辑
    if obstacle_detected:
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

def create_session():
    """创建新的对话会话"""
    global current_session_id, session_start_time, active_sessions
    
    session_id = f"session_{int(time.time())}_{random.randint(1000, 9999)}"
    current_session_id = session_id
    session_start_time = time.time()
    
    # 初始化会话数据
    active_sessions[session_id] = {
        'id': session_id,
        'start_time': session_start_time,
        'last_activity': session_start_time,
        'conversation_history': [],
        'commands': [],
        'emotion_states': [],
        'context': {},
        'status': 'active'
    }
    
    logger.info(f"创建新会话: {session_id}")
    return session_id

def update_session_activity(session_id):
    """更新会话活动时间"""
    if session_id in active_sessions:
        active_sessions[session_id]['last_activity'] = time.time()

def cleanup_inactive_sessions():
    """清理非活跃会话"""
    global active_sessions
    current_time = time.time()
    inactive_threshold = 1800  # 30分钟无活动则清理
    
    sessions_to_remove = []
    for session_id, session_data in active_sessions.items():
        if current_time - session_data['last_activity'] > inactive_threshold:
            sessions_to_remove.append(session_id)
    
    for session_id in sessions_to_remove:
        del active_sessions[session_id]
        logger.info(f"清理非活跃会话: {session_id}")

def get_session_context(session_id):
    """获取会话上下文"""
    if session_id in active_sessions:
        return active_sessions[session_id]['context']
    return {}

def update_session_context(session_id, context_data):
    """更新会话上下文"""
    if session_id in active_sessions:
        active_sessions[session_id]['context'].update(context_data)
        update_session_activity(session_id)

def robot_control_thread():
    global robot_running, last_command, last_command_time
    while True:
        current_time = time.time()
        
        # 安全机制：如果5秒内没有接收到新命令，机器人停止
        if current_time - last_command_time > 5 and last_command != "stop":
            clbrobot.t_stop(0)
            last_command = "stop"
            print("安全停止: 5秒内无新命令")
        
        # 定期清理非活跃会话
        if int(current_time) % 300 == 0:  # 每5分钟清理一次
            cleanup_inactive_sessions()
        
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
    emotion_context = request.json.get('emotion_context')  # 可选情感上下文
    session_id = request.json.get('session_id', current_session_id)  # 可选会话ID
    
    try:
        execute_robot_command(command, duration, emotion_context, session_id)
        return jsonify({
            'status': 'success', 
            'command': command,
            'speed': robot_speed,
            'emotion_context': emotion_context,
            'session_id': session_id
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

@app.route('/ai_conversation', methods=['POST'])
def toggle_ai_conversation():
    """切换AI对话模式"""
    global ai_conversation_enabled, enhanced_voice_controller, ai_conversation_manager, emotion_engine, personality_manager, safety_manager
    
    try:
        if ai_conversation_enabled:
            # 停止AI对话模式
            if enhanced_voice_controller:
                enhanced_voice_controller.stop_conversation_mode()
            if safety_manager:
                safety_manager.stop_monitoring()
            ai_conversation_enabled = False
            logger.info("AI对话模式已停止")
        else:
            # 初始化安全管理器
            if not safety_manager:
                safety_manager = SafetyManager(robot_controller=clbrobot)
                safety_manager.start_monitoring()
                logger.info("安全管理器已初始化并启动监控")
            
            # 初始化AI系统组件
            if not emotion_engine:
                emotion_engine = EmotionEngine()
                logger.info("情感引擎已初始化")
            
            if not personality_manager:
                personality_manager = PersonalityManager(clbrobot, emotion_engine, safety_manager=safety_manager)
                logger.info("个性管理器已初始化")
            
            if not ai_conversation_manager:
                ai_conversation_manager = AIConversationManager(robot_controller=clbrobot, safety_manager=safety_manager)
                logger.info("AI对话管理器已初始化")
            
            if not enhanced_voice_controller:
                # 检查是否需要使用测试模式（避免音频流冲突）
                use_test_mode = os.getenv('VOICE_TEST_MODE', 'false').lower() == 'true'
                
                enhanced_voice_controller = EnhancedVoiceController(
                    robot=clbrobot, 
                    ai_conversation_manager=ai_conversation_manager,
                    safety_manager=safety_manager,
                    test_mode=use_test_mode
                )
                
                if use_test_mode:
                    logger.info("增强语音控制器已初始化（测试模式）")
                else:
                    logger.info("增强语音控制器已初始化（正常模式）")
            
            # 启动AI对话模式
            if enhanced_voice_controller.start_conversation_mode():
                ai_conversation_enabled = True
                # 创建新会话
                session_id = create_session()
                logger.info(f"AI对话模式已启动，会话ID: {session_id}")
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'AI对话模式启动失败，请检查配置'
                })
        
        return jsonify({
            'status': 'success',
            'enabled': ai_conversation_enabled,
            'session_id': current_session_id if ai_conversation_enabled else None
        })
        
    except Exception as e:
        logger.error(f"AI对话模式切换错误: {e}")
        return jsonify({
            'status': 'error',
            'message': f'AI对话模式切换失败: {str(e)}'
        })

@app.route('/ai_chat', methods=['POST'])
def ai_chat():
    """处理AI对话请求"""
    global ai_conversation_manager, current_session_id, personality_manager
    
    try:
        user_input = request.json.get('message', '').strip()
        session_id = request.json.get('session_id', current_session_id)
        
        if not user_input:
            return jsonify({
                'status': 'error',
                'message': '消息不能为空'
            })
        
        if not ai_conversation_manager or not ai_conversation_manager.is_active():
            return jsonify({
                'status': 'error',
                'message': 'AI对话模式未启动'
            })
        
        # 确保会话存在
        if not session_id or session_id not in active_sessions:
            session_id = create_session()
        
        # 更新会话活动时间
        update_session_activity(session_id)
        
        # 处理用户输入
        context = ai_conversation_manager.process_user_input(user_input)
        
        if context:
            # 记录对话到会话历史
            conversation_entry = {
                'user_input': user_input,
                'ai_response': context.ai_response,
                'emotion': context.emotion_detected,
                'timestamp': context.timestamp.isoformat()
            }
            
            if session_id in active_sessions:
                active_sessions[session_id]['conversation_history'].append(conversation_entry)
                active_sessions[session_id]['emotion_states'].append({
                    'emotion': context.emotion_detected,
                    'timestamp': context.timestamp.isoformat()
                })
            
            # 检查是否包含运动指令并执行
            if personality_manager:
                # 分析用户输入中的运动指令
                movement_keywords = ['前进', '后退', '左转', '右转', '转圈', '跳舞', '停止', '移动']
                if any(keyword in user_input for keyword in movement_keywords):
                    try:
                        from emotion_engine import EmotionType
                        emotion_map = {
                            'happy': EmotionType.HAPPY,
                            'excited': EmotionType.EXCITED,
                            'sad': EmotionType.SAD,
                            'confused': EmotionType.CONFUSED,
                            'thinking': EmotionType.THINKING,
                            'angry': EmotionType.ANGRY,
                            'surprised': EmotionType.SURPRISED,
                            'neutral': EmotionType.NEUTRAL
                        }
                        emotion_type = emotion_map.get(context.emotion_detected, EmotionType.NEUTRAL)
                        
                        # 执行个性化运动
                        personality_manager.handle_conversation_command(user_input, emotion_type)
                        logger.info(f"执行对话运动指令: {user_input} (情感: {context.emotion_detected})")
                    except Exception as e:
                        logger.warning(f"执行对话运动指令失败: {e}")
            
            # 如果有增强语音控制器，播放回复并更新显示器
            if enhanced_voice_controller:
                enhanced_voice_controller.speak_text(context.ai_response)
                
                # 更新OLED显示器 - 作为机器人的脸，只显示表情
                if enhanced_voice_controller.display_controller:
                    # 只显示情感表情，持续显示直到下一个表情
                    if context.emotion_detected:
                        # 使用较长的持续时间，让表情保持显示
                        enhanced_voice_controller.display_controller.show_emotion(context.emotion_detected, 30.0)
                    else:
                        # 如果没有明确情感，显示默认的开心表情
                        enhanced_voice_controller.display_controller.show_emotion("happy", 30.0)
            
            return jsonify({
                'status': 'success',
                'response': context.ai_response,
                'emotion': context.emotion_detected,
                'timestamp': context.timestamp.isoformat(),
                'session_id': session_id
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '处理消息失败'
            })
            
    except Exception as e:
        logger.error(f"AI对话处理错误: {e}")
        return jsonify({
            'status': 'error',
            'message': f'对话处理失败: {str(e)}'
        })

@app.route('/conversation_history', methods=['GET'])
def get_conversation_history():
    """获取对话历史"""
    global ai_conversation_manager
    
    try:
        if ai_conversation_manager:
            history = ai_conversation_manager.get_conversation_history()
            return jsonify({
                'status': 'success',
                'history': history
            })
        else:
            return jsonify({
                'status': 'success',
                'history': []
            })
            
    except Exception as e:
        logger.error(f"获取对话历史错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/clear_history', methods=['POST'])
def clear_conversation_history():
    """清空对话历史"""
    global ai_conversation_manager
    
    try:
        session_id = request.json.get('session_id', current_session_id)
        
        if ai_conversation_manager:
            ai_conversation_manager.clear_conversation_history()
        
        # 清空会话历史
        if session_id and session_id in active_sessions:
            active_sessions[session_id]['conversation_history'] = []
            active_sessions[session_id]['emotion_states'] = []
            active_sessions[session_id]['commands'] = []
            update_session_activity(session_id)
        
        return jsonify({
            'status': 'success',
            'message': '对话历史已清空',
            'session_id': session_id
        })
        
    except Exception as e:
        logger.error(f"清空对话历史错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/session/create', methods=['POST'])
def create_new_session():
    """创建新的对话会话"""
    try:
        session_id = create_session()
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'message': '新会话已创建'
        })
    except Exception as e:
        logger.error(f"创建会话错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/session/<session_id>', methods=['GET'])
def get_session_info(session_id):
    """获取会话信息"""
    try:
        if session_id not in active_sessions:
            return jsonify({
                'status': 'error',
                'message': '会话不存在'
            })
        
        session_data = active_sessions[session_id]
        return jsonify({
            'status': 'success',
            'session': {
                'id': session_data['id'],
                'start_time': session_data['start_time'],
                'last_activity': session_data['last_activity'],
                'conversation_count': len(session_data['conversation_history']),
                'command_count': len(session_data['commands']),
                'status': session_data['status']
            }
        })
    except Exception as e:
        logger.error(f"获取会话信息错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/session/<session_id>/history', methods=['GET'])
def get_session_history(session_id):
    """获取会话历史"""
    try:
        if session_id not in active_sessions:
            return jsonify({
                'status': 'error',
                'message': '会话不存在'
            })
        
        session_data = active_sessions[session_id]
        return jsonify({
            'status': 'success',
            'history': session_data['conversation_history'],
            'commands': session_data['commands'],
            'emotions': session_data['emotion_states']
        })
    except Exception as e:
        logger.error(f"获取会话历史错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/sessions', methods=['GET'])
def list_active_sessions():
    """列出所有活跃会话"""
    try:
        sessions_info = []
        for session_id, session_data in active_sessions.items():
            sessions_info.append({
                'id': session_id,
                'start_time': session_data['start_time'],
                'last_activity': session_data['last_activity'],
                'conversation_count': len(session_data['conversation_history']),
                'status': session_data['status']
            })
        
        return jsonify({
            'status': 'success',
            'sessions': sessions_info,
            'total_count': len(sessions_info)
        })
    except Exception as e:
        logger.error(f"列出会话错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/ai_emotion', methods=['GET'])
def get_current_emotion():
    """获取当前情感状态"""
    try:
        if not emotion_engine:
            return jsonify({
                'status': 'error',
                'message': '情感引擎未初始化'
            })
        
        emotion_state = emotion_engine.get_current_emotional_state()
        return jsonify({
            'status': 'success',
            'emotion': {
                'primary': emotion_state.primary_emotion.value,
                'intensity': emotion_state.intensity,
                'movement_pattern': emotion_state.movement_pattern,
                'secondary_emotions': {k.value: v for k, v in emotion_state.secondary_emotions.items()},
                'triggers': emotion_state.triggers,
                'timestamp': emotion_state.timestamp.isoformat()
            }
        })
    except Exception as e:
        logger.error(f"获取情感状态错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/personality_settings', methods=['POST'])
def update_personality_settings():
    """更新个性设置"""
    global personality_manager
    
    try:
        settings = request.json.get('settings', {})
        session_id = request.json.get('session_id', current_session_id)
        
        if not personality_manager:
            return jsonify({
                'status': 'error',
                'message': '个性管理器未初始化'
            })
        
        # 更新个性设置
        personality_traits = {
            'friendliness': settings.get('friendliness', 80) / 100.0,
            'energy_level': settings.get('energy', 70) / 100.0,
            'curiosity': settings.get('curiosity', 60) / 100.0,
            'playfulness': settings.get('playfulness', 90) / 100.0
        }
        
        # 更新个性管理器的设置
        personality_manager.update_personality_traits(personality_traits)
        
        # 更新会话上下文
        if session_id and session_id in active_sessions:
            active_sessions[session_id]['context']['personality_settings'] = settings
            update_session_activity(session_id)
        
        logger.info(f"个性设置已更新: {settings} [会话: {session_id}]")
        
        return jsonify({
            'status': 'success',
            'settings': settings,
            'session_id': session_id
        })
        
    except Exception as e:
        logger.error(f"更新个性设置错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/voice_settings', methods=['POST'])
def update_voice_settings():
    """更新语音设置"""
    global enhanced_voice_controller
    
    try:
        voice = request.json.get('voice', 'zh-CN-XiaoxiaoNeural')
        session_id = request.json.get('session_id', current_session_id)
        
        # 更新增强语音控制器的语音设置
        if enhanced_voice_controller:
            enhanced_voice_controller.set_tts_voice(voice)
        
        # 更新会话上下文
        if session_id and session_id in active_sessions:
            active_sessions[session_id]['context']['voice_settings'] = {'voice': voice}
            update_session_activity(session_id)
        
        logger.info(f"语音设置已更新: {voice} [会话: {session_id}]")
        
        return jsonify({
            'status': 'success',
            'voice': voice,
            'session_id': session_id
        })
        
    except Exception as e:
        logger.error(f"更新语音设置错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/ai_status', methods=['GET'])
def get_ai_status():
    """获取AI系统状态"""
    global ai_conversation_enabled, current_session_id, emotion_engine, personality_manager
    
    try:
        status_info = {
            'ai_conversation_enabled': ai_conversation_enabled,
            'session_id': current_session_id,
            'session_active': current_session_id in active_sessions if current_session_id else False,
            'emotion_engine_active': emotion_engine is not None,
            'personality_manager_active': personality_manager is not None
        }
        
        # 添加当前情感状态
        if emotion_engine:
            try:
                emotion_state = emotion_engine.get_current_emotional_state()
                status_info['current_emotion'] = {
                    'primary': emotion_state.primary_emotion.value,
                    'intensity': emotion_state.intensity,
                    'movement_pattern': emotion_state.movement_pattern
                }
            except Exception as e:
                logger.warning(f"获取情感状态失败: {e}")
                status_info['current_emotion'] = None
        
        # 添加会话统计
        if current_session_id and current_session_id in active_sessions:
            session_data = active_sessions[current_session_id]
            status_info['session_stats'] = {
                'conversation_count': len(session_data['conversation_history']),
                'command_count': len(session_data['commands']),
                'duration': time.time() - session_data['start_time']
            }
        
        return jsonify({
            'status': 'success',
            'ai_status': status_info
        })
        
    except Exception as e:
        logger.error(f"获取AI状态错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/ai_personality', methods=['GET', 'POST'])
def manage_personality():
    """管理个性设置"""
    global personality_manager
    
    try:
        if request.method == 'GET':
            # 获取当前个性设置
            if not personality_manager:
                return jsonify({
                    'status': 'error',
                    'message': '个性管理器未初始化'
                })
            
            status = personality_manager.get_status()
            return jsonify({
                'status': 'success',
                'personality': {
                    'name': status['personality_name'],
                    'traits': status['personality_traits'],
                    'current_emotion': status['current_emotion'],
                    'emotion_intensity': status['emotion_intensity']
                }
            })
        
        elif request.method == 'POST':
            # 更新个性设置
            if not personality_manager:
                return jsonify({
                    'status': 'error',
                    'message': '个性管理器未初始化'
                })
            
            traits = request.json.get('traits', {})
            if traits:
                personality_manager.update_personality_traits(traits)
                return jsonify({
                    'status': 'success',
                    'message': '个性设置已更新',
                    'updated_traits': traits
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': '未提供有效的个性特征数据'
                })
    
    except Exception as e:
        logger.error(f"管理个性设置错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/ai_execute_emotion', methods=['POST'])
def execute_emotional_movement():
    """执行情感驱动的运动"""
    global personality_manager
    
    try:
        if not personality_manager:
            return jsonify({
                'status': 'error',
                'message': '个性管理器未初始化'
            })
        
        emotion = request.json.get('emotion', 'neutral')
        intensity = request.json.get('intensity', 0.5)
        
        # 转换情感类型
        from emotion_engine import EmotionType
        emotion_map = {
            'happy': EmotionType.HAPPY,
            'excited': EmotionType.EXCITED,
            'sad': EmotionType.SAD,
            'confused': EmotionType.CONFUSED,
            'thinking': EmotionType.THINKING,
            'angry': EmotionType.ANGRY,
            'surprised': EmotionType.SURPRISED,
            'neutral': EmotionType.NEUTRAL
        }
        
        emotion_type = emotion_map.get(emotion, EmotionType.NEUTRAL)
        
        # 执行情感运动
        success = personality_manager.execute_emotional_movement(emotion_type, intensity)
        
        return jsonify({
            'status': 'success' if success else 'failed',
            'message': f'情感运动{"执行成功" if success else "执行失败"}',
            'emotion': emotion,
            'intensity': intensity
        })
        
    except Exception as e:
        logger.error(f"执行情感运动错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/status', methods=['GET'])
def get_status():
    global camera_type, auto_obstacle_avoidance, voice_control_enabled, ai_conversation_enabled
    
    # 获取AI对话状态
    ai_status = {}
    if ai_conversation_manager:
        ai_status = ai_conversation_manager.get_status()
    
    # 获取增强语音控制状态
    voice_status = {}
    if enhanced_voice_controller:
        voice_status = enhanced_voice_controller.get_conversation_status()
    
    # 获取情感引擎状态
    emotion_status = {}
    if emotion_engine:
        emotion_status = emotion_engine.get_status()
    
    # 获取个性管理器状态
    personality_status = {}
    if personality_manager:
        personality_status = personality_manager.get_status()
    
    # 获取会话统计
    session_stats = {
        'active_sessions': len(active_sessions),
        'current_session': current_session_id,
        'total_conversations': sum(len(s['conversation_history']) for s in active_sessions.values()),
        'total_commands': sum(len(s['commands']) for s in active_sessions.values())
    }
    
    return jsonify({
        'status': 'online',
        'last_command': last_command,
        'speed': robot_speed,
        'uptime': time.time() - start_time,
        'camera_type': camera_type,
        'auto_avoidance': auto_obstacle_avoidance,
        'voice_control': voice_control_enabled,
        'ai_conversation': ai_conversation_enabled,
        'sensors': sensor_data,
        'ai_status': ai_status,
        'voice_status': voice_status,
        'emotion_status': emotion_status,
        'personality_status': personality_status,
        'session_stats': session_stats
    })

@app.route('/ai_integrated_command', methods=['POST'])
def ai_integrated_command():
    """集成AI对话和机器人控制的统一接口"""
    global ai_conversation_manager, personality_manager, current_session_id
    
    try:
        user_input = request.json.get('message', '').strip()
        command_type = request.json.get('type', 'conversation')  # 'conversation' 或 'command'
        session_id = request.json.get('session_id', current_session_id)
        
        if not user_input:
            return jsonify({
                'status': 'error',
                'message': '输入不能为空'
            })
        
        # 确保AI系统已初始化
        if not ai_conversation_manager or not ai_conversation_manager.is_active():
            return jsonify({
                'status': 'error',
                'message': 'AI对话系统未启动'
            })
        
        # 确保会话存在
        if not session_id or session_id not in active_sessions:
            session_id = create_session()
        
        update_session_activity(session_id)
        
        # 处理输入
        if command_type == 'conversation':
            # AI对话处理
            context = ai_conversation_manager.process_user_input(user_input)
            
            if not context:
                return jsonify({
                    'status': 'error',
                    'message': '对话处理失败'
                })
            
            # 记录到会话历史
            conversation_entry = {
                'user_input': user_input,
                'ai_response': context.ai_response,
                'emotion': context.emotion_detected,
                'timestamp': context.timestamp.isoformat(),
                'type': 'conversation'
            }
            
            if session_id in active_sessions:
                active_sessions[session_id]['conversation_history'].append(conversation_entry)
                active_sessions[session_id]['emotion_states'].append({
                    'emotion': context.emotion_detected,
                    'timestamp': context.timestamp.isoformat()
                })
            
            # 分析是否包含运动指令
            movement_executed = False
            if personality_manager:
                movement_keywords = ['前进', '后退', '左转', '右转', '转圈', '跳舞', '停止', '移动', '走', '来', '去']
                if any(keyword in user_input for keyword in movement_keywords):
                    try:
                        from emotion_engine import EmotionType
                        emotion_map = {
                            'happy': EmotionType.HAPPY,
                            'excited': EmotionType.EXCITED,
                            'sad': EmotionType.SAD,
                            'confused': EmotionType.CONFUSED,
                            'thinking': EmotionType.THINKING,
                            'angry': EmotionType.ANGRY,
                            'surprised': EmotionType.SURPRISED,
                            'neutral': EmotionType.NEUTRAL
                        }
                        emotion_type = emotion_map.get(context.emotion_detected, EmotionType.NEUTRAL)
                        
                        # 执行个性化运动
                        movement_executed = personality_manager.handle_conversation_command(user_input, emotion_type)
                        
                        # 记录运动命令
                        if movement_executed and session_id in active_sessions:
                            active_sessions[session_id]['commands'].append({
                                'command': user_input,
                                'timestamp': time.time(),
                                'emotion_context': context.emotion_detected,
                                'type': 'ai_triggered'
                            })
                        
                        logger.info(f"AI触发运动指令: {user_input} (情感: {context.emotion_detected}) - {'成功' if movement_executed else '失败'}")
                    except Exception as e:
                        logger.warning(f"AI触发运动指令失败: {e}")
            
            # 语音回复
            if enhanced_voice_controller:
                enhanced_voice_controller.speak_text(context.ai_response)
            
            return jsonify({
                'status': 'success',
                'response': context.ai_response,
                'emotion': context.emotion_detected,
                'timestamp': context.timestamp.isoformat(),
                'session_id': session_id,
                'movement_executed': movement_executed,
                'type': 'conversation'
            })
        
        elif command_type == 'command':
            # 直接命令处理
            # 解析命令
            command_mapping = {
                '前进': 'forward',
                '后退': 'backward',
                '左转': 'left',
                '右转': 'right',
                '左移': 'move_left',
                '右移': 'move_right',
                '停止': 'stop'
            }
            
            robot_command = None
            for chinese_cmd, english_cmd in command_mapping.items():
                if chinese_cmd in user_input:
                    robot_command = english_cmd
                    break
            
            if robot_command:
                # 获取当前情感状态作为上下文
                emotion_context = 'neutral'
                if emotion_engine:
                    current_emotion = emotion_engine.get_current_emotional_state()
                    emotion_context = current_emotion.primary_emotion.value
                
                # 执行命令
                execute_robot_command(robot_command, 1.0, emotion_context, session_id)
                
                return jsonify({
                    'status': 'success',
                    'command': robot_command,
                    'original_input': user_input,
                    'emotion_context': emotion_context,
                    'session_id': session_id,
                    'type': 'command'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'未识别的命令: {user_input}'
                })
        
        else:
            return jsonify({
                'status': 'error',
                'message': f'不支持的命令类型: {command_type}'
            })
    
    except Exception as e:
        logger.error(f"集成命令处理错误: {e}")
        return jsonify({
            'status': 'error',
            'message': f'处理失败: {str(e)}'
        })

@app.route('/ai_wake_up', methods=['POST'])
def ai_wake_up():
    """强制唤醒AI对话模式（用于测试或手动激活）"""
    global enhanced_voice_controller
    
    try:
        if not enhanced_voice_controller:
            return jsonify({
                'status': 'error',
                'message': '增强语音控制器未初始化'
            })
        
        success = enhanced_voice_controller.force_wake_up()
        
        return jsonify({
            'status': 'success' if success else 'failed',
            'message': '强制唤醒' + ('成功' if success else '失败')
        })
        
    except Exception as e:
        logger.error(f"强制唤醒错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/safety/status', methods=['GET'])
def get_safety_status():
    """获取安全状态"""
    try:
        if not safety_manager:
            return jsonify({
                'status': 'error',
                'message': '安全管理器未初始化'
            })
        
        safety_status = safety_manager.get_safety_status()
        system_health = safety_manager.get_system_health()
        
        return jsonify({
            'status': 'success',
            'safety_status': safety_status,
            'system_health': system_health
        })
        
    except Exception as e:
        logger.error(f"获取安全状态错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/safety/emergency_stop', methods=['POST'])
def emergency_stop():
    """紧急停止"""
    try:
        if safety_manager:
            safety_manager.emergency_stop()
        else:
            # 直接停止机器人
            clbrobot.t_stop(0.1)
        
        return jsonify({
            'status': 'success',
            'message': '紧急停止已执行'
        })
        
    except Exception as e:
        logger.error(f"紧急停止错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/safety/reset_emergency', methods=['POST'])
def reset_emergency_stop():
    """重置紧急停止状态"""
    try:
        if not safety_manager:
            return jsonify({
                'status': 'error',
                'message': '安全管理器未初始化'
            })
        
        safety_manager.reset_emergency_stop()
        
        return jsonify({
            'status': 'success',
            'message': '紧急停止状态已重置'
        })
        
    except Exception as e:
        logger.error(f"重置紧急停止错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/safety/offline_command', methods=['POST'])
def process_offline_command():
    """处理离线模式命令"""
    try:
        user_input = request.json.get('command', '').strip()
        
        if not user_input:
            return jsonify({
                'status': 'error',
                'message': '命令不能为空'
            })
        
        if not safety_manager:
            return jsonify({
                'status': 'error',
                'message': '安全管理器未初始化'
            })
        
        response = safety_manager.process_offline_command(user_input)
        
        if response:
            return jsonify({
                'status': 'success',
                'response': response,
                'offline_mode': safety_manager.safety_state.offline_mode_active
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '无法处理该命令'
            })
            
    except Exception as e:
        logger.error(f"处理离线命令错误: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
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
            
        # 停止AI对话模式
        if enhanced_voice_controller:
            enhanced_voice_controller.stop_conversation_mode()
            
        if ai_conversation_manager:
            ai_conversation_manager.stop_conversation_mode()
            
        # 释放摄像头资源
        if camera_type == "picamera" and picam:
            picam.close()
        elif camera_type == "webcam" and camera:
            camera.release()
            
        GPIO.cleanup()
        print("系统已关闭") 