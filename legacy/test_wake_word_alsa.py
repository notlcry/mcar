#!/usr/bin/env python3
"""
使用ALSA直接录音的唤醒词检测测试
绕过PyAudio的兼容性问题
"""

import os
import sys
import time
import signal
import subprocess
import threading
import struct
import numpy as np
from scipy import signal as scipy_signal

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 设置ALSA静音以减少错误输出
os.environ['ALSA_QUIET'] = '1'

# 加载环境变量
env_file = ".ai_pet_env"
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                if line.startswith('export '):
                    line = line[7:]
                key, value = line.split('=', 1)
                value = value.strip('"\'')
                os.environ[key] = value
    print("✅ 环境变量已加载")

# 导入Porcupine
try:
    import pvporcupine
    print("✅ Porcupine模块导入成功")
except ImportError as e:
    print(f"❌ 导入Porcupine失败: {e}")
    sys.exit(1)

class AlsaWakeWordDetector:
    """使用ALSA直接录音的唤醒词检测器"""
    
    def __init__(self):
        self.porcupine = None
        self.is_listening = False
        self.detection_callback = None
        self.alsa_process = None
        self.detection_thread = None
        
        # 初始化Porcupine
        self._initialize_porcupine()
    
    def _initialize_porcupine(self):
        """初始化Porcupine引擎"""
        try:
            access_key = os.getenv('PICOVOICE_ACCESS_KEY')
            if not access_key or access_key == 'your_picovoice_access_key_here':
                print("❌ 未设置PICOVOICE_ACCESS_KEY")
                return False
            
            # 查找唤醒词文件
            wake_word_file = None
            possible_paths = [
                'wake_words/kk_zh_raspberry-pi_v3_0_0.ppn',
                'src/wake_words/kk_zh_raspberry-pi_v3_0_0.ppn'
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    wake_word_file = path
                    break
            
            if not wake_word_file:
                print("❌ 未找到唤醒词文件")
                return False
            
            # 查找中文模型
            model_file = None
            possible_models = [
                'models/porcupine/porcupine_params_zh.pv',
                'src/models/porcupine/porcupine_params_zh.pv'
            ]
            
            for path in possible_models:
                if os.path.exists(path):
                    model_file = path
                    break
            
            if not model_file:
                print("❌ 未找到中文语言模型")
                return False
            
            # 创建Porcupine实例
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keyword_paths=[wake_word_file],
                model_path=model_file,
                sensitivities=[0.5]
            )
            
            print(f"✅ Porcupine初始化成功")
            print(f"🔑 唤醒词文件: {wake_word_file}")
            print(f"🌐 中文模型: {model_file}")
            print(f"📊 采样率: {self.porcupine.sample_rate}Hz")
            print(f"📏 帧长度: {self.porcupine.frame_length}")
            
            return True
            
        except Exception as e:
            print(f"❌ Porcupine初始化失败: {e}")
            return False
    
    def start_detection(self, callback):
        """开始检测"""
        if not self.porcupine:
            print("❌ Porcupine未初始化")
            return False
        
        self.detection_callback = callback
        self.is_listening = True
        
        # 启动检测线程
        self.detection_thread = threading.Thread(target=self._detection_worker, daemon=True)
        self.detection_thread.start()
        
        return True
    
    def stop_detection(self):
        """停止检测"""
        self.is_listening = False
        
        if self.alsa_process:
            try:
                self.alsa_process.terminate()
                self.alsa_process.wait(timeout=2)
            except:
                try:
                    self.alsa_process.kill()
                except:
                    pass
        
        if self.detection_thread:
            self.detection_thread.join(timeout=2)
    
    def _detection_worker(self):
        """检测工作线程"""
        print("🎤 启动ALSA录音检测线程...")
        
        # ALSA录音命令
        # 使用hw:1,0 (ReSpeaker设备) 或 hw:CARD=array
        alsa_commands = [
            # 尝试直接指定ReSpeaker设备
            ['arecord', '-D', 'hw:CARD=array', '-f', 'S16_LE', '-r', '48000', '-c', '2', '-t', 'raw'],
            ['arecord', '-D', 'plughw:1,0', '-f', 'S16_LE', '-r', '48000', '-c', '2', '-t', 'raw'],
            ['arecord', '-D', 'hw:1,0', '-f', 'S16_LE', '-r', '48000', '-c', '2', '-t', 'raw'],
            # 回退到默认设备
            ['arecord', '-f', 'S16_LE', '-r', '16000', '-c', '1', '-t', 'raw']
        ]
        
        alsa_process = None
        sample_rate = None
        channels = None
        
        # 尝试不同的ALSA命令
        for cmd in alsa_commands:
            if not self.is_listening:
                break
                
            try:
                print(f"🔧 尝试ALSA命令: {' '.join(cmd)}")
                alsa_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0
                )
                
                # 从命令中提取参数
                sample_rate = int(cmd[cmd.index('-r') + 1])
                channels = int(cmd[cmd.index('-c') + 1])
                
                # 测试是否能读取数据
                test_data = alsa_process.stdout.read(1024)
                if test_data:
                    print(f"✅ ALSA录音成功启动: {sample_rate}Hz, {channels}通道")
                    self.alsa_process = alsa_process
                    break
                else:
                    alsa_process.terminate()
                    alsa_process = None
                    
            except Exception as e:
                print(f"⚠️ ALSA命令失败: {e}")
                if alsa_process:
                    try:
                        alsa_process.terminate()
                    except:
                        pass
                    alsa_process = None
                continue
        
        if not alsa_process or not self.is_listening:
            print("❌ 所有ALSA录音方法都失败了")
            return
        
        print("🎧 开始唤醒词检测...")
        
        # 计算每帧需要的字节数
        bytes_per_sample = 2  # 16-bit
        samples_per_frame_device = int(self.porcupine.frame_length * sample_rate / self.porcupine.sample_rate)
        bytes_per_frame = samples_per_frame_device * channels * bytes_per_sample
        
        print(f"📊 每帧字节数: {bytes_per_frame}")
        
        consecutive_errors = 0
        max_errors = 10
        
        try:
            while self.is_listening and alsa_process.poll() is None:
                try:
                    # 读取音频数据
                    audio_data = alsa_process.stdout.read(bytes_per_frame)
                    
                    if not audio_data or len(audio_data) != bytes_per_frame:
                        consecutive_errors += 1
                        if consecutive_errors > max_errors:
                            print("❌ 连续读取错误过多")
                            break
                        continue
                    
                    # 转换为numpy数组
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    
                    # 如果是立体声，转换为单声道
                    if channels == 2:
                        audio_array = audio_array.reshape(-1, 2)
                        audio_array = audio_array[:, 0]  # 取左声道
                    
                    # 重采样到16kHz（如果需要）
                    if sample_rate != self.porcupine.sample_rate:
                        # 使用scipy进行重采样
                        target_samples = int(len(audio_array) * self.porcupine.sample_rate / sample_rate)
                        audio_array = scipy_signal.resample(audio_array, target_samples).astype(np.int16)
                    
                    # 确保长度正确
                    if len(audio_array) != self.porcupine.frame_length:
                        continue
                    
                    # 检测唤醒词
                    keyword_index = self.porcupine.process(audio_array)
                    
                    if keyword_index >= 0:
                        print(f"🎉 检测到唤醒词 '快快'！索引: {keyword_index}")
                        if self.detection_callback:
                            self.detection_callback(keyword_index)
                    
                    # 重置错误计数
                    consecutive_errors = 0
                    
                except Exception as e:
                    consecutive_errors += 1
                    print(f"⚠️ 处理音频数据错误: {e}")
                    if consecutive_errors > max_errors:
                        print("❌ 连续处理错误过多")
                        break
                    continue
                    
        except Exception as e:
            print(f"❌ 检测线程错误: {e}")
        
        finally:
            if alsa_process:
                try:
                    alsa_process.terminate()
                    alsa_process.wait(timeout=2)
                except:
                    try:
                        alsa_process.kill()
                    except:
                        pass
        
        print("🛑 检测线程结束")

