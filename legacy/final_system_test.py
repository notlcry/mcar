#!/usr/bin/env python3
# 最终系统测试 - 验证所有组件是否正常工作

import os
import sys
import subprocess

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

def test_audio_system():
    """测试音频系统"""
    print("🔊 测试音频系统...")
    
    try:
        import pygame
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        print("  ✅ pygame音频系统正常")
        pygame.mixer.quit()
        return True
    except Exception as e:
        print(f"  ❌ pygame音频系统异常: {e}")
        return False

def test_porcupine():
    """测试Porcupine唤醒词检测"""
    print("🎤 测试Porcupine唤醒词检测...")
    
    try:
        import pvporcupine
        
        access_key = os.getenv('PICOVOICE_ACCESS_KEY')
        if not access_key:
            print("  ❌ PICOVOICE_ACCESS_KEY未设置")
            return False
        
        porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=['picovoice']
        )
        print("  ✅ Porcupine初始化成功")
        porcupine.delete()
        return True
        
    except Exception as e:
        print(f"  ❌ Porcupine测试失败: {e}")
        return False

def test_gemini_api():
    """测试Gemini API"""
    print("🤖 测试Gemini 2.0 API...")
    
    try:
        import google.generativeai as genai
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("  ❌ GEMINI_API_KEY未设置")
            return False
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        response = model.generate_content("请简单回复'AI系统正常'")
        print(f"  ✅ Gemini 2.0连接成功")
        print(f"     回复: {response.text}")
        return True
        
    except Exception as e:
        print(f"  ❌ Gemini API测试失败: {e}")
        return False

def test_system_modules():
    """测试系统模块"""
    print("📦 测试系统模块...")
    
    sys.path.insert(0, 'src')
    
    modules_to_test = [
        ('config', '配置模块'),
        ('ai_conversation', 'AI对话模块'),
        ('enhanced_voice_control', '语音控制模块'),
        ('emotion_engine', '情感引擎'),
        ('personality_manager', '个性管理器'),
        ('memory_manager', '记忆管理器')
    ]
    
    success_count = 0
    
    for module_name, display_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"  ✅ {display_name}")
            success_count += 1
        except ImportError as e:
            print(f"  ❌ {display_name} - 导入失败: {e}")
        except Exception as e:
            print(f"  ⚠️  {display_name} - 有问题: {e}")
    
    return success_count == len(modules_to_test)

def test_main_application():
    """测试主应用程序"""
    print("🚀 测试主应用程序...")
    
    try:
        sys.path.insert(0, 'src')
        
        # 测试配置加载
        from config import ConfigManager
        config = ConfigManager()
        
        print(f"  ✅ 系统配置加载成功")
        print(f"     AI模型: {config.ai_config.model_name}")
        print(f"     语音引擎: {config.voice_config.tts_voice}")
        print(f"     个性名称: {config.personality_config.name}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 主应用程序测试失败: {e}")
        return False

def main():
    print("=" * 50)
    print("🧪 AI桌宠系统最终测试")
    print("=" * 50)
    print()
    
    tests = [
        ("音频系统", test_audio_system),
        ("Porcupine唤醒词", test_porcupine),
        ("Gemini 2.0 API", test_gemini_api),
        ("系统模块", test_system_modules),
        ("主应用程序", test_main_application)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name}测试出错: {e}")
            results.append((test_name, False))
        print()
    
    # 显示测试结果
    print("=" * 50)
    print("📊 测试结果总结")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print()
    print(f"总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print()
        print("🎉 所有测试通过！系统可以正常启动")
        print()
        print("🚀 启动命令:")
        print("   cd src && python3 robot_voice_web_control.py")
        print()
        print("🌐 Web界面:")
        print("   http://你的树莓派IP:5000")
        print()
        print("🎤 使用说明:")
        print("   • 说 'picovoice' 唤醒系统")
        print("   • 通过Web界面控制机器人")
        print("   • 与AI进行语音对话")
        
        return True
    else:
        print()
        print("⚠️  部分测试失败，请检查相关配置")
        print("📚 查看故障排除指南: cat TROUBLESHOOTING_GUIDE.md")
        
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)