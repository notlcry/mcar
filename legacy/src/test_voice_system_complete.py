#!/usr/bin/python3
"""
完整语音系统测试 - 测试TTS、唤醒词、对话完整流程
"""

import asyncio
import time
import logging
import threading
import tempfile
import os

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VoiceSystemTester:
    """语音系统测试器"""
    
    def __init__(self):
        self.controller = None
        self.wake_detected = False
        self.conversation_active = False
    
    async def test_tts_only(self):
        """测试TTS语音合成"""
        print("🗣️ 测试TTS语音合成...")
        
        try:
            from enhanced_voice_control import EnhancedVoiceController
            
            # 创建控制器（测试模式）
            self.controller = EnhancedVoiceController(test_mode=True)
            print("✅ 语音控制器初始化成功")
            
            # 测试Azure TTS
            test_text = "你好，我是快快，这是小小的声音测试"
            
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                success = await self.controller._async_generate_speech(test_text, tmp_path)
                
                if success:
                    file_size = os.path.getsize(tmp_path)
                    print(f"✅ TTS生成成功，文件大小: {file_size} 字节")
                    
                    # 尝试播放
                    if hasattr(self.controller, '_play_audio_file_pygame'):
                        print("🔊 尝试播放语音...")
                        self.controller._play_audio_file_pygame(tmp_path)
                        print("✅ 语音播放完成")
                    
                    return True
                else:
                    print("❌ TTS生成失败")
                    return False
                    
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            print(f"❌ TTS测试异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_wake_word_callback(self, keyword_index):
        """唤醒词检测回调"""
        print(f"🚨 检测到唤醒词！索引: {keyword_index}")
        self.wake_detected = True
    
    async def test_wake_word_detection(self):
        """测试唤醒词检测"""
        print("\n🎤 测试唤醒词检测...")
        
        if not self.controller:
            print("❌ 控制器未初始化")
            return False
        
        try:
            # 检查唤醒词检测器
            if hasattr(self.controller, 'wake_word_detector') and self.controller.wake_word_detector:
                print("✅ 唤醒词检测器可用")
                
                # 启动检测
                if self.controller.wake_word_detector.start_detection(self.test_wake_word_callback):
                    print("🟢 唤醒词检测已启动")
                    print("🎯 请清晰地说'快快'...")
                    print("⏰ 测试时间: 15秒")
                    
                    # 等待15秒
                    start_time = time.time()
                    timeout = 15
                    
                    while time.time() - start_time < timeout:
                        if self.wake_detected:
                            print("🎉 唤醒词检测成功！")
                            break
                        await asyncio.sleep(1)
                        
                        remaining = int(timeout - (time.time() - start_time))
                        if remaining % 5 == 0 and remaining > 0:
                            print(f"⏳ 剩余时间: {remaining}秒")
                    
                    # 停止检测
                    self.controller.wake_word_detector.stop_detection()
                    print("🔇 已停止唤醒词检测")
                    
                    return self.wake_detected
                else:
                    print("❌ 唤醒词检测启动失败")
                    return False
            else:
                print("❌ 唤醒词检测器不可用")
                return False
                
        except Exception as e:
            print(f"❌ 唤醒词测试异常: {e}")
            return False
    
    async def test_conversation_mode(self):
        """测试对话模式"""
        print("\n💬 测试对话模式...")
        
        if not self.controller:
            print("❌ 控制器未初始化")
            return False
        
        try:
            # 启动对话模式
            self.controller.start_conversation_mode()
            print("✅ 对话模式已启动")
            
            # 等待系统稳定
            await asyncio.sleep(2)
            
            # 检查状态
            if hasattr(self.controller, 'conversation_mode') and self.controller.conversation_mode:
                print("✅ 对话模式状态正常")
                
                # 播放启动提示
                if hasattr(self.controller, 'speak_text'):
                    print("🗣️ 播放启动提示...")
                    self.controller.speak_text("快快已准备好，请说快快唤醒我")
                    await asyncio.sleep(3)
                
                return True
            else:
                print("❌ 对话模式状态异常")
                return False
                
        except Exception as e:
            print(f"❌ 对话模式测试异常: {e}")
            return False
    
    async def test_complete_workflow(self):
        """测试完整工作流程"""
        print("\n🔄 测试完整工作流程...")
        
        try:
            # 1. 启动对话模式
            success = await self.test_conversation_mode()
            if not success:
                return False
            
            # 2. 测试唤醒词
            print("\n🎤 现在测试完整唤醒流程...")
            print("📢 请说'快快'来唤醒系统...")
            
            # 重置状态
            self.wake_detected = False
            
            # 监听唤醒词
            if hasattr(self.controller, '_on_wake_word_detected'):
                # 模拟唤醒检测
                start_time = time.time()
                timeout = 20
                
                while time.time() - start_time < timeout:
                    # 这里应该是真实的唤醒词检测
                    # 为了测试，我们等待用户确认
                    await asyncio.sleep(1)
                    
                    remaining = int(timeout - (time.time() - start_time))
                    if remaining % 5 == 0 and remaining > 0:
                        print(f"⏳ 等待唤醒词: {remaining}秒")
                
                print("⏰ 测试超时")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ 完整流程测试异常: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        if self.controller:
            try:
                if hasattr(self.controller, 'stop_conversation_mode'):
                    self.controller.stop_conversation_mode()
                print("🧹 资源清理完成")
            except:
                pass

async def main():
    """主函数"""
    print("🤖 MCAR完整语音系统测试")
    print("🎯 测试: TTS + 唤醒词 + 对话模式")
    print("=" * 50)
    
    tester = VoiceSystemTester()
    
    try:
        # 1. 测试TTS
        print("\n阶段1: TTS语音合成测试")
        tts_success = await tester.test_tts_only()
        
        if not tts_success:
            print("❌ TTS测试失败，终止测试")
            return
        
        # 2. 测试唤醒词（独立测试）
        print("\n阶段2: 唤醒词检测测试")
        wake_success = await tester.test_wake_word_detection()
        
        # 3. 测试完整流程
        print("\n阶段3: 完整工作流程测试")
        complete_success = await tester.test_complete_workflow()
        
        # 结果总结
        print("\n" + "=" * 50)
        print("📊 测试结果总结:")
        print(f"   TTS语音合成: {'✅ 通过' if tts_success else '❌ 失败'}")
        print(f"   唤醒词检测: {'✅ 通过' if wake_success else '❌ 失败'}")
        print(f"   完整流程: {'✅ 通过' if complete_success else '❌ 失败'}")
        
        if tts_success and wake_success:
            print("\n🎉 语音系统基本功能正常！")
            print("💡 建议: 现在可以运行主系统进行实际测试")
        else:
            print("\n⚠️ 语音系统存在问题，需要进一步调试")
    
    finally:
        tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())