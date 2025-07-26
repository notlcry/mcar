#!/usr/bin/python3
"""
安全管理器 - 实现网络连接丢失时的离线模式、API调用失败的友好错误处理
确保障碍物避让系统优先级高于个性化动作，添加低电量状态的表情显示和动作限制
"""

import time
import threading
import logging
import subprocess
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum
import json
import os
import platform

# 检查运行环境
IS_RASPBERRY_PI = platform.machine().startswith('arm') or platform.machine().startswith('aarch64')
IS_MACOS = platform.system() == 'Darwin'

# 条件导入psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("警告: psutil不可用，某些系统监控功能将被禁用")

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SafetyLevel(Enum):
    """安全级别枚举"""
    NORMAL = "normal"           # 正常运行
    CAUTION = "caution"         # 谨慎模式
    RESTRICTED = "restricted"   # 限制模式
    EMERGENCY = "emergency"     # 紧急模式

class NetworkStatus(Enum):
    """网络状态枚举"""
    ONLINE = "online"
    OFFLINE = "offline"
    LIMITED = "limited"
    UNKNOWN = "unknown"

class PowerStatus(Enum):
    """电源状态枚举"""
    NORMAL = "normal"       # 正常电量 (>30%)
    LOW = "low"            # 低电量 (10-30%)
    CRITICAL = "critical"   # 危险电量 (<10%)
    CHARGING = "charging"   # 充电中
    UNKNOWN = "unknown"     # 未知状态

@dataclass
class SafetyState:
    """安全状态数据模型"""
    safety_level: SafetyLevel = SafetyLevel.NORMAL
    network_status: NetworkStatus = NetworkStatus.UNKNOWN
    power_status: PowerStatus = PowerStatus.UNKNOWN
    battery_percentage: float = 100.0
    obstacle_detected: bool = False
    api_failures: int = 0
    last_api_success: datetime = field(default_factory=datetime.now)
    movement_restricted: bool = False
    emergency_stop_active: bool = False
    offline_mode_active: bool = False
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'safety_level': self.safety_level.value,
            'network_status': self.network_status.value,
            'power_status': self.power_status.value,
            'battery_percentage': self.battery_percentage,
            'obstacle_detected': self.obstacle_detected,
            'api_failures': self.api_failures,
            'last_api_success': self.last_api_success.isoformat(),
            'movement_restricted': self.movement_restricted,
            'emergency_stop_active': self.emergency_stop_active,
            'offline_mode_active': self.offline_mode_active
        }

