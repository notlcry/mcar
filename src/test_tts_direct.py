#!/usr/bin/python3
"""
直接TTS测试 - 测试edge-tts语音合成和播放
"""

import asyncio
import edge_tts
import pygame
import tempfile
import os
import time

async def test_tts_direct():
    """直接测试TTS功能"""
    print("🗣️ 直接TTS测试开始...")
    
    try:
        # 1. 合成语音
        text = "你好，我是快快，语音测试正在进行中"
        voice = "zh-CN-XiaoxiaoNeural"
        
        print(f"📝 文本: {text}")
        print(f"🎤 语音: {voice}")
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        print("🔄 正在合成语音...")
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(tmp_path)
        
        print(f"✅ 语音文件已生成: {tmp_path}")
        
        # 检查文件大小
        file_size = os.path.getsize(tmp_path)
        print(f"📁 文件大小: {file_size} 字节")
        
        if file_size == 0:
            print("❌ 语音文件为空！")
            return False
        
        # 2. 播放语音
        print("🔊 正在播放语音...")
        
        # 初始化pygame音频
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=1024)
        pygame.mixer.init()
        
        # 加载并播放
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        
        print("⏳ 等待播放完成...")
        
        # 等待播放完成
        start_time = time.time()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
            # 防止无限等待
            if time.time() - start_time > 10:
                print("⚠️ 播放超时")
                break
        
        print("✅ 播放完成")
        
        # 清理
        pygame.mixer.music.stop()
        pygame.mixer.quit()
        os.unlink(tmp_path)
        
        return True
        
    except Exception as e:
        print(f"❌ TTS测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_sound():
    """测试简单的蜂鸣音"""
    print("🔔 测试简单蜂鸣音...")
    
    try:
        import numpy as np
        
        # 初始化pygame
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        
        # 生成440Hz的音调（A4音符）
        duration = 1.0  # 1秒
        sample_rate = 22050
        frequency = 440
        
        # 生成正弦波
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = np.sin(frequency * 2 * np.pi * t)
        
        # 添加淡入淡出避免爆音
        fade_frames = int(0.1 * sample_rate)  # 0.1秒淡入淡出
        wave[:fade_frames] *= np.linspace(0, 1, fade_frames)
        wave[-fade_frames:] *= np.linspace(1, 0, fade_frames)
        
        # 转换为16位整数
        audio = (wave * 32767 * 0.5).astype(np.int16)  # 降低音量到50%
        
        # 创建立体声（确保内存连续）
        stereo_audio = np.zeros((len(audio), 2), dtype=np.int16)
        stereo_audio[:, 0] = audio  # 左声道
        stereo_audio[:, 1] = audio  # 右声道
        
        # 播放
        sound = pygame.sndarray.make_sound(stereo_audio)
        sound.play()
        
        print("🎵 播放440Hz测试音...")
        pygame.time.wait(int(duration * 1000))
        
        pygame.mixer.quit()
        print("✅ 蜂鸣音测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 蜂鸣音测试失败: {e}")
        return False

async def main():
    """主函数"""
    print("🎵 音频输出测试程序")
    print("=" * 30)
    
    # 1. 测试简单蜂鸣音
    print("\\n阶段1: 测试基础音频输出")
    if test_simple_sound():
        print("✅ 基础音频输出正常")
    else:
        print("❌ 基础音频输出异常")
        return
    
    print("\\n等待2秒...")
    await asyncio.sleep(2)
    
    # 2. 测试TTS
    print("\\n阶段2: 测试TTS语音合成")
    if await test_tts_direct():
        print("✅ TTS语音合成正常")
    else:
        print("❌ TTS语音合成异常")
    
    print("\\n🎉 测试完成!")

if __name__ == "__main__":
    asyncio.run(main())