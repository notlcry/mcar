#!/usr/bin/env python3
"""
改进的ReSpeaker 2-Mics唤醒词检测测试
添加了更好的错误处理和音频设备兼容性
"""

import os
import sys
import time
import signal

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

# 导入唤醒词检测器
try:
    from wake_word_detector import WakeWordDetector
    print("✅ 唤醒词检测器模块导入成功")
except ImportError as e:
    print(f"❌ 导入唤醒词检测器失败: {e}")
    sys.exit(1)

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

print("🧪 改进的ReSpeaker 2-Mics唤醒词检测测试")
print("=" * 60)

try:
    # 初始化检测器
    print("🔧 初始化唤醒词检测器...")
    detector = WakeWordDetector()
    
    if detector.porcupine is None:
        print("❌ Porcupine初始化失败")
        print("💡 请检查:")
        print("   1. Picovoice访问密钥是否正确")
        print("   2. 唤醒词文件是否存在")
        print("   3. 中文语言模型是否存在")
        sys.exit(1)
    
    print("✅ Porcupine初始化成功")
    if detector.keyword_paths:
        print(f"🔑 使用自定义唤醒词文件: {detector.keyword_paths}")
    else:
        print(f"🔑 使用内置关键词: {detector.keywords}")
    
    # 启动检测
    print(f"\n🎤 启动唤醒词检测...")
    print("📋 系统将尝试多种音频配置以找到最佳设置")
    
    if detector.start_detection(on_wake_word):
        print("✅ 唤醒词检测已启动")
        print("🗣️ 请清晰地说 '快快' 来测试...")
        print("📢 建议距离麦克风30-50cm，音量适中")
        print("⏱️ 测试将持续60秒，按Ctrl+C可提前停止")
        
        # 等待60秒或用户中断
        for i in range(60):
            time.sleep(1)
            if i % 10 == 9:
                print(f"⏰ 测试进行中... ({i+1}/60秒) - 请说 '快快'")
                if i == 29:
                    print("💡 提示: 如果一直没有检测到，可能需要:")
                    print("   - 增大音量或靠近麦克风")
                    print("   - 发音更清晰")
                    print("   - 检查麦克风是否正常工作")
        
        print("\n⏰ 测试时间结束")
        detector.stop_detection()
        print("✅ 测试完成")
    else:
        print("❌ 唤醒词检测启动失败")
        print("💡 常见问题排查:")
        print("   1. 检查麦克风是否连接并工作正常")
        print("   2. 检查音频设备权限")
        print("   3. 尝试重新插拔ReSpeaker设备")
        print("   4. 检查USB端口和供电")
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