# 测试代码
def signal_handler(sig, frame):
    print('\n🛑 停止测试...')
    if 'detector' in globals():
        detector.stop_detection()
    sys.exit(0)

def on_wake_word(keyword_index):
    print(f"\n🎉 检测到唤醒词！索引: {keyword_index}")
    print("✨ 唤醒词检测正常工作!")
    print("🔊 请继续说话测试...")

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)

print("🧪 ALSA直接录音唤醒词检测测试")
print("=" * 50)

try:
    # 初始化检测器
    detector = AlsaWakeWordDetector()
    
    if not detector.porcupine:
        print("❌ 初始化失败")
        sys.exit(1)
    
    # 启动检测
    if detector.start_detection(on_wake_word):
        print("✅ 唤醒词检测已启动")
        print("🗣️ 请清晰地说 '快快' 来测试...")
        print("⏱️ 测试将持续60秒，按Ctrl+C可提前停止")
        
        # 等待60秒或用户中断
        for i in range(60):
            time.sleep(1)
            if i % 15 == 14:
                print(f"⏰ 测试进行中... ({i+1}/60秒) - 请说 '快快'")
        
        print("\n⏰ 测试时间结束")
        detector.stop_detection()
        print("✅ 测试完成")
    else:
        print("❌ 启动失败")
        sys.exit(1)

except KeyboardInterrupt:
    print("\n🛑 用户中断测试")
    if 'detector' in globals():
        detector.stop_detection()

except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)