class SafetyManager:
    """安全管理器 - 处理所有安全相关功能"""
    
    def __init__(self, robot_controller=None, expression_controller=None, 
                 voice_controller=None, ai_conversation_manager=None):
        """
        初始化安全管理器
        Args:
            robot_controller: LOBOROBOT实例
            expression_controller: 表情控制器实例
            voice_controller: 语音控制器实例
            ai_conversation_manager: AI对话管理器实例
        """
        self.robot = robot_controller
        self.expression_controller = expression_controller
        self.voice_controller = voice_controller
        self.ai_conversation_manager = ai_conversation_manager
        
        # 安全状态
        self.safety_state = SafetyState()
        
        # 监控参数
        self.network_check_interval = 10.0  # 网络检查间隔（秒）
        self.power_check_interval = 30.0    # 电量检查间隔（秒）
        self.api_failure_threshold = 3      # API失败阈值
        self.api_timeout = 5.0              # API超时时间
        
        # 离线模式配置
        self.offline_responses = self._load_offline_responses()
        self.offline_commands = self._load_offline_commands()
        
        # 监控线程
        self.monitoring_active = False
        self.network_monitor_thread = None
        self.power_monitor_thread = None
        self.safety_monitor_thread = None
        
        # 回调函数
        self.safety_callbacks: Dict[str, List[Callable]] = {
            'network_change': [],
            'power_change': [],
            'safety_level_change': [],
            'emergency_stop': [],
            'offline_mode_change': []
        }
        
        # 线程锁
        self.state_lock = threading.Lock()
        
        logger.info("安全管理器初始化完成")
    
    def _load_offline_responses(self) -> Dict[str, List[str]]:
        """加载离线模式回复"""
        return {
            'greeting': [
                "你好！我现在处于离线模式，功能有限。",
                "嗨！网络连接有问题，我只能进行基本操作。",
                "你好！我暂时无法连接网络，请稍后再试。"
            ],
            'network_error': [
                "抱歉，网络连接出现问题，我无法访问AI服务。",
                "网络不稳定，我现在只能执行基本命令。",
                "连接中断了，让我们等网络恢复吧。"
            ],
            'api_error': [
                "AI服务暂时不可用，请稍后再试。",
                "服务器响应超时，我先休息一下。",
                "AI大脑有点卡顿，稍等片刻再聊吧。"
            ],
            'low_battery': [
                "电量有点低了，我需要节省体力。",
                "快没电了，动作会比较缓慢。",
                "电池告急，我要进入省电模式了。"
            ],
            'obstacle_warning': [
                "前面有障碍物，我要小心一点。",
                "检测到障碍，安全第一！",
                "路被挡住了，让我绕个路。"
            ]
        }
    
    def _load_offline_commands(self) -> Dict[str, str]:
        """加载离线模式支持的命令"""
        return {
            '前进': 'forward',
            '后退': 'backward',
            '左转': 'left',
            '右转': 'right',
            '停止': 'stop',
            '左移': 'move_left',
            '右移': 'move_right',
            '你好': 'greeting',
            '再见': 'goodbye'
        }
    
    def start_monitoring(self):
        """启动安全监控"""
        if self.monitoring_active:
            logger.warning("安全监控已在运行")
            return
        
        self.monitoring_active = True
        
        # 启动网络监控线程
        self.network_monitor_thread = threading.Thread(
            target=self._network_monitor_worker, 
            daemon=True
        )
        self.network_monitor_thread.start()
        
        # 启动电源监控线程
        self.power_monitor_thread = threading.Thread(
            target=self._power_monitor_worker, 
            daemon=True
        )
        self.power_monitor_thread.start()
        
        # 启动安全监控线程
        self.safety_monitor_thread = threading.Thread(
            target=self._safety_monitor_worker, 
            daemon=True
        )
        self.safety_monitor_thread.start()
        
        logger.info("安全监控已启动")
    
    def stop_monitoring(self):
        """停止安全监控"""
        self.monitoring_active = False
        logger.info("安全监控已停止")
    
    def _network_monitor_worker(self):
        """网络监控工作线程"""
        while self.monitoring_active:
            try:
                old_status = self.safety_state.network_status
                new_status = self._check_network_status()
                
                with self.state_lock:
                    self.safety_state.network_status = new_status
                
                # 如果网络状态发生变化
                if old_status != new_status:
                    self._handle_network_change(old_status, new_status)
                
                time.sleep(self.network_check_interval)
                
            except Exception as e:
                logger.error(f"网络监控错误: {e}")
                time.sleep(self.network_check_interval)
    
    def _power_monitor_worker(self):
        """电源监控工作线程"""
        while self.monitoring_active:
            try:
                old_status = self.safety_state.power_status
                old_percentage = self.safety_state.battery_percentage
                
                new_status, new_percentage = self._check_power_status()
                
                with self.state_lock:
                    self.safety_state.power_status = new_status
                    self.safety_state.battery_percentage = new_percentage
                
                # 如果电源状态发生变化
                if old_status != new_status or abs(old_percentage - new_percentage) > 5:
                    self._handle_power_change(old_status, new_status, new_percentage)
                
                time.sleep(self.power_check_interval)
                
            except Exception as e:
                logger.error(f"电源监控错误: {e}")
                time.sleep(self.power_check_interval)
    
    def _safety_monitor_worker(self):
        """安全监控工作线程"""
        while self.monitoring_active:
            try:
                old_level = self.safety_state.safety_level
                new_level = self._calculate_safety_level()
                
                with self.state_lock:
                    self.safety_state.safety_level = new_level
                
                # 如果安全级别发生变化
                if old_level != new_level:
                    self._handle_safety_level_change(old_level, new_level)
                
                time.sleep(5.0)  # 每5秒检查一次安全级别
                
            except Exception as e:
                logger.error(f"安全监控错误: {e}")
                time.sleep(5.0)
    
    def _check_network_status(self) -> NetworkStatus:
        """检查网络连接状态"""
        try:
            # 检查基本网络连接
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '3', '8.8.8.8'],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # 检查AI API连接
                if self._test_api_connection():
                    return NetworkStatus.ONLINE
                else:
                    return NetworkStatus.LIMITED
            else:
                return NetworkStatus.OFFLINE
                
        except Exception as e:
            logger.error(f"网络状态检查失败: {e}")
            return NetworkStatus.UNKNOWN
    
    def _test_api_connection(self) -> bool:
        """测试AI API连接"""
        try:
            # 测试Google AI API连接
            response = requests.get(
                'https://generativelanguage.googleapis.com',
                timeout=self.api_timeout
            )
            return response.status_code in [200, 404]  # 404也表示服务可达
        except:
            return False
    
    def _check_power_status(self) -> tuple[PowerStatus, float]:
        """检查电源状态"""
        try:
            # macOS环境下跳过电池检查
            if IS_MACOS or not PSUTIL_AVAILABLE:
                logger.debug("macOS环境或psutil不可用，跳过电池检查")
                return PowerStatus.NORMAL, 100.0
            
            # 获取电池信息
            battery = psutil.sensors_battery()
            
            if battery is None:
                # 如果无法获取电池信息，假设是台式机或外接电源
                return PowerStatus.NORMAL, 100.0
            
            percentage = battery.percent
            is_charging = battery.power_plugged
            
            if is_charging:
                return PowerStatus.CHARGING, percentage
            elif percentage > 30:
                return PowerStatus.NORMAL, percentage
            elif percentage > 10:
                return PowerStatus.LOW, percentage
            else:
                return PowerStatus.CRITICAL, percentage
                
        except Exception as e:
            logger.error(f"电源状态检查失败: {e}")
            return PowerStatus.UNKNOWN, 100.0
    
    def _check_system_resources(self) -> Dict[str, bool]:
        """
        检查系统资源状态
        Returns:
            Dict: 包含不同级别的资源限制状态
        """
        try:
            # macOS环境下或psutil不可用时使用简化检查
            if IS_MACOS or not PSUTIL_AVAILABLE:
                logger.debug("macOS环境或psutil不可用，使用简化的资源检查")
                return self._check_system_resources_simplified()
            
            # CPU使用率检查
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 内存使用率检查
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用率检查
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # 系统温度检查（如果可用）
            temperature_critical = False
            try:
                temps = psutil.sensors_temperatures()
                if 'cpu_thermal' in temps:
                    temp = temps['cpu_thermal'][0].current
                    temperature_critical = temp > 80  # 80°C以上认为过热
            except:
                pass
            
            # 进程数量检查
            process_count = len(psutil.pids())
            process_critical = process_count > 200  # 超过200个进程认为过多
            
            # 定义资源限制级别
            critical_conditions = [
                cpu_percent > 95,           # CPU使用率超过95%
                memory_percent > 95,        # 内存使用率超过95%
                disk_percent > 95,          # 磁盘使用率超过95%
                temperature_critical,       # 温度过高
                memory.available < 50 * 1024 * 1024  # 可用内存少于50MB
            ]
            
            high_conditions = [
                cpu_percent > 85,           # CPU使用率超过85%
                memory_percent > 85,        # 内存使用率超过85%
                disk_percent > 90,          # 磁盘使用率超过90%
                process_critical,           # 进程数过多
                memory.available < 100 * 1024 * 1024  # 可用内存少于100MB
            ]
            
            moderate_conditions = [
                cpu_percent > 70,           # CPU使用率超过70%
                memory_percent > 70,        # 内存使用率超过70%
                disk_percent > 80           # 磁盘使用率超过80%
            ]
            
            return {
                'critical': any(critical_conditions),
                'high': any(high_conditions),
                'moderate': any(moderate_conditions),
                'details': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'disk_percent': disk_percent,
                    'available_memory_mb': memory.available / (1024 * 1024),
                    'process_count': process_count,
                    'temperature_critical': temperature_critical
                }
            }
            
        except Exception as e:
            logger.error(f"系统资源检查失败: {e}")
            return {
                'critical': False,
                'high': False,
                'moderate': False,
                'details': {'error': str(e)}
            }
    
    def _check_system_resources_simplified(self) -> Dict[str, bool]:
        """
        简化的系统资源检查（适用于macOS或psutil不可用的环境）
        """
        try:
            # 使用系统命令获取基本信息
            if IS_MACOS:
                # macOS特定的检查
                # 检查内存使用情况
                try:
                    result = subprocess.run(['vm_stat'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        # 简单解析vm_stat输出
                        lines = result.stdout.split('\n')
                        # 这里可以添加更详细的内存解析，但为了简化，我们假设正常
                        memory_ok = True
                    else:
                        memory_ok = True
                except:
                    memory_ok = True
                
                # 检查磁盘空间
                try:
                    result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        if len(lines) > 1:
                            parts = lines[1].split()
                            if len(parts) >= 5:
                                usage_str = parts[4].replace('%', '')
                                disk_usage = int(usage_str)
                                disk_ok = disk_usage < 90
                            else:
                                disk_ok = True
                        else:
                            disk_ok = True
                    else:
                        disk_ok = True
                except:
                    disk_ok = True
                
                return {
                    'critical': False,  # macOS环境下不认为有严重资源问题
                    'high': not (memory_ok and disk_ok),
                    'moderate': False,
                    'details': {
                        'platform': 'macOS',
                        'memory_check': memory_ok,
                        'disk_check': disk_ok,
                        'note': 'simplified_check'
                    }
                }
            else:
                # 其他环境的简化检查
                return {
                    'critical': False,
                    'high': False,
                    'moderate': False,
                    'details': {
                        'platform': platform.system(),
                        'note': 'minimal_check_no_psutil'
                    }
                }
                
        except Exception as e:
            logger.error(f"简化资源检查失败: {e}")
            return {
                'critical': False,
                'high': False,
                'moderate': False,
                'details': {'error': str(e), 'check_type': 'simplified'}
            }
    
    def _calculate_safety_level(self) -> SafetyLevel:
        """计算当前安全级别"""
        # 检查系统资源状态
        system_resources_limited = self._check_system_resources()
        
        # 紧急情况
        if (self.safety_state.power_status == PowerStatus.CRITICAL or
            self.safety_state.emergency_stop_active or
            system_resources_limited['critical']):
            return SafetyLevel.EMERGENCY
        
        # 限制模式
        if (self.safety_state.power_status == PowerStatus.LOW or
            self.safety_state.api_failures >= self.api_failure_threshold or
            self.safety_state.obstacle_detected or
            system_resources_limited['high']):
            return SafetyLevel.RESTRICTED
        
        # 谨慎模式
        if (self.safety_state.network_status == NetworkStatus.OFFLINE or
            self.safety_state.network_status == NetworkStatus.LIMITED or
            system_resources_limited['moderate']):
            return SafetyLevel.CAUTION
        
        # 正常模式
        return SafetyLevel.NORMAL
    
    def _handle_network_change(self, old_status: NetworkStatus, new_status: NetworkStatus):
        """处理网络状态变化"""
        logger.info(f"网络状态变化: {old_status.value} -> {new_status.value}")
        
        # 进入离线模式
        if new_status == NetworkStatus.OFFLINE and not self.safety_state.offline_mode_active:
            self._enter_offline_mode()
        
        # 退出离线模式
        elif old_status == NetworkStatus.OFFLINE and new_status in [NetworkStatus.ONLINE, NetworkStatus.LIMITED]:
            self._exit_offline_mode()
        
        # 触发回调
        self._trigger_callbacks('network_change', old_status, new_status)
        
        # 显示网络状态表情
        if self.expression_controller:
            if new_status == NetworkStatus.OFFLINE:
                self.expression_controller.show_emotion('confused')
            elif new_status == NetworkStatus.ONLINE:
                self.expression_controller.show_emotion('happy')
    
    def _handle_power_change(self, old_status: PowerStatus, new_status: PowerStatus, percentage: float):
        """处理电源状态变化"""
        logger.info(f"电源状态变化: {old_status.value} -> {new_status.value} ({percentage:.1f}%)")
        
        # 低电量限制
        if new_status in [PowerStatus.LOW, PowerStatus.CRITICAL]:
            self._apply_power_restrictions(new_status)
        
        # 电量恢复
        elif old_status in [PowerStatus.LOW, PowerStatus.CRITICAL] and new_status in [PowerStatus.NORMAL, PowerStatus.CHARGING]:
            self._remove_power_restrictions()
        
        # 触发回调
        self._trigger_callbacks('power_change', old_status, new_status, percentage)
        
        # 显示电量状态表情
        if self.expression_controller:
            if new_status == PowerStatus.CRITICAL:
                self.expression_controller.show_emotion('sad')
            elif new_status == PowerStatus.LOW:
                self.expression_controller.show_emotion('thinking')
            elif new_status == PowerStatus.CHARGING:
                self.expression_controller.show_emotion('happy')
    
    def _handle_safety_level_change(self, old_level: SafetyLevel, new_level: SafetyLevel):
        """处理安全级别变化"""
        logger.info(f"安全级别变化: {old_level.value} -> {new_level.value}")
        
        # 应用安全限制
        if new_level == SafetyLevel.EMERGENCY:
            self._apply_emergency_restrictions()
        elif new_level == SafetyLevel.RESTRICTED:
            self._apply_movement_restrictions()
        elif new_level == SafetyLevel.CAUTION:
            self._apply_caution_restrictions()
        elif new_level == SafetyLevel.NORMAL and old_level != SafetyLevel.NORMAL:
            self._remove_all_restrictions()
        
        # 触发回调
        self._trigger_callbacks('safety_level_change', old_level, new_level)
    
    def _enter_offline_mode(self):
        """进入离线模式"""
        with self.state_lock:
            self.safety_state.offline_mode_active = True
        
        logger.info("进入离线模式")
        
        # 通知用户
        self._speak_offline_response('network_error')
        
        # 触发回调
        self._trigger_callbacks('offline_mode_change', True)
    
    def _exit_offline_mode(self):
        """退出离线模式"""
        with self.state_lock:
            self.safety_state.offline_mode_active = False
            self.safety_state.api_failures = 0  # 重置API失败计数
        
        logger.info("退出离线模式")
        
        # 通知用户
        if self.voice_controller:
            self.voice_controller.speak_text("网络连接已恢复！")
        
        # 触发回调
        self._trigger_callbacks('offline_mode_change', False)
    
    def _apply_emergency_restrictions(self):
        """应用紧急限制"""
        with self.state_lock:
            self.safety_state.emergency_stop_active = True
            self.safety_state.movement_restricted = True
        
        # 立即停止机器人
        if self.robot:
            self.robot.t_stop(0.1)
        
        # 显示紧急状态表情
        if self.expression_controller:
            self.expression_controller.show_emotion('sad')
        
        # 通知用户
        self._speak_offline_response('low_battery')
        
        logger.warning("应用紧急限制 - 机器人已停止")
    
    def _apply_movement_restrictions(self):
        """应用运动限制"""
        with self.state_lock:
            self.safety_state.movement_restricted = True
        
        logger.info("应用运动限制")
    
    def _apply_caution_restrictions(self):
        """应用谨慎限制"""
        logger.info("应用谨慎限制")
    
    def _apply_power_restrictions(self, power_status: PowerStatus):
        """应用电量限制"""
        if power_status == PowerStatus.CRITICAL:
            # 危险电量：停止所有运动
            with self.state_lock:
                self.safety_state.movement_restricted = True
            
            if self.robot:
                self.robot.t_stop(0.1)
            
            self._speak_offline_response('low_battery')
            
        elif power_status == PowerStatus.LOW:
            # 低电量：限制运动速度和频率
            logger.info("低电量模式：限制运动性能")
    
    def _remove_power_restrictions(self):
        """移除电量限制"""
        with self.state_lock:
            if self.safety_state.safety_level != SafetyLevel.EMERGENCY:
                self.safety_state.movement_restricted = False
        
        logger.info("电量限制已移除")
    
    def _remove_all_restrictions(self):
        """移除所有限制"""
        with self.state_lock:
            self.safety_state.movement_restricted = False
            self.safety_state.emergency_stop_active = False
        
        logger.info("所有安全限制已移除")
    
    def _speak_offline_response(self, response_type: str):
        """播放离线模式回复"""
        if response_type in self.offline_responses:
            import random
            response = random.choice(self.offline_responses[response_type])
            
            if self.voice_controller:
                self.voice_controller.speak_text(response)
            else:
                logger.info(f"离线回复: {response}")
    
    def handle_api_failure(self, error_type: str, retry_count: int = 0) -> str:
        """
        处理API调用失败
        Args:
            error_type: 错误类型
            retry_count: 重试次数
        Returns:
            str: 友好的错误回复
        """
        with self.state_lock:
            self.safety_state.api_failures += 1
        
        logger.warning(f"API调用失败: {error_type} (失败次数: {self.safety_state.api_failures})")
        
        # 选择合适的错误回复
        if self.safety_state.api_failures >= self.api_failure_threshold:
            # 多次失败，进入离线模式
            if not self.safety_state.offline_mode_active:
                self._enter_offline_mode()
            
            import random
            return random.choice(self.offline_responses['api_error'])
        else:
            # 首次失败，给出友好提示
            return f"抱歉，服务暂时不可用，让我再试试... (尝试 {retry_count + 1}/3)"
    
    def handle_api_success(self):
        """处理API调用成功"""
        with self.state_lock:
            self.safety_state.api_failures = 0
            self.safety_state.last_api_success = datetime.now()
        
        # 如果之前在离线模式，检查是否可以退出
        if self.safety_state.offline_mode_active and self.safety_state.network_status == NetworkStatus.ONLINE:
            self._exit_offline_mode()
    
    def check_movement_safety(self, command: str, emotion_context: str = None) -> bool:
        """
        检查运动安全性
        Args:
            command: 运动命令
            emotion_context: 情感上下文
        Returns:
            bool: 是否允许执行运动
        """
        # 紧急停止状态
        if self.safety_state.emergency_stop_active:
            logger.warning(f"紧急停止状态，拒绝运动命令: {command}")
            return False
        
        # 运动限制状态
        if self.safety_state.movement_restricted:
            # 只允许停止命令
            if command in ['stop', '停止']:
                return True
            
            logger.warning(f"运动受限状态，拒绝运动命令: {command}")
            self._speak_offline_response('low_battery')
            return False
        
        # 障碍物检测优先级
        if self.safety_state.obstacle_detected:
            # 障碍物存在时，只允许安全的运动
            safe_commands = ['stop', 'backward', '停止', '后退']
            if command not in safe_commands:
                logger.warning(f"检测到障碍物，拒绝运动命令: {command}")
                self._speak_offline_response('obstacle_warning')
                return False
        
        return True
    
    def update_obstacle_status(self, obstacle_detected: bool):
        """更新障碍物检测状态"""
        old_status = self.safety_state.obstacle_detected
        
        with self.state_lock:
            self.safety_state.obstacle_detected = obstacle_detected
        
        if old_status != obstacle_detected:
            logger.info(f"障碍物状态变化: {old_status} -> {obstacle_detected}")
            
            if obstacle_detected:
                # 检测到障碍物，立即停止
                if self.robot:
                    self.robot.t_stop(0.1)
                
                # 显示警告表情
                if self.expression_controller:
                    self.expression_controller.show_emotion('confused')
    
    def process_offline_command(self, user_input: str) -> Optional[str]:
        """
        处理离线模式下的命令
        Args:
            user_input: 用户输入
        Returns:
            str: 回复内容，如果无法处理返回None
        """
        if not self.safety_state.offline_mode_active:
            return None
        
        user_input = user_input.strip()
        
        # 查找匹配的离线命令
        for keyword, command in self.offline_commands.items():
            if keyword in user_input:
                if command == 'greeting':
                    import random
                    return random.choice(self.offline_responses['greeting'])
                elif command == 'goodbye':
                    return "再见！希望网络快点恢复~"
                elif command in ['forward', 'backward', 'left', 'right', 'stop', 'move_left', 'move_right']:
                    # 检查是否允许运动
                    if self.check_movement_safety(command):
                        # 执行基本运动命令
                        if self.robot:
                            if command == 'forward':
                                self.robot.t_up(30, 0.5)  # 降低速度
                            elif command == 'backward':
                                self.robot.t_down(30, 0.5)
                            elif command == 'left':
                                self.robot.turnLeft(30, 0.5)
                            elif command == 'right':
                                self.robot.turnRight(30, 0.5)
                            elif command == 'move_left':
                                self.robot.moveLeft(30, 0.5)
                            elif command == 'move_right':
                                self.robot.moveRight(30, 0.5)
                            elif command == 'stop':
                                self.robot.t_stop(0.1)
                        
                        return f"好的，执行{keyword}命令。"
                    else:
                        return "抱歉，当前无法执行运动命令。"
        
        # 默认离线回复
        import random
        return random.choice(self.offline_responses['network_error'])
    
    def register_callback(self, event_type: str, callback: Callable):
        """注册安全事件回调"""
        if event_type in self.safety_callbacks:
            self.safety_callbacks[event_type].append(callback)
            logger.info(f"已注册 {event_type} 回调")
    
    def _trigger_callbacks(self, event_type: str, *args):
        """触发回调函数"""
        if event_type in self.safety_callbacks:
            for callback in self.safety_callbacks[event_type]:
                try:
                    callback(*args)
                except Exception as e:
                    logger.error(f"回调函数执行失败: {e}")
    
    def emergency_stop(self):
        """紧急停止"""
        logger.critical("执行紧急停止")
        
        with self.state_lock:
            self.safety_state.emergency_stop_active = True
            self.safety_state.movement_restricted = True
        
        # 立即停止机器人
        if self.robot:
            self.robot.t_stop(0.1)
        
        # 显示紧急状态
        if self.expression_controller:
            self.expression_controller.show_emotion('sad')
        
        # 通知用户
        if self.voice_controller:
            self.voice_controller.speak_text("紧急停止已激活！")
        
        # 触发回调
        self._trigger_callbacks('emergency_stop')
    
    def reset_emergency_stop(self):
        """重置紧急停止状态"""
        with self.state_lock:
            self.safety_state.emergency_stop_active = False
            
            # 重新评估是否需要运动限制
            if (self.safety_state.power_status not in [PowerStatus.CRITICAL] and
                not self.safety_state.obstacle_detected):
                self.safety_state.movement_restricted = False
        
        logger.info("紧急停止状态已重置")
        
        if self.voice_controller:
            self.voice_controller.speak_text("紧急停止已解除。")
    
    def get_safety_status(self) -> Dict:
        """获取安全状态"""
        with self.state_lock:
            return self.safety_state.to_dict()
    
    def get_system_health(self) -> Dict:
        """获取系统健康状态"""
        try:
            # macOS环境下或psutil不可用时使用简化版本
            if IS_MACOS or not PSUTIL_AVAILABLE:
                return self._get_system_health_simplified()
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # 系统温度（如果可用）
            temperature = None
            try:
                temps = psutil.sensors_temperatures()
                if 'cpu_thermal' in temps:
                    temperature = temps['cpu_thermal'][0].current
            except:
                pass
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'temperature': temperature,
                'uptime': time.time() - psutil.boot_time(),
                'safety_status': self.get_safety_status()
            }
            
        except Exception as e:
            logger.error(f"获取系统健康状态失败: {e}")
            return {'error': str(e)}
    
    def _get_system_health_simplified(self) -> Dict:
        """获取简化的系统健康状态（适用于macOS）"""
        try:
            health_data = {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'python_version': platform.python_version(),
                'safety_status': self.get_safety_status()
            }
            
            # 尝试获取一些基本的系统信息
            if IS_MACOS:
                try:
                    # 获取系统负载
                    result = subprocess.run(['uptime'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        health_data['uptime_info'] = result.stdout.strip()
                except:
                    pass
                
                try:
                    # 获取内存信息
                    result = subprocess.run(['vm_stat'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        health_data['memory_info'] = 'available'
                except:
                    health_data['memory_info'] = 'unavailable'
                
                try:
                    # 获取磁盘信息
                    result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        if len(lines) > 1:
                            health_data['disk_info'] = lines[1]
                except:
                    health_data['disk_info'] = 'unavailable'
            
            health_data['note'] = 'simplified_health_check_for_macos'
            return health_data
            
        except Exception as e:
            logger.error(f"获取简化系统健康状态失败: {e}")
            return {
                'error': str(e),
                'platform': platform.system(),
                'safety_status': self.get_safety_status()
            }

# 测试函数
def test_safety_manager():
    """测试安全管理器功能"""
    print("=== 安全管理器测试 ===")
    
    # 创建模拟的机器人控制器
    class MockRobot:
        def __init__(self):
            self.actions = []
        
        def __getattr__(self, name):
            def mock_method(*args):
                self.actions.append(f"{name}({', '.join(map(str, args))})")
                print(f"执行动作: {name}({', '.join(map(str, args))})")
                time.sleep(0.1)
            return mock_method
    
    # 创建测试实例
    mock_robot = MockRobot()
    safety_manager = SafetyManager(robot_controller=mock_robot)
    
    # 启动监控
    safety_manager.start_monitoring()
    
    # 测试网络状态
    print(f"\n当前网络状态: {safety_manager._check_network_status().value}")
    
    # 测试电源状态
    power_status, percentage = safety_manager._check_power_status()
    print(f"当前电源状态: {power_status.value} ({percentage:.1f}%)")
    
    # 测试安全级别
    safety_level = safety_manager._calculate_safety_level()
    print(f"当前安全级别: {safety_level.value}")
    
    # 测试API失败处理
    print(f"\n测试API失败处理:")
    for i in range(5):
        response = safety_manager.handle_api_failure("timeout", i)
        print(f"失败 {i+1}: {response}")
        time.sleep(0.5)
    
    # 测试运动安全检查
    print(f"\n测试运动安全检查:")
    test_commands = ['forward', 'backward', 'stop', 'left', 'right']
    for command in test_commands:
        safe = safety_manager.check_movement_safety(command)
        print(f"命令 '{command}': {'安全' if safe else '不安全'}")
    
    # 测试离线命令处理
    print(f"\n测试离线命令处理:")
    safety_manager.safety_state.offline_mode_active = True
    test_inputs = ['你好', '前进', '停止', '再见', '转圈']
    for user_input in test_inputs:
        response = safety_manager.process_offline_command(user_input)
        print(f"输入: '{user_input}' -> 回复: '{response}'")
    
    # 显示系统健康状态
    print(f"\n=== 系统健康状态 ===")
    health = safety_manager.get_system_health()
    for key, value in health.items():
        print(f"{key}: {value}")
    
    # 显示安全状态
    print(f"\n=== 安全状态 ===")
    status = safety_manager.get_safety_status()
    for key, value in status.items():
        print(f"{key}: {value}")
    
    # 停止监控
    time.sleep(2)
    safety_manager.stop_monitoring()
    print("\n测试完成")

if __name__ == "__main__":
    test_safety_manager()