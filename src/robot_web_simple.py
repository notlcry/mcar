#!/usr/bin/python3
"""
简化版机器人Web控制 - 只保留基本功能，排查问题
"""

from flask import Flask, render_template, request, jsonify
import time
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 简化的机器人控制类
class SimpleRobot:
    def __init__(self):
        self.connected = False
        try:
            # 尝试初始化I2C和PCA9685
            import smbus
            self.bus = smbus.SMBus(1)
            # 测试I2C通信
            self.bus.write_byte_data(0x40, 0x00, 0x00)
            self.connected = True
            print("✅ 机器人硬件连接成功")
        except Exception as e:
            print(f"⚠️ 机器人硬件连接失败: {e}")
            print("💡 将使用模拟模式")
            self.connected = False
    
    def move_forward(self, duration=1.0):
        if self.connected:
            try:
                # 实际的前进控制代码
                print(f"🤖 机器人前进 {duration}秒")
                return True
            except Exception as e:
                print(f"❌ 前进失败: {e}")
                return False
        else:
            print(f"🎭 模拟：机器人前进 {duration}秒")
            return True
    
    def move_backward(self, duration=1.0):
        if self.connected:
            print(f"🤖 机器人后退 {duration}秒")
            return True
        else:
            print(f"🎭 模拟：机器人后退 {duration}秒")
            return True
    
    def turn_left(self, duration=1.0):
        if self.connected:
            print(f"🤖 机器人左转 {duration}秒")
            return True
        else:
            print(f"🎭 模拟：机器人左转 {duration}秒")
            return True
    
    def turn_right(self, duration=1.0):
        if self.connected:
            print(f"🤖 机器人右转 {duration}秒")
            return True
        else:
            print(f"🎭 模拟：机器人右转 {duration}秒")
            return True
    
    def stop(self):
        if self.connected:
            print("🤖 机器人停止")
            return True
        else:
            print("🎭 模拟：机器人停止")
            return True

# 全局机器人实例
robot = SimpleRobot()

@app.route('/')
def index():
    """主页"""
    return render_template('voice_index.html')

@app.route('/control', methods=['POST'])
def control_robot():
    """机器人控制API"""
    try:
        data = request.get_json()
        command = data.get('command')
        duration = float(data.get('duration', 1.0))
        
        logger.info(f"收到控制命令: {command}, 持续时间: {duration}")
        
        success = False
        if command == 'forward':
            success = robot.move_forward(duration)
        elif command == 'backward':
            success = robot.move_backward(duration)
        elif command == 'left':
            success = robot.turn_left(duration)
        elif command == 'right':
            success = robot.turn_right(duration)
        elif command == 'stop':
            success = robot.stop()
        else:
            return jsonify({'status': 'error', 'message': f'未知命令: {command}'})
        
        if success:
            return jsonify({'status': 'success', 'command': command})
        else:
            return jsonify({'status': 'error', 'message': '命令执行失败'})
            
    except Exception as e:
        logger.error(f"控制命令错误: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/sensors')
def get_sensors():
    """传感器数据API"""
    return jsonify({
        'left_ir': False,
        'right_ir': False,
        'ultrasonic': 50,
        'last_update': int(time.time())
    })

@app.route('/status')
def get_status():
    """系统状态API"""
    return jsonify({
        'robot_connected': robot.connected,
        'timestamp': int(time.time())
    })

if __name__ == '__main__':
    print("🤖 简化版机器人Web控制启动")
    print("🌐 访问地址: http://0.0.0.0:5000")
    print("🔧 调试模式: 仅包含基本Web控制功能")
    
    app.run(host='0.0.0.0', port=5000, debug=False)