#!/usr/bin/python3
"""
增强语音控制系统设置脚本
配置Whisper、edge-tts、Porcupine等依赖
"""

import os
import sys
import subprocess
import json
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_python_packages():
    """检查Python包依赖"""
    print("=== 检查Python包依赖 ===")
    
    required_packages = [
        'speech_recognition',
        'pyaudio', 
        'edge-tts',
        'openai-whisper',
        'pvporcupine',
        'pygame',
        'google-generativeai'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - 缺失")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n缺失的包: {missing_packages}")
        print("请运行: pip install " + " ".join(missing_packages))
        return False
    else:
        print("\n所有Python包依赖已满足")
        return True

def check_system_dependencies():
    """检查系统依赖"""
    print("\n=== 检查系统依赖 ===")
    
    system_deps = [
        ('aplay', '音频播放'),
        ('ffmpeg', '音频处理'),
        ('portaudio19-dev', '音频录制（开发包）')
    ]
    
    available_deps = []
    
    for dep, description in system_deps:
        try:
            result = subprocess.run(['which', dep], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ {dep} - {description}")
                available_deps.append(dep)
            else:
                print(f"✗ {dep} - {description} (可选)")
        except:
            print(f"✗ {dep} - {description} (检查失败)")
    
    return len(available_deps) > 0

def setup_whisper_models():
    """设置Whisper模型"""
    print("\n=== 设置Whisper模型 ===")
    
    try:
        import whisper
        
        # 下载基础模型
        models_to_download = ['tiny', 'base']
        
        for model_name in models_to_download:
            try:
                print(f"下载Whisper {model_name} 模型...")
                model = whisper.load_model(model_name)
                print(f"✓ {model_name} 模型下载成功")
            except Exception as e:
                print(f"✗ {model_name} 模型下载失败: {e}")
        
        return True
        
    except ImportError:
        print("Whisper未安装，跳过模型下载")
        return False

def test_audio_system():
    """测试音频系统"""
    print("\n=== 测试音频系统 ===")
    
    try:
        import pyaudio
        
        # 测试音频输入
        pa = pyaudio.PyAudio()
        
        print("可用音频设备:")
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            print(f"  {i}: {info['name']} - 输入:{info['maxInputChannels']} 输出:{info['maxOutputChannels']}")
        
        # 查找默认输入设备
        try:
            default_input = pa.get_default_input_device_info()
            print(f"\n默认输入设备: {default_input['name']}")
        except:
            print("\n未找到默认输入设备")
        
        # 查找默认输出设备
        try:
            default_output = pa.get_default_output_device_info()
            print(f"默认输出设备: {default_output['name']}")
        except:
            print("未找到默认输出设备")
        
        pa.terminate()
        return True
        
    except Exception as e:
        print(f"音频系统测试失败: {e}")
        return False

def test_edge_tts():
    """测试edge-tts"""
    print("\n=== 测试Edge-TTS ===")
    
    try:
        import edge_tts
        import asyncio
        import tempfile
        import os
        
        async def test_synthesis():
            text = "这是语音合成测试"
            voice = "zh-CN-XiaoxiaoNeural"
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            try:
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(temp_file_path)
                
                if os.path.exists(temp_file_path) and os.path.getsize(temp_file_path) > 0:
                    print("✓ Edge-TTS语音合成成功")
                    return True
                else:
                    print("✗ Edge-TTS语音合成失败")
                    return False
            finally:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
        
        return asyncio.run(test_synthesis())
        
    except Exception as e:
        print(f"✗ Edge-TTS测试失败: {e}")
        return False

def create_config_template():
    """创建配置模板"""
    print("\n=== 创建配置模板 ===")
    
    config_template = {
        "voice_control": {
            "wake_word": "喵喵小车",
            "conversation_timeout": 30,
            "use_whisper": True,
            "whisper_model": "base",
            "use_porcupine": False,
            "tts_voice": "zh-CN-XiaoxiaoNeural",
            "tts_rate": "+0%",
            "tts_volume": "+0%"
        },
        "audio": {
            "sample_rate": 16000,
            "channels": 1,
            "chunk_size": 1024,
            "energy_threshold": 300,
            "pause_threshold": 0.8
        },
        "ai_integration": {
            "confirmation_feedback": True,
            "emotional_responses": True,
            "context_memory": True
        }
    }
    
    config_file = "voice_control_config.json"
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_template, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 配置模板已创建: {config_file}")
        return True
        
    except Exception as e:
        print(f"✗ 配置模板创建失败: {e}")
        return False

def install_missing_packages():
    """安装缺失的包"""
    print("\n=== 安装缺失的包 ===")
    
    response = input("是否自动安装缺失的Python包？(y/n): ")
    if response.lower() != 'y':
        print("跳过自动安装")
        return False
    
    packages_to_install = [
        'edge-tts>=6.1.0',
        'openai-whisper>=20231117', 
        'pvporcupine>=3.0.0',
        'pygame>=2.1.0'
    ]
    
    for package in packages_to_install:
        try:
            print(f"安装 {package}...")
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', package
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ {package} 安装成功")
            else:
                print(f"✗ {package} 安装失败: {result.stderr}")
                
        except Exception as e:
            print(f"✗ {package} 安装异常: {e}")
    
    return True

def main():
    """主设置函数"""
    print("====== 增强语音控制系统设置 ======")
    print("此脚本将检查和配置语音控制系统的依赖")
    
    # 检查步骤
    steps = [
        ("Python包依赖", check_python_packages),
        ("系统依赖", check_system_dependencies), 
        ("音频系统", test_audio_system),
        ("Edge-TTS", test_edge_tts),
        ("Whisper模型", setup_whisper_models),
        ("配置模板", create_config_template)
    ]
    
    results = []
    
    for step_name, step_func in steps:
        print(f"\n{'='*50}")
        try:
            result = step_func()
            results.append((step_name, result))
        except Exception as e:
            print(f"步骤 '{step_name}' 执行失败: {e}")
            results.append((step_name, False))
    
    # 显示结果汇总
    print(f"\n{'='*50}")
    print("设置结果汇总:")
    
    for step_name, result in results:
        status = "✓ 成功" if result else "✗ 失败"
        print(f"  {step_name}: {status}")
    
    # 统计
    success_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    print(f"\n完成度: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    # 如果有失败的步骤，提供安装选项
    if success_count < total_count:
        print("\n有些依赖未满足，建议:")
        print("1. 检查错误信息并手动安装缺失的依赖")
        print("2. 运行自动安装（如果可用）")
        
        install_missing_packages()
    else:
        print("\n✓ 所有依赖都已满足，系统已准备就绪！")
        print("\n下一步:")
        print("1. 运行 python test_enhanced_voice_system.py 进行功能测试")
        print("2. 配置 voice_control_config.json 文件")
        print("3. 启动完整的语音控制系统")

if __name__ == "__main__":
    main()