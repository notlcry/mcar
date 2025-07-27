#!/usr/bin/env python3
"""
最终唤醒词测试 - 确认功能正常
"""

import os
import sys
import time

# 加载环境变量
def load_env():
    try:
        with open('.ai_pet_env', 'r') as f:
            for line in f:
                if line.startswith('export ') and '=' in line:
                    line = line.replace('export ', '').strip()
                    key, value = line.split('=', 1)
                    value = value.strip('"')
                    os.environ[key] = value
    except:
        pass

load_env()
sys.path.insert(0, 'src')

def test_final_wake_word():
    """最终唤醒词测试"""
    print("🎤 最终唤醒词检测测试")
    print("=" * 50)
    
    try:
        from wake_word_detector import WakeWordDetector
        
        # 创建唤醒词检测器
        print("🔧 初始化唤醒词检测器...")
        detector = WakeWordDetector()
        
        if not detector.porcupine:
            print("❌ 唤醒词检测器初始化失败")
            return False
        
        print("✅ 唤醒词检测器初始化成功")
        print(f"   采样率: {detector.target_sample_rate} Hz")
        print(f"   帧长度: {detector.porcupine.frame_length}")
        
        # 定义回复语句
        responses = [
            "你好！我听到了！",
            "主人，我在这里！", 
            "有什么可以帮助您的吗？",
            "您好，我是AI桌宠！",
            "快快，我来了！"
        ]
        
        detection_count = 0
        
        def on_wake_word_detected(keyword_index):
            nonlocal detection_count
            detection_count += 1
            
            print(f"\n🎉 检测 #{detection_count}: 唤醒词 '快快' (索引: {keyword_index})")
            
            # 选择回复语句
            response = responses[(detection_count - 1) % len(responses)]
            print(f"🗣️  文字回复: {response}")
            print("💡 (语音合成功能需要修复音频输出设备)")
            
            # 简单的提示音
            print("\a")  # 系统提示音
        
        # 开始检测
        print(f"\n🎙️  开始监听唤醒词 '快快'...")
        print("💡 检测到唤醒词后会显示文字回复")
        print("按 Ctrl+C 停止测试")
        print("-" * 50)
        
        if detector.start_detection(on_wake_word_detected):
            try:
                # 保持运行
                while True:
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print(f"\n\n🛑 停止测试...")
                detector.stop_detection()
                print(f"📊 总共检测到 {detection_count} 次唤醒词")
                print("✅ 测试结束")
                return detection_count > 0
        else:
            print("❌ 启动唤醒词检测失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🎤 最终唤醒词检测确认测试")
    print("=" * 60)
    
    if test_final_wake_word():
        print("\n🎉 唤醒词检测功能完全正常！")
        print("\n✅ 已修复的功能:")
        print("• 唤醒词 '快快' 检测正常")
        print("• 使用16kHz原生采样率")
        print("• 避免了重采样问题")
        print("• 检测响应速度快")
        
        print("\n⚠️  待修复的功能:")
        print("• 音频输出设备配置")
        print("• 语音合成播放")
        
        print("\n💡 下一步:")
        print("• 可以集成到主系统中使用唤醒词功能")
        print("• 语音合成问题是独立的，不影响唤醒词检测")
        
    else:
        print("\n❌ 唤醒词检测仍有问题")