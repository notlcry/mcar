#!/usr/bin/python3
"""
简单TTS测试 - 测试语音输出功能
"""

import asyncio
import edge_tts
import pygame
import tempfile
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_edge_tts():
    """测试edge-tts语音合成"""
    print("🎵 测试edge-tts语音合成...")
    
    try:
        # 使用中文语音
        voice = "zh-CN-XiaoxiaoNeural"
        text = "语音测试成功，机器人语音功能正常工作"
        
        print(f"🗣️ 合成文本: {text}")
        print(f"🎤 使用语音: {voice}")
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        # 合成语音
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(tmp_path)
        
        print(f"✅ 语音文件已生成: {tmp_path}")
        
        # 播放语音
        print("🔊 正在播放语音...")
        pygame.mixer.init()
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        
        # 等待播放完成
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
        
        print("✅ 语音播放完成")
        
        # 清理临时文件
        os.unlink(tmp_path)
        pygame.mixer.quit()
        
        return True
        
    except Exception as e:
        print(f"❌ TTS测试失败: {e}")
        return False

def test_basic_audio():
    """测试基础音频播放"""
    print("🔊 测试基础音频播放...")
    
    try:
        # 初始化pygame音频
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        
        print("✅ pygame音频初始化成功")
        
        # 生成简单的提示音
        import numpy as np
        sample_rate = 22050
        duration = 0.5  # 0.5秒
        frequency = 800  # 800Hz
        
        # 生成正弦波
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = np.sin(frequency * 2 * np.pi * t)
        
        # 转换为16位整数
        audio = (wave * 32767).astype(np.int16)
        
        # 创建立体声
        stereo_audio = np.array([audio, audio]).T
        
        # 播放
        sound = pygame.sndarray.make_sound(stereo_audio)
        sound.play()
        
        print("🔊 播放提示音...")
        pygame.time.wait(int(duration * 1000))
        
        pygame.mixer.quit()
        print("✅ 基础音频测试成功")
        return True
        
    except Exception as e:
        print(f"❌ 基础音频测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🎵 语音输出测试开始")
    print("=" * 30)
    
    # 测试基础音频
    if test_basic_audio():
        print("\n✅ 基础音频功能正常")
    else:
        print("\n❌ 基础音频功能异常")
        return
    
    # 测试TTS
    if await test_edge_tts():
        print("\n✅ TTS语音合成功能正常")
    else:
        print("\n❌ TTS语音合成功能异常")
    
    print("\n🎉 语音测试完成")

if __name__ == "__main__":
    asyncio.run(main())