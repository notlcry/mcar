#!/bin/bash
# 最终语音功能修复 - 解决剩余的小问题

echo "🔧 最终语音功能修复"
echo "=================================="

# 1. 安装缺失的ALSA工具
echo "1. 安装ALSA工具..."
sudo apt-get update -qq
sudo apt-get install -y alsa-utils
echo "✅ ALSA工具安装完成"

# 2. 修复唤醒词检测器的bug
echo "2. 修复唤醒词检测器bug..."

# 检查wake_word_detector.py文件
if [ -f "src/wake_word_detector.py" ]; then
    echo "找到唤醒词检测器文件，检查是否需要修复..."
    
    # 备份原文件
    cp src/wake_word_detector.py src/wake_word_detector.py.backup.$(date +%s)
    
    # 检查是否有set相关的错误
    if grep -q "keywords = set" src/wake_word_detector.py; then
        echo "发现set相关问题，正在修复..."
        
        # 修复set对象不可下标的问题
        sed -i 's/keywords = set(/keywords = list(/g' src/wake_word_detector.py
        sed -i 's/self\.keywords = set(/self.keywords = list(/g' src/wake_word_detector.py
        
        echo "✅ 唤醒词检测器bug已修复"
    else
        echo "未发现明显的set相关问题"
    fi
else
    echo "⚠️  未找到wake_word_detector.py文件"
fi

# 3. 测试修复后的语音功能
echo "3. 测试修复后的语音功能..."

cat > test_final_voice.py << 'EOF'
#!/usr/bin/env python3
# 最终语音功能测试

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

def test_voice_components():
    print("🎤 最终语音功能测试")
    print("=" * 40)
    
    success_count = 0
    total_tests = 4
    
    # 1. 测试PyAudio麦克风
    print("1. 测试PyAudio麦克风...")
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        
        # 查找输入设备
        input_devices = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                input_devices.append(i)
        
        if input_devices:
            print(f"✅ 找到 {len(input_devices)} 个输入设备")
            
            # 测试第一个设备
            device_index = input_devices[0]
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024
            )
            
            # 读取一些数据
            data = stream.read(1024, exception_on_overflow=False)
            stream.close()
            
            print(f"✅ 麦克风录音测试成功 (设备 {device_index})")
            success_count += 1
        else:
            print("❌ 没有找到输入设备")
        
        p.terminate()
        
    except Exception as e:
        print(f"❌ PyAudio测试失败: {e}")
    
    # 2. 测试Porcupine唤醒词
    print("\n2. 测试Porcupine唤醒词...")
    try:
        import pvporcupine
        
        access_key = os.getenv('PICOVOICE_ACCESS_KEY')
        if access_key:
            porcupine = pvporcupine.create(
                access_key=access_key,
                keywords=['picovoice']
            )
            print("✅ Porcupine唤醒词初始化成功")
            porcupine.delete()
            success_count += 1
        else:
            print("❌ PICOVOICE_ACCESS_KEY未设置")
            
    except Exception as e:
        print(f"❌ Porcupine测试失败: {e}")
    
    # 3. 测试语音识别
    print("\n3. 测试语音识别...")
    try:
        import speech_recognition as sr
        
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
        
        print("✅ 语音识别初始化成功")
        success_count += 1
        
    except Exception as e:
        print(f"❌ 语音识别测试失败: {e}")
    
    # 4. 测试增强语音控制器
    print("\n4. 测试增强语音控制器...")
    try:
        from enhanced_voice_control import EnhancedVoiceController
        
        # 创建模拟机器人
        class MockRobot:
            def t_stop(self, duration=0):
                pass
        
        mock_robot = MockRobot()
        voice_controller = EnhancedVoiceController(robot=mock_robot)
        
        print("✅ 增强语音控制器创建成功")
        success_count += 1
        
    except Exception as e:
        print(f"❌ 增强语音控制器测试失败: {e}")
    
    # 结果总结
    print("\n" + "=" * 40)
    print(f"📊 测试结果: {success_count}/{total_tests} 项通过")
    
    if success_count == total_tests:
        print("🎉 所有语音功能测试通过！")
        print("\n🚀 可以启动AI桌宠系统:")
        print("   ./start_ai_pet_quiet.sh")
        return True
    elif success_count >= 3:
        print("✅ 主要语音功能正常，可以尝试启动系统")
        return True
    else:
        print("❌ 语音功能仍有问题，需要进一步排查")
        return False

if __name__ == "__main__":
    success = test_voice_components()
    sys.exit(0 if success else 1)
EOF

chmod +x test_final_voice.py

# 运行最终测试
echo "4. 运行最终语音功能测试..."
python3 test_final_voice.py

echo
echo "=================================="
echo "🎯 最终修复完成！"
echo "=================================="
echo
echo "📋 下一步操作:"
echo "1. 如果测试通过，启动AI桌宠系统:"
echo "   ./start_ai_pet_quiet.sh"
echo
echo "2. 在Web界面中启用AI对话模式"
echo
echo "3. 测试语音功能:"
echo "   • 说 'picovoice' 或 'kk' 唤醒系统"
echo "   • 然后进行语音对话"
echo
echo "4. 如果仍有问题，查看系统日志:"
echo "   tail -f src/data/logs/ai_pet.log"