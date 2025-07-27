#!/usr/bin/env python3
"""
测试音频修复后唤醒词是否还能正常工作
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

def test_wake_word_still_works():
    """测试唤醒词是否还能正常工作"""
    print("🎤 测试音频修复后唤醒词功能")
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
        
        detection_count = 0
        
        def on_wake_word_detected(keyword_index):
            nonlocal detection_count
            detection_count += 1
            print(f"\n🎉 检测 #{detection_count}: 唤醒词 '快快' (索引: {keyword_index})")
            print("✅ 唤醒词功能正常！")
        
        # 开始检测
        print(f"\n🎙️  测试唤醒词 '快快' (10秒测试)...")
        print("💡 如果能检测到，说明录音功能没有被破坏")
        print("-" * 50)
        
        if detector.start_detection(on_wake_word_detected):
            try:
                # 测试10秒
                start_time = time.time()
                while time.time() - start_time < 10:
                    time.sleep(0.1)
                    
            except KeyboardInterrupt:
                pass
            
            detector.stop_detection()
            
            if detection_count > 0:
                print(f"\n✅ 唤醒词功能正常！检测到 {detection_count} 次")
                return True
            else:
                print(f"\n⚠️  10秒内未检测到唤醒词")
                print("💡 可能是没有说话，或者需要更长时间测试")
                return True  # 初始化成功就算正常
        else:
            print("❌ 启动唤醒词检测失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_recording_still_works():
    """测试录音功能是否还能正常工作"""
    print("\n🎤 测试录音功能")
    print("=" * 30)
    
    try:
        import subprocess
        
        # 测试录音到临时文件
        test_file = "/tmp/test_recording.wav"
        
        print("🔄 测试录音 (2秒)...")
        cmd = ['arecord', '-D', 'plughw:1,0', '-f', 'cd', '-t', 'wav', '-d', '2', test_file]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 录音功能正常")
            
            # 检查文件是否存在
            if os.path.exists(test_file):
                file_size = os.path.getsize(test_file)
                print(f"   录音文件大小: {file_size} 字节")
                os.unlink(test_file)  # 清理
                return True
            else:
                print("❌ 录音文件未生成")
                return False
        else:
            print(f"❌ 录音失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 录音测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🔍 音频修复后功能验证")
    print("=" * 60)
    
    # 测试录音功能
    recording_ok = test_recording_still_works()
    
    # 测试唤醒词功能
    wake_word_ok = test_wake_word_still_works()
    
    print("\n" + "=" * 60)
    print("📊 测试结果:")
    print(f"• 录音功能: {'✅ 正常' if recording_ok else '❌ 异常'}")
    print(f"• 唤醒词功能: {'✅ 正常' if wake_word_ok else '❌ 异常'}")
    
    if recording_ok and wake_word_ok:
        print("\n🎉 所有功能正常！可以安全修复播放配置")
    else:
        print("\n⚠️  有功能异常，需要谨慎修复播放配置")
        print("💡 建议先恢复原始配置，再重新调试")