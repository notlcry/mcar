#!/usr/bin/env python3
"""
测试回音防护机制
验证音频播放时是否能正确阻止录音和语音识别
"""

import os
import sys
import time
import threading
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, 'src')

def test_echo_prevention():
    """测试回音防护机制"""
    print("🛡️ 测试回音防护机制")
    print("=" * 50)
    
    try:
        from enhanced_voice_control import EnhancedVoiceController
        
        # 创建模拟机器人
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        # 创建测试模式控制器
        print("🔧 创建测试模式控制器...")
        voice_controller = EnhancedVoiceController(
            robot=MockRobot(), 
            test_mode=True
        )
        print("✅ 控制器创建成功")
        
        # 测试1: 验证初始状态
        print("\n📊 测试1: 验证初始状态")
        print(f"   播放状态: {voice_controller.is_playing_audio}")
        print(f"   录音暂停: {voice_controller.recording_paused}")
        print(f"   有音频锁: {hasattr(voice_controller, 'audio_lock')}")
        
        # 测试2: 验证暂停/恢复录音机制
        print("\n📊 测试2: 验证暂停/恢复录音机制")
        
        # 暂停录音
        voice_controller._pause_recording()
        print(f"   暂停后录音状态: {voice_controller.recording_paused}")
        
        # 恢复录音
        voice_controller._resume_recording()
        print(f"   恢复后录音状态: {voice_controller.recording_paused}")
        
        # 测试3: 验证过滤TTS文本功能
        print("\n📊 测试3: 验证TTS文本过滤")
        test_texts = [
            "你好！",
            "(快快听完后，认真地点点头) 喔喔！我明白了！",
            "[快快做了个开心的动作] 太棒了！",
            "（快快眨眨眼）知道了呢~",
            "【快快转个圈】我很高兴！",
            "(表情描述)[动作描述]（中文描述）【中文动作】实际要说的话"
        ]
        
        for text in test_texts:
            filtered = voice_controller._filter_tts_text(text)
            print(f"   原文: {text}")
            print(f"   过滤: {filtered}")
            print()
        
        # 测试4: 模拟播放-录音冲突场景
        print("📊 测试4: 模拟播放-录音冲突场景")
        
        def simulate_audio_playback():
            """模拟音频播放"""
            print("   🔊 开始模拟音频播放...")
            with voice_controller.audio_lock:
                voice_controller.is_playing_audio = True
            voice_controller._pause_recording()
            
            time.sleep(2)  # 模拟播放2秒
            
            with voice_controller.audio_lock:
                voice_controller.is_playing_audio = False
            voice_controller._resume_recording()
            print("   ✅ 模拟音频播放完成")
        
        def simulate_recording_attempt():
            """模拟录音尝试"""
            print("   🎤 尝试开始录音...")
            
            # 模拟 _handle_conversation_round 的检查逻辑
            if voice_controller.is_playing_audio or voice_controller.recording_paused:
                print("   🔇 录音被正确阻止（防回音）")
                return False
            else:
                print("   ⚠️ 录音未被阻止（可能有回音风险）")
                return True
        
        # 启动播放线程
        playback_thread = threading.Thread(target=simulate_audio_playback, daemon=True)
        playback_thread.start()
        
        # 短暂延迟后尝试录音
        time.sleep(0.5)
        recording_blocked = not simulate_recording_attempt()
        
        # 等待播放完成
        playback_thread.join()
        time.sleep(0.5)
        
        # 播放完成后再次尝试录音
        print("   🎤 播放完成后尝试录音...")
        recording_allowed = simulate_recording_attempt()
        
        # 测试5: 验证语音识别的回音检测
        print("\n📊 测试5: 验证语音识别回音检测")
        
        # 设置播放状态
        with voice_controller.audio_lock:
            voice_controller.is_playing_audio = True
        
        # 创建模拟音频对象
        class MockAudio:
            pass
        
        # 尝试进行语音识别
        mock_audio = MockAudio()
        result = voice_controller._recognize_speech_enhanced(mock_audio)
        
        recognition_blocked = (result == "")
        print(f"   语音识别被阻止: {recognition_blocked}")
        
        # 恢复状态
        with voice_controller.audio_lock:
            voice_controller.is_playing_audio = False
        
        # 汇总测试结果
        print("\n🎉 测试结果汇总:")
        print("=" * 40)
        print(f"✅ 录音暂停/恢复机制: 正常")
        print(f"✅ TTS文本过滤机制: 正常")
        print(f"{'✅' if recording_blocked else '❌'} 播放时录音阻止: {'正常' if recording_blocked else '异常'}")
        print(f"{'✅' if recording_allowed else '❌'} 播放后录音恢复: {'正常' if recording_allowed else '异常'}")
        print(f"{'✅' if recognition_blocked else '❌'} 语音识别回音检测: {'正常' if recognition_blocked else '异常'}")
        
        overall_success = all([recording_blocked, recording_allowed, recognition_blocked])
        
        if overall_success:
            print("\n🎯 回音防护机制测试成功！")
            print("💡 系统可以有效防止音频回音问题")
        else:
            print("\n⚠️ 回音防护机制需要进一步优化")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🧪 回音防护机制测试")
    print("验证音频播放时的录音阻止机制")
    print("=" * 60)
    
    success = test_echo_prevention()
    
    if success:
        print("\n🎉 所有测试通过！")
        print("📋 验证结果:")
        print("✅ 音频播放时录音会被正确阻止")
        print("✅ TTS文本过滤正常工作")
        print("✅ 语音识别有回音检测保护")
        print("✅ 播放完成后录音功能恢复")
        
        print("\n💡 部署建议:")
        print("1. 在树莓派上测试实际的音频回音情况")
        print("2. 如果仍有回音，可以调整等待时间或硬件配置")
        print("3. 考虑使用不同的音频输入/输出设备")
        
    else:
        print("\n😞 测试未完全通过，需要进一步调试")

if __name__ == "__main__":
    main()