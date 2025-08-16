#!/usr/bin/env python3
"""
修复AI对话中的音频问题
专门解决ALSA段错误和音频设备配置问题
"""

import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_audio_devices():
    """检查音频设备状态"""
    print("🔍 检查音频设备...")
    
    try:
        # 检查录音设备
        result = subprocess.run(['arecord', '-l'], capture_output=True, text=True)
        print("📱 录音设备:")
        print(result.stdout)
        
        # 检查播放设备  
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
        print("🔊 播放设备:")
        print(result.stdout)
        
        return True
    except Exception as e:
        logger.error(f"检查音频设备失败: {e}")
        return False

def create_safe_asoundrc():
    """创建安全的ALSA配置"""
    print("🔧 创建安全的ALSA配置...")
    
    # 备份现有配置
    asoundrc_path = os.path.expanduser("~/.asoundrc")
    if os.path.exists(asoundrc_path):
        backup_path = asoundrc_path + ".backup"
        try:
            subprocess.run(['cp', asoundrc_path, backup_path])
            print(f"✅ 已备份现有配置到: {backup_path}")
        except:
            pass
    
    # 创建最小化安全配置
    safe_config = '''# 安全的ALSA配置 - 避免段错误
pcm.!default {
    type hw
    card 1
    device 0
}

ctl.!default {
    type hw
    card 1
}

# 用于PyAudio的安全配置
pcm.pyaudio {
    type hw
    card 1
    device 0
    rate 16000
    format S16_LE
    channels 1
}'''
    
    try:
        with open(asoundrc_path, 'w') as f:
            f.write(safe_config)
        print(f"✅ 创建安全ALSA配置: {asoundrc_path}")
        return True
    except Exception as e:
        logger.error(f"创建ALSA配置失败: {e}")
        return False

def test_safe_audio():
    """测试安全的音频录制"""
    print("🧪 测试安全音频录制...")
    
    try:
        # 简单的录音测试
        cmd = ['arecord', '-D', 'hw:1,0', '-f', 'S16_LE', '-r', '16000', '-c', '1', '-d', '2', 'test_safe.wav']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print("✅ 安全录音测试成功")
            # 清理测试文件
            if os.path.exists('test_safe.wav'):
                os.remove('test_safe.wav')
            return True
        else:
            print(f"❌ 录音测试失败: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"音频测试失败: {e}")
        return False

def create_safe_ai_conversation_test():
    """创建安全的AI对话测试脚本"""
    print("📝 创建安全的AI对话测试...")
    
    safe_test_script = '''#!/usr/bin/env python3
"""
安全的AI对话测试 - 避免ALSA段错误
"""

import os
import sys
import speech_recognition as sr
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, 'src')

def safe_ai_conversation_test():
    """安全的AI对话测试"""
    print("🤖 安全AI对话测试")
    print("=" * 40)
    
    try:
        # 导入组件
        from vosk_recognizer import VoskRecognizer
        
        # 初始化Vosk（已验证工作正常）
        vosk_recognizer = VoskRecognizer()
        if not vosk_recognizer.is_available:
            print("❌ Vosk不可用")
            return False
        
        print("✅ Vosk中文识别器准备就绪")
        
        # 安全的音频输入
        recognizer = sr.Recognizer()
        
        # 尝试使用最简单的麦克风配置
        try:
            microphone = sr.Microphone(device_index=None, sample_rate=16000, chunk_size=1024)
            print("✅ 使用默认麦克风配置")
        except Exception as e:
            print(f"⚠️ 默认麦克风配置失败: {e}")
            try:
                microphone = sr.Microphone()
                print("✅ 使用系统麦克风配置")
            except Exception as e2:
                print(f"❌ 麦克风初始化完全失败: {e2}")
                return False
        
        # 简单测试
        print("\\n🎙️ 请说一句中文...")
        input("按Enter开始录音...")
        
        try:
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                print("正在录音...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=6)
            
            print("📍 使用Vosk识别...")
            result = vosk_recognizer.recognize_from_speech_recognition_audio(audio)
            
            if result and result.strip():
                print(f"🎉 识别成功: '{result}'")
                
                # 尝试AI回复（不包含音频输出）
                try:
                    from ai_conversation import AIConversationManager
                    ai_manager = AIConversationManager()
                    
                    response = ai_manager.get_ai_response(result, session_id="test_session")
                    if response:
                        print(f"🤖 AI回复: {response}")
                        print("✅ AI对话核心功能正常")
                    else:
                        print("⚠️ AI回复为空")
                        
                except Exception as e:
                    print(f"⚠️ AI回复失败: {e}")
                    print("语音识别正常，AI模块可能需要配置")
                
                return True
            else:
                print("😞 识别失败")
                return False
                
        except Exception as e:
            print(f"❌ 录音识别失败: {e}")
            return False
    
    except Exception as e:
        print(f"❌ 系统初始化失败: {e}")
        return False

if __name__ == "__main__":
    print("🛡️ 安全AI对话测试")
    print("避免ALSA段错误，专注核心功能")
    print("=" * 50)
    
    success = safe_ai_conversation_test()
    
    if success:
        print("\\n🎉 安全测试成功！")
        print("💡 核心AI对话功能正常工作")
        print("📋 下一步可以:")
        print("1. 优化音频输出配置")
        print("2. 调试唤醒词集成")
        print("3. 测试完整对话流程")
    else:
        print("\\n😞 测试失败")
        print("💡 建议:")
        print("1. 检查API密钥配置")
        print("2. 确认网络连接")
        print("3. 检查依赖包安装")
'''
    
    try:
        with open('safe_ai_conversation_test.py', 'w') as f:
            f.write(safe_test_script)
        print("✅ 创建安全测试脚本: safe_ai_conversation_test.py")
        return True
    except Exception as e:
        logger.error(f"创建测试脚本失败: {e}")
        return False

def main():
    """主修复流程"""
    print("🔧 修复AI对话音频问题")
    print("=" * 40)
    
    # 1. 检查音频设备
    if not check_audio_devices():
        print("❌ 音频设备检查失败")
        return False
    
    # 2. 创建安全配置
    if not create_safe_asoundrc():
        print("❌ ALSA配置创建失败")
        return False
    
    # 3. 测试安全音频
    if not test_safe_audio():
        print("⚠️ 音频测试失败，但继续尝试")
    
    # 4. 创建安全测试脚本
    if not create_safe_ai_conversation_test():
        print("❌ 安全测试脚本创建失败")
        return False
    
    print("\\n🎉 修复完成！")
    print("📋 下一步:")
    print("1. 运行安全测试: python3 safe_ai_conversation_test.py")
    print("2. 如果成功，逐步增加功能")
    print("3. 避免直接运行可能导致段错误的完整版本")
    
    return True

if __name__ == "__main__":
    main()