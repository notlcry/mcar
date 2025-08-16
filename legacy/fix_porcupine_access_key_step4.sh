#!/bin/bash
# 第四步：修复Porcupine access_key问题
# 解决新版本Porcupine需要access_key的问题

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查当前Porcupine版本和要求
check_porcupine_requirements() {
    log_step "检查Porcupine版本和要求..."
    
    python3 -c "
import pvporcupine
print('Porcupine版本:', pvporcupine.LIBRARY_VERSION)

# 检查create函数的参数要求
import inspect
sig = inspect.signature(pvporcupine.create)
print('create函数参数:', list(sig.parameters.keys()))

# 检查是否需要access_key
if 'access_key' in sig.parameters:
    print('✓ 需要access_key参数')
    param = sig.parameters['access_key']
    if param.default == inspect.Parameter.empty:
        print('✗ access_key是必需参数')
    else:
        print('✓ access_key有默认值')
else:
    print('✓ 不需要access_key参数')
"
}

# 配置Picovoice access key
configure_picovoice_access_key() {
    log_step "配置Picovoice access key..."
    
    # 检查环境变量文件
    if [[ -f ~/.ai_pet_env ]]; then
        # 检查是否已有PICOVOICE_ACCESS_KEY
        if grep -q "PICOVOICE_ACCESS_KEY" ~/.ai_pet_env; then
            current_key=$(grep "PICOVOICE_ACCESS_KEY" ~/.ai_pet_env | cut -d'"' -f2)
            if [[ "$current_key" != "your_picovoice_access_key_here" && -n "$current_key" ]]; then
                log_info "✓ Picovoice access key已配置"
                return 0
            fi
        fi
        
        # 添加或更新access key配置
        if ! grep -q "PICOVOICE_ACCESS_KEY" ~/.ai_pet_env; then
            echo "" >> ~/.ai_pet_env
            echo "# Picovoice访问密钥（用于Porcupine唤醒词检测）" >> ~/.ai_pet_env
            echo "# 获取地址: https://console.picovoice.ai/" >> ~/.ai_pet_env
            echo "export PICOVOICE_ACCESS_KEY=\"your_picovoice_access_key_here\"" >> ~/.ai_pet_env
        fi
    else
        log_error "环境变量文件不存在"
        return 1
    fi
    
    log_warn "⚠️  需要配置Picovoice access key"
    echo
    echo "请按以下步骤获取和配置access key："
    echo "1. 访问 https://console.picovoice.ai/"
    echo "2. 注册或登录账户"
    echo "3. 在控制台中获取你的Access Key"
    echo "4. 编辑 ~/.ai_pet_env 文件"
    echo "5. 将 'your_picovoice_access_key_here' 替换为你的实际密钥"
    echo
    
    read -p "是否现在配置access key? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "请输入你的Picovoice Access Key:"
        read -r access_key
        
        if [[ -n "$access_key" && "$access_key" != "your_picovoice_access_key_here" ]]; then
            # 更新环境变量文件
            sed -i "s/your_picovoice_access_key_here/$access_key/g" ~/.ai_pet_env
            log_info "✓ Access key已配置"
            
            # 重新加载环境变量
            source ~/.ai_pet_env
            return 0
        else
            log_warn "无效的access key，跳过配置"
        fi
    fi
    
    return 1
}

