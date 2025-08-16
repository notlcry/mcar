#!/usr/bin/env python3
# 为AI桌宠添加提示音功能

import os
import pygame
import numpy as np

def create_beep_sounds():
    """创建提示音文件"""
    
    # 确保pygame音频已初始化
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    # 创建音频目录
    os.makedirs('src/sounds', exist_ok=True)
    
    def generate_beep(frequency, duration, sample_rate=22050):
        """生成提示音"""
        frames = int(duration * sample_rate)
        arr = np.zeros((frames, 2))  # 立体声
        
        for i in range(frames):
            # 生成正弦波
            wave = np.sin(2 * np.pi * frequency * i / sample_rate)
            # 添加淡入淡出效果
            if i < frames * 0.1:  # 淡入
                wave *= i / (frames * 0.1)
            elif i > frames * 0.9:  # 淡出
                wave *= (frames - i) / (frames * 0.1)
            
            arr[i] = [wave, wave]  # 左右声道
        
        # 转换为16位整数
        arr = (arr * 32767).astype(np.int16)
        return arr
    
    # 创建不同的提示音
    sounds = {
        'wake_up': (800, 0.2),      # 唤醒提示音 - 高频短音
        'listening': (600, 0.1),    # 开始录音提示音 - 中频短音
        'processing': (400, 0.3),   # 处理中提示音 - 低频长音
        'success': (1000, 0.15),    # 成功提示音 - 很高频短音
        'error': (200, 0.5),        # 错误提示音 - 很低频长音
        'goodbye': (500, 0.4)       # 再见提示音 - 中频中等长度
    }
    
    print("🔊 创建提示音文件...")
    
    for name, (freq, duration) in sounds.items():
        print(f"   创建 {name}.wav (频率: {freq}Hz, 时长: {duration}s)")
        
        # 生成音频数据
        audio_data = generate_beep(freq, duration)
        
        # 保存为WAV文件
        sound = pygame.sndarray.make_sound(audio_data)
        pygame.mixer.Sound.play(sound)  # 测试播放
        
        # 保存文件
        filename = f'src/sounds/{name}.wav'
        # 注意：pygame不直接支持保存WAV，我们用numpy保存
        import wave
        with wave.open(filename, 'w') as wav_file:
            wav_file.setnchannels(2)  # 立体声
            wav_file.setsampwidth(2)  # 16位
            wav_file.setframerate(22050)
            wav_file.writeframes(audio_data.tobytes())
    
    print("✅ 提示音文件创建完成！")
    return True

def create_enhanced_voice_control():
    """创建增强的语音控制器，支持提示音"""
    
    enhanced_code = '''
# 在 enhanced_voice_control.py 中添加提示音支持

import pygame
import os

class EnhancedVoiceControlWithBeeps:
    """增强的语音控制器，支持提示音"""
    
    def __init__(self):
        # ... 原有初始化代码 ...
        self._load_beep_sounds()
    
    def _load_beep_sounds(self):
        """加载提示音"""
        self.beep_sounds = {}
        sounds_dir = 'sounds'
        
        if os.path.exists(sounds_dir):
            sound_files = {
                'wake_up': 'wake_up.wav',
                'listening': 'listening.wav', 
                'processing': 'processing.wav',
                'success': 'success.wav',
                'error': 'error.wav',
                'goodbye': 'goodbye.wav'
            }
            
            for name, filename in sound_files.items():
                filepath = os.path.join(sounds_dir, filename)
                if os.path.exists(filepath):
                    try:
                        self.beep_sounds[name] = pygame.mixer.Sound(filepath)
                        logger.info(f"加载提示音: {name}")
                    except Exception as e:
                        logger.warning(f"加载提示音失败 {name}: {e}")
    
    def play_beep(self, beep_type):
        """播放提示音"""
        if beep_type in self.beep_sounds:
            try:
                self.beep_sounds[beep_type].play()
                logger.info(f"播放提示音: {beep_type}")
            except Exception as e:
                logger.warning(f"播放提示音失败 {beep_type}: {e}")
    
    def _on_wake_word_detected(self, keyword_index):
        """唤醒词检测回调 - 增强版"""
        if not self.conversation_mode:
            return
            
        logger.info(f"检测到唤醒词，索引: {keyword_index}")
        
        # 播放唤醒提示音
        self.play_beep('wake_up')
        
        # 设置唤醒状态
        self.wake_word_detected = True
        self.last_interaction_time = time.time()
        
        # 开始录音
        self.start_voice_recording()
    
    def start_voice_recording(self):
        """开始语音录音 - 增强版"""
        if self.recording:
            return
            
        # 播放开始录音提示音
        self.play_beep('listening')
        
        # ... 原有录音代码 ...
    
    def process_voice_input(self, audio_data):
        """处理语音输入 - 增强版"""
        # 播放处理中提示音
        self.play_beep('processing')
        
        # ... 原有处理代码 ...
        
        # 根据处理结果播放相应提示音
        if success:
            self.play_beep('success')
        else:
            self.play_beep('error')
    
    def stop_conversation_mode(self):
        """停止AI对话模式 - 增强版"""
        # 播放再见提示音
        self.play_beep('goodbye')
        
        # ... 原有停止代码 ...
'''
    
    print("📝 增强语音控制器代码示例已生成")
    print("   可以参考上面的代码来修改 enhanced_voice_control.py")
    
    return enhanced_code

if __name__ == "__main__":
    print("====================================")
    print("🔊 添加AI桌宠提示音功能")
    print("====================================")
    
    try:
        # 创建提示音文件
        create_beep_sounds()
        
        # 显示增强代码示例
        create_enhanced_voice_control()
        
        print("\n✅ 提示音功能添加完成！")
        print("\n📋 使用说明:")
        print("• 提示音文件保存在: src/sounds/")
        print("• wake_up.wav - 唤醒提示音")
        print("• listening.wav - 开始录音提示音") 
        print("• processing.wav - 处理中提示音")
        print("• success.wav - 成功提示音")
        print("• error.wav - 错误提示音")
        print("• goodbye.wav - 再见提示音")
        print("\n🧪 测试提示音:")
        print("python3 -c \"import pygame; pygame.mixer.init(); s=pygame.mixer.Sound('src/sounds/wake_up.wav'); s.play(); import time; time.sleep(1)\"")
        
    except Exception as e:
        print(f"❌ 添加提示音功能失败: {e}")