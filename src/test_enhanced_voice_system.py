#!/usr/bin/python3
"""
增强语音控制系统测试脚本
测试唤醒词检测、Whisper语音识别、edge-tts语音合成等功能
"""

import sys
import time
import threading
import logging
from enhanced_voice_control import EnhancedVoiceController
from ai_conversation import AIConversationManager
from LOBOROBOT import LOBOROBOT

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_basic_functionality():
    """测试基本功能"""
    print("=== 基本功能测试 ===")
    
    try:
        # 创建机器人控制器
        robot = LOBOROBOT()
        
        # 创建AI对话管理器
        ai_manager = AIConversationManager(robot)
        
        # 创建增强语音控制器
        voice_controller = EnhancedVoiceController(robot, ai_manager)
        
        # 测试状态获取
        status = voice_controller.get_conversation_status()
        print(f"初始状态: {status}")
        
        # 测试TTS功能
        print("\n测试TTS功能...")
        voice_controller.conversation_mode = True
        voice_controller.tts_thread = threading.Thread(target=voice_controller._tts_worker, daemon=True)
        voice_controller.tts_thread.start()
        
        voice_controller.speak_text("TTS系统测试成功！")
        time.sleep(3)
        
        # 测试语音列表
        voices = voice_controller.get_available_voices()
        print(f"\n可用语音数量: {len(voices)}")
        for voice in voices:
            print(f"  - {voice['name']}: {voice['description']}")
        
        voice_controller.conversation_mode = False
        print("\n基本功能测试完成")
        
        return True
        
    except Exception as e:
        logger.error(f"基本功能测试失败: {e}")
        return False

def test_conversation_mode():
    """测试对话模式"""
    print("\n=== 对话模式测试 ===")
    
    try:
        # 创建增强语音控制器
        voice_controller = EnhancedVoiceController()
        
        # 启动对话模式
        if voice_controller.start_conversation_mode():
            print("对话模式启动成功")
            
            # 显示状态
            status = voice_controller.get_conversation_status()
            print(f"对话模式状态: {status}")
            
            # 测试强制唤醒
            print("\n测试强制唤醒...")
            if voice_controller.force_wake_up():
                print("强制唤醒成功")
            
            time.sleep(2)
            
            # 停止对话模式
            voice_controller.stop_conversation_mode()
            print("对话模式已停止")
            
            return True
        else:
            print("对话模式启动失败")
            return False
            
    except Exception as e:
        logger.error(f"对话模式测试失败: {e}")
        return False

def test_whisper_integration():
    """测试Whisper集成"""
    print("\n=== Whisper集成测试 ===")
    
    try:
        from whisper_integration import get_whisper_recognizer
        
        # 获取Whisper识别器
        recognizer = get_whisper_recognizer("tiny")
        
        if recognizer.model:
            print("Whisper模型加载成功")
            print("模型大小: tiny")
            return True
        else:
            print("Whisper模型加载失败")
            return False
            
    except Exception as e:
        logger.error(f"Whisper集成测试失败: {e}")
        return False

def test_wake_word_detection():
    """测试唤醒词检测"""
    print("\n=== 唤醒词检测测试 ===")
    
    try:
        from wake_word_detector import WakeWordDetector, SimpleWakeWordDetector
        
        # 测试Porcupine检测器
        porcupine_detector = WakeWordDetector()
        if porcupine_detector.porcupine:
            print("Porcupine唤醒词检测器可用")
            porcupine_available = True
        else:
            print("Porcupine不可用，将使用简单检测器")
            porcupine_available = False
        
        # 测试简单检测器
        simple_detector = SimpleWakeWordDetector(["喵喵小车", "小车"])
        if simple_detector.microphone:
            print("简单唤醒词检测器可用")
            simple_available = True
        else:
            print("简单唤醒词检测器不可用")
            simple_available = False
        
        return porcupine_available or simple_available
        
    except Exception as e:
        logger.error(f"唤醒词检测测试失败: {e}")
        return False

def test_edge_tts():
    """测试edge-tts功能"""
    print("\n=== Edge-TTS测试 ===")
    
    try:
        import edge_tts
        import asyncio
        import tempfile
        import os
        
        async def test_tts():
            text = "这是edge-tts语音合成测试"
            voice = "zh-CN-XiaoxiaoNeural"
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            try:
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(temp_file_path)
                
                # 检查文件是否生成
                if os.path.exists(temp_file_path) and os.path.getsize(temp_file_path) > 0:
                    print("Edge-TTS语音生成成功")
                    return True
                else:
                    print("Edge-TTS语音生成失败")
                    return False
            finally:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
        
        return asyncio.run(test_tts())
        
    except Exception as e:
        logger.error(f"Edge-TTS测试失败: {e}")
        return False

def run_interactive_test():
    """运行交互式测试"""
    print("\n=== 交互式测试 ===")
    print("这将启动完整的语音对话系统")
    print("请确保:")
    print("1. 麦克风已连接并工作正常")
    print("2. 扬声器已连接并工作正常")
    print("3. 网络连接正常（用于AI对话）")
    
    response = input("\n是否继续交互式测试？(y/n): ")
    if response.lower() != 'y':
        print("跳过交互式测试")
        return
    
    try:
        # 创建增强语音控制器
        voice_controller = EnhancedVoiceController()
        
        # 启动对话模式
        if voice_controller.start_conversation_mode():
            print("\n对话系统已启动！")
            print("说'喵喵小车'来唤醒机器人")
            print("唤醒后可以进行自然对话")
            print("说'再见'来结束对话")
            print("按Ctrl+C退出测试")
            
            # 启动监听
            listen_thread = threading.Thread(target=voice_controller.listen_continuously, daemon=True)
            listen_thread.start()
            
            # 保持程序运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n正在停止...")
                voice_controller.stop()
                voice_controller.stop_conversation_mode()
                print("交互式测试结束")
        else:
            print("对话系统启动失败")
            
    except Exception as e:
        logger.error(f"交互式测试失败: {e}")

def main():
    """主测试函数"""
    print("====== 增强语音控制系统测试 ======")
    
    test_results = []
    
    # 运行各项测试
    test_results.append(("基本功能", test_basic_functionality()))
    test_results.append(("Whisper集成", test_whisper_integration()))
    test_results.append(("唤醒词检测", test_wake_word_detection()))
    test_results.append(("Edge-TTS", test_edge_tts()))
    test_results.append(("对话模式", test_conversation_mode()))
    
    # 显示测试结果
    print("\n====== 测试结果汇总 ======")
    for test_name, result in test_results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
    
    # 计算通过率
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    print(f"\n总体通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    # 如果基本测试通过，提供交互式测试选项
    if test_results[0][1]:  # 基本功能测试通过
        run_interactive_test()
    else:
        print("\n基本功能测试失败，跳过交互式测试")
        print("请检查依赖安装和配置")

if __name__ == "__main__":
    main()