#!/usr/bin/env python3
"""
简单的TTS修复 - 避免异步库冲突
使用系统命令方式进行语音合成
"""

import subprocess
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

def simple_tts_speak(text, voice="zh-CN-XiaoxiaoNeural"):
    """
    简单的TTS语音输出
    使用edge-tts命令行工具避免Python异步库冲突
    """
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # 使用edge-tts命令行工具
        cmd = [
            'edge-tts',
            '--voice', voice,
            '--text', text,
            '--write-media', temp_path
        ]
        
        # 生成语音文件
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            # 播放语音文件
            play_cmd = ['aplay', temp_path]
            play_result = subprocess.run(play_cmd, capture_output=True, timeout=10)
            
            # 清理临时文件
            os.unlink(temp_path)
            
            if play_result.returncode == 0:
                print("🔊 语音播放成功")
                return True
            else:
                print(f"⚠️ 播放失败: {play_result.stderr.decode()}")
                return False
        else:
            print(f"⚠️ TTS生成失败: {result.stderr.decode()}")
            os.unlink(temp_path)
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️ TTS处理超时")
        return False
    except Exception as e:
        print(f"⚠️ TTS失败: {e}")
        return False

def test_simple_tts():
    """测试简单TTS"""
    print("🔊 测试简单TTS...")
    
    test_text = "你好，这是TTS测试"
    success = simple_tts_speak(test_text)
    
    if success:
        print("✅ TTS修复成功！")
    else:
        print("❌ TTS仍有问题")
        
        # 检查edge-tts是否安装
        try:
            result = subprocess.run(['edge-tts', '--list-voices'], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0:
                print("✅ edge-tts命令行工具可用")
            else:
                print("❌ edge-tts命令行工具不可用")
                print("💡 安装方法: pip install edge-tts")
        except:
            print("❌ edge-tts未安装")
            print("💡 安装方法: pip install edge-tts")

if __name__ == "__main__":
    test_simple_tts()