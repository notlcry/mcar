#!/usr/bin/env python3
"""
使用Python原生音频处理的唤醒词检测
避免PyAudio的兼容性问题，使用更简单的音频获取方法
"""

import os
import sys
import time
import signal
import threading
import struct
import numpy as np
from scipy import signal as scipy_signal
import wave
import tempfile

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

# 导入音频库
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
    print("✅ sounddevice模块可用")
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    print("⚠️ sounddevice模块不可用")

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
    print("✅ pyaudio模块可用")
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("⚠️ pyaudio模块不可用")

# 导入Porcupine
try:
    import pvporcupine
    print("✅ Porcupine模块导入成功")
except ImportError as e:
    print(f"❌ 导入Porcupine失败: {e}")
    sys.exit(1)

class PythonAudioWakeWordDetector:
    """使用Python原生音频处理的唤醒词检测器"""
    
    def __init__(self):
        self.porcupine = None
        self.is_listening = False
        self.detection_callback = None
        self.detection_thread = None
        self.audio_method = None
        self.stream = None
        
        # 音频参数
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 512
        
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
            
            # 使用Porcupine要求的参数
            self.sample_rate = self.porcupine.sample_rate
            self.chunk_size = self.porcupine.frame_length
            
            print(f"✅ Porcupine初始化成功")
            print(f"🔑 唤醒词文件: {wake_word_file}")
            print(f"🌐 中文模型: {model_file}")
            print(f"📊 采样率: {self.sample_rate}Hz")
            print(f"📏 帧长度: {self.chunk_size}")
            
            return True
            
        except Exception as e:
            print(f"❌ Porcupine初始化失败: {e}")
            return False
    
    def _setup_sounddevice_audio(self):
        """设置sounddevice音频"""
        try:
            # 列出音频设备
            devices = sd.query_devices()
            print("📊 可用音频设备:")
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    print(f"  设备 {i}: {device['name']} (输入通道: {device['max_input_channels']})")
            
            # 查找ReSpeaker设备
            respeaker_device = None
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    name = device['name'].lower()
                    if 'array' in name or 'respeaker' in name or 'seeed' in name:
                        respeaker_device = i
                        print(f"✅ 找到ReSpeaker设备: {device['name']}")
                        break
            
            # 测试音频录制
            test_duration = 0.1
            try:
                test_audio = sd.rec(
                    int(test_duration * self.sample_rate),
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    device=respeaker_device,
                    dtype=np.int16
                )
                sd.wait()  # 等待录制完成
                
                if test_audio is not None and len(test_audio) > 0:
                    self.audio_method = 'sounddevice'
                    self.device_id = respeaker_device
                    print(f"✅ sounddevice音频测试成功")
                    return True
                
            except Exception as e:
                print(f"⚠️ sounddevice测试失败: {e}")
                return False
                
        except Exception as e:
            print(f"⚠️ sounddevice设置失败: {e}")
            return False
    
    def _setup_pyaudio_simple(self):
        """设置简化的PyAudio音频"""
        try:
            pa = pyaudio.PyAudio()
            
            # 使用默认设备和最基本的设置
            try:
                self.stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size,
                    input_device_index=None  # 使用默认设备
                )
                
                # 测试读取
                test_data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                if test_data:
                    self.audio_method = 'pyaudio_simple'
                    print("✅ 简化PyAudio音频测试成功")
                    return True
                
            except Exception as e:
                print(f"⚠️ 简化PyAudio测试失败: {e}")
                if self.stream:
                    self.stream.close()
                    self.stream = None
                return False
                
        except Exception as e:
            print(f"⚠️ PyAudio设置失败: {e}")
            return False
    
    def start_detection(self, callback):
        """开始检测"""
        if not self.porcupine:
            print("❌ Porcupine未初始化")
            return False
        
        self.detection_callback = callback
        self.is_listening = True
        
        # 尝试不同的音频方法
        audio_setup_success = False
        
        if SOUNDDEVICE_AVAILABLE and not audio_setup_success:
            print("🔧 尝试使用sounddevice...")
            audio_setup_success = self._setup_sounddevice_audio()
        
        if PYAUDIO_AVAILABLE and not audio_setup_success:
            print("🔧 尝试使用简化PyAudio...")
            audio_setup_success = self._setup_pyaudio_simple()
        
        if not audio_setup_success:
            print("❌ 所有音频方法都失败了")
            return False
        
        # 启动检测线程
        self.detection_thread = threading.Thread(target=self._detection_worker, daemon=True)
        self.detection_thread.start()
        
        return True
    
    def stop_detection(self):
        """停止检测"""
        self.is_listening = False
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None
        
        if self.detection_thread:
            self.detection_thread.join(timeout=2)
    
    def _detection_worker(self):
        """检测工作线程"""
        print(f"🎤 启动{self.audio_method}录音检测线程...")
        
        consecutive_errors = 0
        max_errors = 10
        
        try:
            while self.is_listening:
                try:
                    # 根据音频方法读取数据
                    if self.audio_method == 'sounddevice':
                        # 使用sounddevice录制
                        audio_chunk = sd.rec(
                            self.chunk_size,
                            samplerate=self.sample_rate,
                            channels=self.channels,
                            device=self.device_id,
                            dtype=np.int16
                        )
                        sd.wait()  # 等待录制完成
                        audio_data = audio_chunk.flatten()
                        
                    elif self.audio_method == 'pyaudio_simple':
                        # 使用PyAudio录制
                        raw_data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                        audio_data = np.frombuffer(raw_data, dtype=np.int16)
                        
                    else:
                        print("❌ 未知的音频方法")
                        break
                    
                    if len(audio_data) != self.chunk_size:
                        print(f"⚠️ 音频数据长度不匹配: {len(audio_data)} != {self.chunk_size}")
                        continue
                    
                    # 检测唤醒词
                    keyword_index = self.porcupine.process(audio_data)
                    
                    if keyword_index >= 0:
                        print(f"\n🎉 检测到唤醒词 '快快'！索引: {keyword_index}")
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
                    time.sleep(0.01)
                    continue
                    
        except Exception as e:
            print(f"❌ 检测线程错误: {e}")
        
        print("🛑 检测线程结束")

# 测试代码
def signal_handler(sig, frame):
    print('\n🛑 停止测试...')
    if 'detector' in globals():
        detector.stop_detection()
    sys.exit(0)

def on_wake_word(keyword_index):
    print(f"🎉 检测到唤醒词！索引: {keyword_index}")
    print("✨ 唤醒词检测正常工作!")
    print("🔊 请继续说话测试...")

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)

print("🧪 Python原生音频唤醒词检测测试")
print("=" * 50)

try:
    # 初始化检测器
    detector = PythonAudioWakeWordDetector()
    
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

finally:
    print("\n📊 测试总结:")
    print("   如果成功检测到唤醒词，说明系统工作正常")
    print("   如果没有检测到，请检查:")
    print("   - 麦克风设备是否正常")
    print("   - 环境噪音是否过大")
    print("   - 发音是否清晰")
    print("   - 音量是否合适")