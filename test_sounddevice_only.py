#!/usr/bin/env python3
"""
专门测试sounddevice的唤醒词检测
"""

import os
import sys
import time
import signal
import threading
import numpy as np

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

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

try:
    import sounddevice as sd
    print("✅ sounddevice模块导入成功")
except ImportError as e:
    print(f"❌ 导入sounddevice失败: {e}")
    sys.exit(1)

try:
    import pvporcupine
    print("✅ Porcupine模块导入成功")
except ImportError as e:
    print(f"❌ 导入Porcupine失败: {e}")
    sys.exit(1)

class SoundDeviceWakeWordDetector:
    """专门使用sounddevice的唤醒词检测器"""
    
    def __init__(self):
        self.porcupine = None
        self.is_listening = False
        self.detection_callback = None
        self.detection_thread = None
        self.device_id = None
        
        # 初始化Porcupine
        self._initialize_porcupine()
    
    def _initialize_porcupine(self):
        """初始化Porcupine引擎"""
        try:
            access_key = os.getenv('PICOVOICE_ACCESS_KEY')
            
            # 查找文件
            wake_word_file = 'wake_words/kk_zh_raspberry-pi_v3_0_0.ppn'
            model_file = 'models/porcupine/porcupine_params_zh.pv'
            
            if not os.path.exists(wake_word_file):
                print(f"❌ 唤醒词文件不存在: {wake_word_file}")
                return False
            
            if not os.path.exists(model_file):
                print(f"❌ 中文模型不存在: {model_file}")
                return False
            
            # 创建Porcupine实例
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keyword_paths=[wake_word_file],
                model_path=model_file,
                sensitivities=[0.5]
            )
            
            print(f"✅ Porcupine初始化成功")
            print(f"📊 采样率: {self.porcupine.sample_rate}Hz")
            print(f"📏 帧长度: {self.porcupine.frame_length}")
            
            return True
            
        except Exception as e:
            print(f"❌ Porcupine初始化失败: {e}")
            return False
    
    def start_detection(self, callback):
        """开始检测"""
        if not self.porcupine:
            return False
        
        self.detection_callback = callback
        self.is_listening = True
        
        # 查找音频设备
        try:
            devices = sd.query_devices()
            print("📊 可用音频设备:")
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    print(f"  设备 {i}: {device['name']} (输入通道: {device['max_input_channels']})")
                    # 查找ReSpeaker设备
                    name = device['name'].lower()
                    if 'seeed' in name or 'array' in name:
                        self.device_id = i
                        print(f"✅ 选择ReSpeaker设备: {device['name']}")
            
            # 测试录音
            print("🧪 测试sounddevice录音...")
            test_audio = sd.rec(
                1024,  # 录制1024个样本
                samplerate=self.porcupine.sample_rate,
                channels=1,
                device=self.device_id,
                dtype=np.int16
            )
            sd.wait()  # 等待录制完成
            
            if test_audio is not None and len(test_audio) > 0:
                print("✅ sounddevice录音测试成功")
            else:
                print("❌ sounddevice录音测试失败")
                return False
            
        except Exception as e:
            print(f"❌ 音频设备设置失败: {e}")
            return False
        
        # 启动检测线程
        self.detection_thread = threading.Thread(target=self._detection_worker, daemon=True)
        self.detection_thread.start()
        
        return True
    
    def stop_detection(self):
        """停止检测"""
        self.is_listening = False
        if self.detection_thread:
            self.detection_thread.join(timeout=2)
    
    def _detection_worker(self):
        """检测工作线程"""
        print("🎤 启动sounddevice检测线程...")
        
        frame_length = self.porcupine.frame_length
        sample_rate = self.porcupine.sample_rate
        
        detection_count = 0
        
        try:
            while self.is_listening:
                try:
                    # 使用sounddevice录制音频
                    audio_chunk = sd.rec(
                        frame_length,
                        samplerate=sample_rate,
                        channels=1,
                        device=self.device_id,
                        dtype=np.int16
                    )
                    sd.wait()  # 等待录制完成
                    
                    # 转换为1维数组
                    audio_data = audio_chunk.flatten()
                    
                    if len(audio_data) != frame_length:
                        print(f"⚠️ 音频数据长度不匹配: {len(audio_data)} != {frame_length}")
                        continue
                    
                    # 检测唤醒词
                    keyword_index = self.porcupine.process(audio_data)
                    
                    detection_count += 1
                    if detection_count % 100 == 0:
                        print(f"🔄 已处理 {detection_count} 帧音频数据")
                    
                    if keyword_index >= 0:
                        print(f"\n🎉 检测到唤醒词 '快快'！索引: {keyword_index}")
                        if self.detection_callback:
                            self.detection_callback(keyword_index)
                    
                except Exception as e:
                    print(f"⚠️ 处理音频数据错误: {e}")
                    time.sleep(0.01)
                    continue
                    
        except Exception as e:
            print(f"❌ 检测线程错误: {e}")
        
        print(f"🛑 检测线程结束，共处理 {detection_count} 帧")

# 测试代码
def signal_handler(sig, frame):
    print('\n🛑 停止测试...')
    if 'detector' in globals():
        detector.stop_detection()
    sys.exit(0)

def on_wake_word(keyword_index):
    print(f"🎉 检测到唤醒词！索引: {keyword_index}")
    print("✨ 唤醒词检测正常工作!")

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)

print("🧪 SoundDevice专用唤醒词检测测试")
print("=" * 50)

try:
    detector = SoundDeviceWakeWordDetector()
    
    if not detector.porcupine:
        print("❌ 初始化失败")
        sys.exit(1)
    
    if detector.start_detection(on_wake_word):
        print("✅ 唤醒词检测已启动")
        print("🗣️ 请清晰地说 '快快' 来测试...")
        print("⏱️ 测试将持续30秒")
        
        # 等待30秒
        time.sleep(30)
        
        print("\n⏰ 测试时间结束")
        detector.stop_detection()
        print("✅ 测试完成")
    else:
        print("❌ 启动失败")

except KeyboardInterrupt:
    print("\n🛑 用户中断测试")
    if 'detector' in globals():
        detector.stop_detection()

except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()