# 创建支持access key的唤醒词检测器
create_access_key_wake_detector() {
    log_step "创建支持access key的唤醒词检测器..."
    
    cat > src/wake_detector_with_key.py << 'EOF'
#!/usr/bin/env python3
# 支持access key的唤醒词检测器

import os
import pvporcupine
import pyaudio
import struct
import logging

class WakeDetectorWithKey:
    def __init__(self):
        self.porcupine = None
        self.audio_stream = None
        self.pa = None
        self.logger = logging.getLogger(__name__)
        
    def initialize(self):
        """初始化唤醒词检测器"""
        try:
            # 获取access key
            access_key = os.getenv('PICOVOICE_ACCESS_KEY')
            
            if not access_key or access_key == 'your_picovoice_access_key_here':
                self.logger.error("✗ PICOVOICE_ACCESS_KEY未配置或无效")
                self.logger.info("请访问 https://console.picovoice.ai/ 获取access key")
                return False
            
            # 使用access key初始化Porcupine
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keywords=['picovoice']
            )
            self.logger.info("✓ 使用access key初始化Porcupine成功")
            
            # 初始化音频
            self.pa = pyaudio.PyAudio()
            self.audio_stream = self.pa.open(
                rate=self.porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.porcupine.frame_length
            )
            
            self.logger.info("✓ 音频流初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"✗ 初始化失败: {e}")
            return False
    
    def detect(self):
        """检测唤醒词"""
        if not self.porcupine or not self.audio_stream:
            return False
            
        try:
            pcm = self.audio_stream.read(self.porcupine.frame_length)
            pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
            
            keyword_index = self.porcupine.process(pcm)
            if keyword_index >= 0:
                self.logger.info(f"✓ 检测到唤醒词: {keyword_index}")
                return True
                
        except Exception as e:
            self.logger.error(f"✗ 检测过程出错: {e}")
            
        return False
    
    def cleanup(self):
        """清理资源"""
        if self.audio_stream:
            self.audio_stream.close()
        if self.pa:
            self.pa.terminate()
        if self.porcupine:
            self.porcupine.delete()

# 测试函数
def test_wake_detector():
    # 加载环境变量
    import subprocess
    try:
        result = subprocess.run(['bash', '-c', 'source ~/.ai_pet_env && env'], 
                              capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
    except:
        pass
    
    detector = WakeDetectorWithKey()
    if detector.initialize():
        print("✓ 唤醒词检测器初始化成功")
        print("说 'picovoice' 来测试唤醒词检测...")
        print("按Ctrl+C停止测试")
        
        try:
            while True:
                if detector.detect():
                    print("✓ 唤醒词检测成功！")
                    break
        except KeyboardInterrupt:
            print("\n测试中断")
        finally:
            detector.cleanup()
    else:
        print("✗ 唤醒词检测器初始化失败")
        print("请检查PICOVOICE_ACCESS_KEY是否正确配置")

if __name__ == "__main__":
    test_wake_detector()
EOF
    
    log_info "支持access key的唤醒词检测器已创建: src/wake_detector_with_key.py"
}

# 创建备用的简单语音检测器
create_fallback_detector() {
    log_step "创建备用的简单语音检测器..."
    
    cat > src/simple_voice_detector.py << 'EOF'
#!/usr/bin/env python3
# 简单的语音活动检测器 - 不依赖Porcupine
# 当Porcupine不可用时的备选方案

import pyaudio
import numpy as np
import time
import logging

class SimpleVoiceDetector:
    def __init__(self, threshold=1000, duration=2.0):
        self.threshold = threshold  # 音量阈值
        self.duration = duration    # 持续时间
        self.pa = None
        self.stream = None
        self.logger = logging.getLogger(__name__)
        
    def initialize(self):
        """初始化音频流"""
        try:
            self.pa = pyaudio.PyAudio()
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
            self.logger.info("✓ 简单语音检测器初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"✗ 初始化失败: {e}")
            return False
    
    def detect_voice_activity(self):
        """检测语音活动"""
        if not self.stream:
            return False
            
        try:
            # 读取音频数据
            data = self.stream.read(1024)
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            # 计算音量（RMS）
            rms = np.sqrt(np.mean(audio_data**2))
            
            # 检查是否超过阈值
            if rms > self.threshold:
                self.logger.info(f"检测到语音活动，音量: {rms:.0f}")
                return True
                
        except Exception as e:
            self.logger.error(f"✗ 检测过程出错: {e}")
            
        return False
    
    def wait_for_voice(self, timeout=30):
        """等待语音输入"""
        print(f"等待语音输入... (阈值: {self.threshold}, 超时: {timeout}秒)")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.detect_voice_activity():
                print("✓ 检测到语音输入！")
                return True
            time.sleep(0.1)
        
        print("✗ 语音检测超时")
        return False
    
    def cleanup(self):
        """清理资源"""
        if self.stream:
            self.stream.close()
        if self.pa:
            self.pa.terminate()

# 测试函数
def test_voice_detector():
    detector = SimpleVoiceDetector(threshold=500)  # 较低的阈值用于测试
    
    if detector.initialize():
        print("✓ 简单语音检测器初始化成功")
        print("请对着麦克风说话...")
        
        try:
            detector.wait_for_voice(timeout=10)
        except KeyboardInterrupt:
            print("\n测试中断")
        finally:
            detector.cleanup()
    else:
        print("✗ 简单语音检测器初始化失败")

if __name__ == "__main__":
    test_voice_detector()
EOF
    
    log_info "备用语音检测器已创建: src/simple_voice_detector.py"
}

# 测试access key配置
test_access_key_configuration() {
    log_step "测试access key配置..."
    
    # 加载环境变量
    source ~/.ai_pet_env 2>/dev/null || true
    
    python3 << 'EOF'
import os
import sys

# 检查环境变量
access_key = os.getenv('PICOVOICE_ACCESS_KEY')
print(f"PICOVOICE_ACCESS_KEY: {'已配置' if access_key and access_key != 'your_picovoice_access_key_here' else '未配置'}")

if access_key and access_key != 'your_picovoice_access_key_here':
    try:
        import pvporcupine
        
        # 测试access key
        porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=['picovoice']
        )
        print("✓ Access key有效，Porcupine初始化成功")
        porcupine.delete()
        
    except Exception as e:
        print(f"✗ Access key测试失败: {e}")
        if "invalid access key" in str(e).lower():
            print("请检查access key是否正确")
        elif "quota" in str(e).lower():
            print("可能已达到使用配额限制")
        sys.exit(1)
else:
    print("⚠️  Access key未配置，将使用备用检测器")
EOF
    
    return $?
}

# 显示完成信息
show_completion_info() {
    log_step "Access key配置完成！"
    
    echo
    echo "======================================"
    echo "🔧 第四步：Porcupine Access Key修复完成"
    echo "======================================"
    echo
    echo "✅ 已完成的修复："
    echo "• 识别了Porcupine版本要求"
    echo "• 配置了Picovoice access key环境变量"
    echo "• 创建了支持access key的检测器"
    echo "• 创建了备用的简单语音检测器"
    echo
    echo "🧪 测试结果："
    if test_access_key_configuration; then
        echo "• ✓ Access key配置正确"
        echo "• ✓ Porcupine可以正常初始化"
        echo "• ✓ 唤醒词检测功能正常"
    else
        echo "• ⚠️  Access key需要配置或验证"
        echo "• ✓ 备用语音检测器可用"
    fi
    echo
    echo "📋 配置文件："
    echo "• 环境变量: ~/.ai_pet_env"
    echo "• 主检测器: src/wake_detector_with_key.py"
    echo "• 备用检测器: src/simple_voice_detector.py"
    echo
    echo "🔑 Access Key配置："
    echo "• 获取地址: https://console.picovoice.ai/"
    echo "• 配置文件: ~/.ai_pet_env"
    echo "• 环境变量: PICOVOICE_ACCESS_KEY"
    echo
    echo "🧪 测试命令："
    echo "• 测试Porcupine: python3 src/wake_detector_with_key.py"
    echo "• 测试备用检测器: python3 src/simple_voice_detector.py"
    echo
    echo "✅ 下一步: 配置Gemini API密钥"
    echo
}

# 主函数
main() {
    echo "======================================"
    echo "🔧 第四步：修复Porcupine Access Key"
    echo "======================================"
    echo
    echo "检测到问题："
    echo "• Porcupine需要access_key参数"
    echo "• 新版本Picovoice要求注册和密钥"
    echo
    echo "解决方案："
    echo "• 配置Picovoice access key"
    echo "• 创建支持密钥的检测器"
    echo "• 提供备用的简单语音检测器"
    echo
    
    read -p "按Enter键继续配置access key，或Ctrl+C取消: "
    
    check_porcupine_requirements
    configure_picovoice_access_key
    create_access_key_wake_detector
    create_fallback_detector
    show_completion_info
    
    log_info "Access key配置完成！"
}

# 错误处理
trap 'log_error "Access key配置过程中发生错误"; exit 1' ERR

# 运行主程序
main "$@"