#!/usr/bin/python3
"""
唤醒词专项测试 - 独立测试唤醒词检测功能
"""

import time
import logging
import threading
import os
import sys

# 设置日志
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_wake_word_detection():
    """测试唤醒词检测"""
    print("🎤 唤醒词检测专项测试")
    print("=" * 40)
    
    try:
        # 导入唤醒词检测器
        from wake_word_detector import WakeWordDetector, SimpleWakeWordDetector
        
        print("✅ 成功导入唤醒词检测模块")
        
        # 测试标志
        wake_detected = threading.Event()
        detection_count = 0
        
        def on_wake_word(keyword_index):
            """唤醒词检测回调"""
            nonlocal detection_count
            detection_count += 1
            print(f"🚨 检测到唤醒词！索引: {keyword_index}, 总计: {detection_count}")
            wake_detected.set()
        
        # 尝试Porcupine检测器
        print("\n📋 测试1: Porcupine唤醒词检测器")
        wake_detector = WakeWordDetector()
        
        if wake_detector.porcupine:
            print("✅ Porcupine初始化成功")
            print("🎯 支持的唤醒词:")
            for i, keyword in enumerate(wake_detector.keywords):
                print(f"   {i}: {keyword}")
            
            print("\n🎤 开始监听唤醒词（请说'快快'）...")
            print("💡 说话提示: 清晰地说'快快'，距离麦克风30-50cm")
            print("⏰ 测试时间: 30秒")
            
            if wake_detector.start_detection(on_wake_word):
                print("🟢 唤醒词检测已启动")
                
                # 等待30秒或检测到唤醒词
                start_time = time.time()
                timeout = 30
                
                while time.time() - start_time < timeout:
                    if wake_detected.wait(1):
                        print("🎉 唤醒词检测成功！")
                        break
                    
                    # 显示剩余时间
                    remaining = int(timeout - (time.time() - start_time))
                    if remaining % 5 == 0:
                        print(f"⏳ 剩余时间: {remaining}秒 (请说'快快')")
                
                # 停止检测
                wake_detector.stop_detection()
                print("🔇 已停止唤醒词检测")
                
                if detection_count > 0:
                    print(f"✅ 测试结果: 成功检测到 {detection_count} 次唤醒词")
                    return True
                else:
                    print("❌ 测试结果: 未检测到任何唤醒词")
            else:
                print("❌ 唤醒词检测启动失败")
        else:
            print("❌ Porcupine初始化失败")
        
        # 备选：简单检测器
        print("\n📋 测试2: 简单唤醒词检测器")
        simple_detector = SimpleWakeWordDetector(["快快", "小车", "机器人"])
        
        if simple_detector:
            print("✅ 简单检测器初始化成功")
            print("🎯 支持的唤醒词: 快快, 小车, 机器人")
            
            # 重置检测状态
            wake_detected.clear()
            detection_count = 0
            
            print("\n🎤 开始监听唤醒词（请说'快快'）...")
            print("⏰ 测试时间: 20秒")
            
            if simple_detector.start_detection(on_wake_word):
                print("🟢 简单检测器已启动")
                
                # 等待20秒
                start_time = time.time()
                timeout = 20
                
                while time.time() - start_time < timeout:
                    if wake_detected.wait(1):
                        print("🎉 简单检测器检测成功！")
                        break
                    
                    remaining = int(timeout - (time.time() - start_time))
                    if remaining % 5 == 0:
                        print(f"⏳ 剩余时间: {remaining}秒")
                
                simple_detector.stop_detection()
                print("🔇 已停止简单检测器")
                
                if detection_count > 0:
                    print(f"✅ 简单检测器结果: 成功检测到 {detection_count} 次")
                    return True
                else:
                    print("❌ 简单检测器结果: 未检测到唤醒词")
        
        return False
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_audio_input():
    """测试音频输入设备"""
    print("\n🔊 音频输入设备测试")
    print("-" * 30)
    
    try:
        import pyaudio
        
        # 获取音频设备信息
        audio = pyaudio.PyAudio()
        
        print("📱 可用音频设备:")
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                print(f"   {i}: {device_info['name']} "
                      f"(输入通道: {device_info['maxInputChannels']}, "
                      f"采样率: {device_info['defaultSampleRate']})")
        
        # 获取默认输入设备
        default_device = audio.get_default_input_device_info()
        print(f"\n🎯 默认输入设备: {default_device['name']}")
        
        audio.terminate()
        return True
        
    except Exception as e:
        print(f"❌ 音频设备测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🤖 MCAR唤醒词检测专项测试")
    print("🎯 目标: 测试'快快'唤醒词是否正常工作")
    print("=" * 50)
    
    # 测试音频设备
    if not test_audio_input():
        print("⚠️ 音频设备异常，可能影响唤醒词检测")
    
    # 测试唤醒词检测
    success = test_wake_word_detection()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 唤醒词检测测试通过")
        print("💡 建议: 现在可以启动主系统测试完整功能")
    else:
        print("❌ 唤醒词检测测试失败")
        print("💡 建议: 检查麦克风连接和音频设备配置")
    
    print("\n🔧 故障排除:")
    print("1. 确保麦克风正确连接")
    print("2. 检查ALSA音频配置")  
    print("3. 确认Porcupine访问密钥设置")
    print("4. 尝试调整说话音量和距离")

if __name__ == "__main__":
    main()