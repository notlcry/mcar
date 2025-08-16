#!/usr/bin/env python3
"""
AI桌宠运行时诊断脚本
检查所有依赖和配置，找出运行问题
"""

import os
import sys
import importlib
import traceback
from pathlib import Path

def load_env_file():
    """加载环境变量文件"""
    env_file = '.ai_pet_env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('export ') and '=' in line:
                    line = line.replace('export ', '').strip()
                    key, value = line.split('=', 1)
                    value = value.strip('"')
                    os.environ[key] = value
        print("✅ 环境变量文件加载成功")
        return True
    else:
        print("❌ 环境变量文件不存在")
        return False

def check_python_path():
    """检查Python路径"""
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    
    # 添加src目录到路径
    src_path = os.path.join(os.getcwd(), 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
        print(f"✅ 已添加src目录到Python路径: {src_path}")
    
    return True

def check_required_modules():
    """检查必需的Python模块"""
    print("\n🔍 检查Python模块依赖...")
    
    required_modules = [
        ('flask', 'Flask Web框架'),
        ('RPi.GPIO', '树莓派GPIO控制'),
        ('cv2', 'OpenCV图像处理'),
        ('pygame', '音频播放'),
        ('google.generativeai', 'Google Gemini API'),
        ('pvporcupine', 'Porcupine唤醒词检测'),
        ('speech_recognition', '语音识别'),
        ('edge_tts', '语音合成'),
        ('numpy', '数值计算'),
        ('threading', '多线程支持'),
        ('queue', '队列管理'),
        ('json', 'JSON处理'),
        ('time', '时间处理'),
        ('logging', '日志记录')
    ]
    
    missing_modules = []
    
    for module_name, description in required_modules:
        try:
            importlib.import_module(module_name)
            print(f"  ✅ {module_name} - {description}")
        except ImportError as e:
            print(f"  ❌ {module_name} - {description} (缺失: {e})")
            missing_modules.append(module_name)
        except Exception as e:
            print(f"  ⚠️  {module_name} - {description} (问题: {e})")
    
    return len(missing_modules) == 0, missing_modules

def check_project_files():
    """检查项目文件结构"""
    print("\n📁 检查项目文件结构...")
    
    required_files = [
        'src/robot_voice_web_control.py',
        'src/config.py',
        'src/ai_conversation.py',
        'src/emotion_engine.py',
        'src/personality_manager.py',
        'src/safety_manager.py',
        'src/memory_manager.py',
        'src/enhanced_voice_control.py',
        'src/LOBOROBOT.py',
        'src/voice_control.py',
        'src/templates/voice_index.html',
        '.ai_pet_env'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} (缺失)")
            missing_files.append(file_path)
    
    return len(missing_files) == 0, missing_files

def check_api_configuration():
    """检查API配置"""
    print("\n🔑 检查API配置...")
    
    gemini_key = os.getenv('GEMINI_API_KEY')
    porcupine_key = os.getenv('PICOVOICE_ACCESS_KEY')
    
    if gemini_key:
        print(f"  ✅ Gemini API密钥已配置: {gemini_key[:20]}...")
    else:
        print("  ❌ Gemini API密钥未配置")
    
    if porcupine_key:
        print(f"  ✅ Porcupine访问密钥已配置: {porcupine_key[:20]}...")
    else:
        print("  ⚠️  Porcupine访问密钥未配置 (可选)")
    
    return bool(gemini_key)

def test_module_imports():
    """测试模块导入"""
    print("\n🧪 测试项目模块导入...")
    
    project_modules = [
        'config',
        'ai_conversation', 
        'emotion_engine',
        'personality_manager',
        'safety_manager',
        'memory_manager',
        'enhanced_voice_control',
        'LOBOROBOT',
        'voice_control'
    ]
    
    import_errors = []
    
    for module_name in project_modules:
        try:
            module = importlib.import_module(module_name)
            print(f"  ✅ {module_name}")
        except ImportError as e:
            print(f"  ❌ {module_name} - 导入失败: {e}")
            import_errors.append((module_name, str(e)))
        except Exception as e:
            print(f"  ⚠️  {module_name} - 导入有问题: {e}")
            import_errors.append((module_name, str(e)))
    
    return len(import_errors) == 0, import_errors

def test_basic_functionality():
    """测试基本功能"""
    print("\n⚙️ 测试基本功能...")
    
    try:
        # 测试配置管理
        from config import ConfigManager
        config = ConfigManager()
        print("  ✅ 配置管理器初始化成功")
        
        # 测试AI对话管理器
        from ai_conversation import AIConversationManager
        ai_manager = AIConversationManager()
        print("  ✅ AI对话管理器初始化成功")
        
        # 测试情感引擎
        from emotion_engine import EmotionEngine
        emotion_engine = EmotionEngine()
        print("  ✅ 情感引擎初始化成功")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 基本功能测试失败: {e}")
        traceback.print_exc()
        return False

def check_hardware_permissions():
    """检查硬件权限"""
    print("\n🔧 检查硬件权限...")
    
    # 检查GPIO权限
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.cleanup()
        print("  ✅ GPIO权限正常")
    except Exception as e:
        print(f"  ❌ GPIO权限问题: {e}")
    
    # 检查音频设备
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.quit()
        print("  ✅ 音频设备访问正常")
    except Exception as e:
        print(f"  ❌ 音频设备访问问题: {e}")
    
    return True

def generate_startup_script():
    """生成启动脚本"""
    print("\n📝 生成启动脚本...")
    
    startup_script = '''#!/bin/bash
# AI桌宠启动脚本 - 自动生成

echo "🤖 启动AI桌宠系统..."

# 加载环境变量
if [ -f ".ai_pet_env" ]; then
    source .ai_pet_env
    echo "✅ 环境变量已加载"
else
    echo "❌ 环境变量文件不存在"
    exit 1
fi

# 检查必要的环境变量
if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ GEMINI_API_KEY未设置"
    exit 1
fi

# 进入src目录并启动
cd src

echo "🚀 启动主程序..."
python3 robot_voice_web_control.py

echo "🛑 程序已退出"
'''
    
    with open('start_ai_pet.sh', 'w') as f:
        f.write(startup_script)
    
    os.chmod('start_ai_pet.sh', 0o755)
    print("  ✅ 启动脚本已生成: start_ai_pet.sh")
    
    return True

def main():
    """主诊断函数"""
    print("=" * 60)
    print("🔍 AI桌宠运行时诊断")
    print("=" * 60)
    
    # 检查步骤
    checks = [
        ("加载环境变量", load_env_file),
        ("检查Python路径", check_python_path),
        ("检查Python模块", check_required_modules),
        ("检查项目文件", check_project_files),
        ("检查API配置", check_api_configuration),
        ("测试模块导入", test_module_imports),
        ("测试基本功能", test_basic_functionality),
        ("检查硬件权限", check_hardware_permissions),
        ("生成启动脚本", generate_startup_script)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        print(f"\n{'='*20} {check_name} {'='*20}")
        try:
            result = check_func()
            if isinstance(result, tuple):
                success, details = result
                results.append((check_name, success, details))
            else:
                results.append((check_name, result, None))
        except Exception as e:
            print(f"❌ {check_name}检查出错: {e}")
            results.append((check_name, False, str(e)))
    
    # 总结报告
    print("\n" + "=" * 60)
    print("📊 诊断结果总结")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for check_name, success, details in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{check_name:20} {status}")
        if not success and details:
            if isinstance(details, list):
                for detail in details[:3]:  # 只显示前3个错误
                    print(f"  - {detail}")
            else:
                print(f"  - {details}")
        if success:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 项检查通过")
    
    if passed == total:
        print("\n🎉 所有检查通过！系统应该可以正常启动")
        print("\n🚀 启动命令:")
        print("   ./start_ai_pet.sh")
        print("   或者: cd src && python3 robot_voice_web_control.py")
        print("\n🌐 Web界面地址:")
        print("   http://你的树莓派IP:5000")
    else:
        print(f"\n⚠️  {total - passed} 项检查失败，请解决以下问题:")
        
        failed_checks = [name for name, success, _ in results if not success]
        for i, check_name in enumerate(failed_checks, 1):
            print(f"   {i}. {check_name}")
        
        print("\n💡 建议:")
        print("   1. 检查缺失的Python模块: pip install <模块名>")
        print("   2. 确认API密钥配置正确")
        print("   3. 检查文件权限: chmod +x *.sh")
        print("   4. 查看详细错误信息并逐一解决")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  诊断被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 诊断过程出错: {e}")
        traceback.print_exc()
        sys.exit(1)