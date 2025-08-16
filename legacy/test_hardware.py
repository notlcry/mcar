#!/usr/bin/env python3
"""
硬件测试脚本
测试树莓派硬件接口是否正常工作
"""

import sys
import subprocess
import time

def test_gpio():
    """测试GPIO接口"""
    print("🔌 测试GPIO接口...")
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        print("✅ GPIO接口正常")
        GPIO.cleanup()
        return True
    except Exception as e:
        print(f"❌ GPIO接口错误: {e}")
        return False

def test_i2c():
    """测试I2C接口"""
    print("🔗 测试I2C接口...")
    try:
        result = subprocess.run(['i2cdetect', '-y', '1'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ I2C接口正常")
            if '3c' in result.stdout or '3d' in result.stdout:
                print("  📺 检测到OLED显示设备")
            return True
        else:
            print("❌ I2C接口不可用")
            return False
    except Exception as e:
        print(f"❌ I2C测试失败: {e}")
        return False

def test_camera():
    """测试摄像头"""
    print("📷 测试摄像头...")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"✅ 摄像头正常 (分辨率: {frame.shape[1]}x{frame.shape[0]})")
                cap.release()
                return True
            else:
                print("❌ 摄像头无法读取图像")
                cap.release()
                return False
        else:
            print("❌ 摄像头无法打开")
            return False
    except Exception as e:
        print(f"❌ 摄像头测试失败: {e}")
        return False

def test_audio():
    """测试音频设备"""
    print("🎤 测试音频设备...")
    
    # 测试录音设备
    try:
        result = subprocess.run(['arecord', '-l'], 
                              capture_output=True, text=True, timeout=5)
        if 'card' in result.stdout:
            print("✅ 录音设备可用")
            audio_input = True
        else:
            print("❌ 未找到录音设备")
            audio_input = False
    except Exception as e:
        print(f"❌ 录音设备测试失败: {e}")
        audio_input = False
    
    # 测试播放设备
    try:
        result = subprocess.run(['aplay', '-l'], 
                              capture_output=True, text=True, timeout=5)
        if 'card' in result.stdout:
            print("✅ 播放设备可用")
            audio_output = True
        else:
            print("❌ 未找到播放设备")
            audio_output = False
    except Exception as e:
        print(f"❌ 播放设备测试失败: {e}")
        audio_output = False
    
    return audio_input and audio_output

def test_python_packages():
    """测试Python包"""
    print("🐍 测试Python包...")
    
    packages = [
        ('cv2', 'OpenCV'),
        ('numpy', 'NumPy'),
        ('RPi.GPIO', 'RPi.GPIO'),
        ('flask', 'Flask'),
        ('google.generativeai', 'Google AI'),
        ('speech_recognition', 'SpeechRecognition'),
        ('edge_tts', 'Edge-TTS'),
        ('pygame', 'Pygame'),
        ('pvporcupine', 'Picovoice'),
    ]
    
    success_count = 0
    for package, name in packages:
        try:
            __import__(package)
            print(f"✅ {name}")
            success_count += 1
        except ImportError:
            print(f"❌ {name}: 未安装")
        except Exception as e:
            print(f"❌ {name}: {e}")
    
    return success_count == len(packages)

def test_system_info():
    """显示系统信息"""
    print("💻 系统信息...")
    
    try:
        # 树莓派型号
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().strip('\x00')
            print(f"设备型号: {model}")
    except:
        print("设备型号: 未知")
    
    try:
        # CPU温度
        result = subprocess.run(['vcgencmd', 'measure_temp'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            temp = result.stdout.strip()
            print(f"CPU温度: {temp}")
    except:
        print("CPU温度: 无法获取")
    
    try:
        # 内存信息
        result = subprocess.run(['free', '-h'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Mem:' in line:
                    parts = line.split()
                    print(f"内存: {parts[1]} 总计, {parts[2]} 已用, {parts[3]} 可用")
                    break
    except:
        print("内存信息: 无法获取")

def main():
    """主测试函数"""
    print("🧪 AI桌宠硬件测试")
    print("==================")
    print()
    
    test_system_info()
    print()
    
    # 运行所有测试
    tests = [
        ("Python包", test_python_packages),
        ("GPIO接口", test_gpio),
        ("I2C接口", test_i2c),
        ("摄像头", test_camera),
        ("音频设备", test_audio),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name}测试 ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n" + "="*40)
    print("📊 测试结果汇总")
    print("="*40)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:12} : {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 项测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！系统准备就绪")
        return 0
    else:
        print("⚠️  部分测试失败，请检查硬件连接和配置")
        return 1

if __name__ == "__main__":
    sys.exit(main())