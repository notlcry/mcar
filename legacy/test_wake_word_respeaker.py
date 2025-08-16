#!/usr/bin/env python3
"""
测试ReSpeaker 2-Mics的唤醒词检测
"""

import os
import sys
import time
import signal

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

# 导入唤醒词检测器
from wake_word_detector import WakeWordDetector

def signal_handler(sig, frame):
    print('\n🛑 停止测试...')
    if 'detector' in globals():
        detector.stop_detection()
    sys.exit(0)

def on_wake_word(keyword_index):
    print(f"\n🎉 检测到唤醒词！索引: {keyword_index}")
    print("✨ 唤醒词检测正常工作!")

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)

print("🧪 测试ReSpeaker 2-Mics唤醒词检测")
print("=" * 50)

try:
    # 初始化检测器
    detector = WakeWordDetector()
    
    if detector.porcupine is None:
        print("❌ Porcupine初始化失败")
        sys.exit(1)
    
    print("✅ Porcupine初始化成功")
    print(f"🔑 使用关键词文件: {detector.keyword_paths}")
    
    # 启动检测
    print("\n🎤 启动唤醒词检测...")
    if detector.start_detection(on_wake_word):
        print("✅ 唤醒词检测已启动")
        print("🗣️ 请说 '快快' 来测试...")
        print("⏱️ 测试将持续30秒，按Ctrl+C可提前停止")
        
        # 等待30秒或用户中断
        for i in range(30):
            time.sleep(1)
            if i % 5 == 4:
                print(f"⏰ 测试进行中... ({i+1}/30秒)")
        
        print("\n⏰ 测试时间结束")
        detector.stop_detection()
        print("✅ 测试完成")
    else:
        print("❌ 唤醒词检测启动失败")
        
except Exception as e:
    print(f"❌ 测试失败: {e}")
    sys.exit(1)