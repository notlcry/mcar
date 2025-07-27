#!/usr/bin/env python3
"""
测试修复后的唤醒词检测器
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

def test_fixed_wake_word():
    """测试修复后的唤醒词检测器"""
    print("🎤 测试修复后的唤醒词检测器")
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
        
        # 定义唤醒回调
        detection_count = 0
        
        def on_wake_word_detected(keyword_index):
            nonlocal detection_count
            detection_count += 1
            print(f"\n🎉 检测 #{detection_count}: 唤醒词 '快快' (索引: {keyword_index})")
            print("🗣️  回应: 你好！我听到了！")
        
        # 开始检测
        print(f"\n🎙️  开始监听唤醒词 '快快'...")
        print("💡 现在使用16kHz原生采样率，应该能正常工作")
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
    if test_fixed_wake_word():
        print("\n🎉 修复成功！唤醒词检测器现在可以正常工作了！")
        print("💡 现在可以在主系统中使用唤醒词功能")
    else:
        print("\n❌ 修复失败，需要进一步调试")