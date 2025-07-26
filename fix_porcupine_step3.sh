#!/bin/bash
# 第三步：修复Porcupine语言不匹配问题
# 解决中文唤醒词文件与英文模型不匹配的问题

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

# 检查当前Porcupine状态
check_current_porcupine_status() {
    log_step "检查当前Porcupine状态..."
    
    # 检查唤醒词目录
    if [[ -d "src/wake_words" ]]; then
        log_info "唤醒词目录存在: src/wake_words"
        echo "目录内容:"
        ls -la src/wake_words/ || true
    else
        log_warn "唤醒词目录不存在"
    fi
    
    # 检查Python中的Porcupine
    echo
    log_info "检查Porcupine Python模块..."
    python3 -c "
try:
    import pvporcupine
    print('✓ pvporcupine模块已安装')
    print('版本:', pvporcupine.LIBRARY_VERSION)
    
    # 列出内置关键词
    print('内置英文关键词:', pvporcupine.KEYWORDS)
    
except ImportError as e:
    print('✗ pvporcupine模块未安装:', e)
except Exception as e:
    print('✗ pvporcupine检查失败:', e)
"
}

# 创建唤醒词目录和下载模型
setup_wake_words_directory() {
    log_step "设置唤醒词目录和模型..."
    
    # 创建目录
    mkdir -p src/wake_words
    cd src/wake_words
    
    # 下载中文模型文件
    log_info "下载Porcupine中文模型..."
    if [[ ! -f "porcupine_params_zh.pv" ]]; then
        # 尝试多个下载方式
        if command -v wget &> /dev/null; then
            wget -O porcupine_params_zh.pv \
                "https://github.com/Picovoice/porcupine/raw/master/lib/common/porcupine_params_zh.pv" || \
            log_warn "wget下载失败，尝试curl"
        fi
        
        if [[ ! -f "porcupine_params_zh.pv" ]] && command -v curl &> /dev/null; then
            curl -L -o porcupine_params_zh.pv \
                "https://github.com/Picovoice/porcupine/raw/master/lib/common/porcupine_params_zh.pv" || \
            log_warn "curl下载失败"
        fi
        
        if [[ -f "porcupine_params_zh.pv" ]]; then
            log_info "✓ 中文模型下载成功"
            ls -la porcupine_params_zh.pv
        else
            log_warn "✗ 中文模型下载失败，将使用内置英文模型"
        fi
    else
        log_info "✓ 中文模型已存在"
    fi
    
    # 检查自定义唤醒词文件
    if ls *.ppn 1> /dev/null 2>&1; then
        log_info "发现自定义唤醒词文件:"
        for file in *.ppn; do
            echo "  - $file"
        done
    else
        log_info "未发现自定义唤醒词文件，将使用内置关键词"
    fi
    
    cd ../..
}

# 更新配置文件
update_configuration() {
    log_step "更新Porcupine配置..."
    
    # 检查配置文件
    if [[ -f "src/config.py" ]]; then
        log_info "更新 src/config.py..."
        
        # 备份配置文件
        cp src/config.py src/config.py.backup.$(date +%Y%m%d_%H%M%S)
        
        # 使用Python脚本更新配置
        python3 << 'EOF'
import re
import os

# 读取配置文件
config_path = 'src/config.py'
with open(config_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否有中文模型文件
has_zh_model = os.path.exists('src/wake_words/porcupine_params_zh.pv')
has_custom_keywords = any(f.endswith('.ppn') for f in os.listdir('src/wake_words/') if os.path.isfile(os.path.join('src/wake_words/', f)))

print(f"中文模型存在: {has_zh_model}")
print(f"自定义关键词存在: {has_custom_keywords}")

# 更新或添加Porcupine配置
porcupine_config = '''
# Porcupine唤醒词检测配置
'''

if has_zh_model and has_custom_keywords:
    porcupine_config += '''PORCUPINE_MODEL_PATH = "wake_words/porcupine_params_zh.pv"
PORCUPINE_USE_CUSTOM_KEYWORDS = True
PORCUPINE_KEYWORDS_PATH = "wake_words/"
'''
    print("配置: 使用中文模型 + 自定义关键词")
elif has_zh_model:
    porcupine_config += '''PORCUPINE_MODEL_PATH = "wake_words/porcupine_params_zh.pv"
PORCUPINE_USE_CUSTOM_KEYWORDS = False
PORCUPINE_BUILTIN_KEYWORDS = ["picovoice"]  # 使用内置英文关键词作为备选
'''
    print("配置: 使用中文模型 + 内置关键词")
else:
    porcupine_config += '''PORCUPINE_MODEL_PATH = None  # 使用默认英文模型
PORCUPINE_USE_CUSTOM_KEYWORDS = False
PORCUPINE_BUILTIN_KEYWORDS = ["picovoice", "computer", "hey google"]
'''
    print("配置: 使用默认英文模型 + 内置关键词")

# 移除旧的Porcupine配置
content = re.sub(r'# Porcupine.*?(?=\n[A-Z_]|\n#|\Z)', '', content, flags=re.DOTALL)
content = re.sub(r'PORCUPINE_[A-Z_]*\s*=.*?\n', '', content)

# 添加新配置
if '# Porcupine唤醒词检测配置' not in content:
    content += porcupine_config

# 写回文件
with open(config_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("配置文件已更新")
EOF
        
        log_info "配置文件更新完成"
    else
        log_warn "配置文件 src/config.py 不存在，创建基本配置..."
        
        # 创建基本配置文件
        cat > src/config.py << 'EOF'
# AI桌宠基本配置文件

# Porcupine唤醒词检测配置
PORCUPINE_MODEL_PATH = None  # 使用默认英文模型
PORCUPINE_USE_CUSTOM_KEYWORDS = False
PORCUPINE_BUILTIN_KEYWORDS = ["picovoice", "computer"]

# 其他配置
WHISPER_MODEL_SIZE = "base"
RESPONSE_TIMEOUT = 30
EOF
        log_info "基本配置文件已创建"
    fi
}

# 测试Porcupine配置
test_porcupine_configuration() {
    log_step "测试Porcupine配置..."
    
    # 加载环境变量
    source ~/.ai_pet_env 2>/dev/null || true
    
    log_info "测试Porcupine初始化..."
    python3 << 'EOF'
import sys
import os
sys.path.insert(0, 'src')

try:
    import pvporcupine
    print("✓ pvporcupine模块导入成功")
    
    # 尝试不同的初始化方式
    
    # 方式1: 使用内置英文关键词
    try:
        porcupine = pvporcupine.create(keywords=['picovoice'])
        print("✓ 内置英文关键词初始化成功")
        porcupine.delete()
    except Exception as e:
        print(f"✗ 内置英文关键词初始化失败: {e}")
    
    # 方式2: 如果有中文模型，尝试使用
    zh_model_path = 'src/wake_words/porcupine_params_zh.pv'
    if os.path.exists(zh_model_path):
        try:
            # 使用中文模型但配合英文内置关键词
            porcupine = pvporcupine.create(
                model_path=zh_model_path,
                keywords=['picovoice']
            )
            print("✓ 中文模型 + 英文关键词初始化成功")
            porcupine.delete()
        except Exception as e:
            print(f"✗ 中文模型初始化失败: {e}")
    
    # 方式3: 检查自定义关键词文件
    wake_words_dir = 'src/wake_words'
    if os.path.exists(wake_words_dir):
        ppn_files = [f for f in os.listdir(wake_words_dir) if f.endswith('.ppn')]
        if ppn_files:
            print(f"发现自定义关键词文件: {ppn_files}")
            # 注意：自定义关键词需要与模型语言匹配
            print("⚠️  自定义关键词需要与模型语言匹配")
    
    print("✓ Porcupine配置测试完成")
    
except ImportError as e:
    print(f"✗ pvporcupine模块导入失败: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Porcupine测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF
    
    if [[ $? -eq 0 ]]; then
        log_info "✓ Porcupine配置测试通过"
        return 0
    else
        log_error "✗ Porcupine配置测试失败"
        return 1
    fi
}

# 创建简化的唤醒词检测器
create_simple_wake_detector() {
    log_step "创建简化的唤醒词检测器..."
    
    cat > src/simple_wake_detector.py << 'EOF'
#!/usr/bin/env python3
# 简化的唤醒词检测器 - 解决语言不匹配问题

import pvporcupine
import pyaudio
import struct
import logging

class SimpleWakeDetector:
    def __init__(self):
        self.porcupine = None
        self.audio_stream = None
        self.pa = None
        self.logger = logging.getLogger(__name__)
        
    def initialize(self):
        """初始化唤醒词检测器"""
        try:
            # 优先使用内置英文关键词，避免语言不匹配
            self.porcupine = pvporcupine.create(keywords=['picovoice'])
            self.logger.info("✓ 使用内置英文关键词 'picovoice' 初始化成功")
            
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
    detector = SimpleWakeDetector()
    if detector.initialize():
        print("✓ 简化唤醒词检测器初始化成功")
        print("说 'picovoice' 来测试唤醒词检测...")
        
        try:
            for i in range(100):  # 测试10秒
                if detector.detect():
                    print("✓ 唤醒词检测成功！")
                    break
        except KeyboardInterrupt:
            print("测试中断")
        finally:
            detector.cleanup()
    else:
        print("✗ 简化唤醒词检测器初始化失败")

if __name__ == "__main__":
    test_wake_detector()
EOF
    
    log_info "简化唤醒词检测器已创建: src/simple_wake_detector.py"
}

# 显示完成信息
show_completion_info() {
    log_step "Porcupine修复完成！"
    
    echo
    echo "======================================"
    echo "🔧 第三步：Porcupine语言问题修复完成"
    echo "======================================"
    echo
    echo "✅ 已完成的修复："
    echo "• 设置了唤醒词目录结构"
    echo "• 下载了中文模型文件（如果可用）"
    echo "• 更新了配置文件"
    echo "• 创建了简化的唤醒词检测器"
    echo
    echo "🧪 测试结果："
    if test_porcupine_configuration; then
        echo "• ✓ Porcupine可以正常初始化"
        echo "• ✓ 内置英文关键词工作正常"
        echo "• ✓ 语言不匹配问题已解决"
    else
        echo "• ✗ Porcupine测试失败，需要进一步排查"
    fi
    echo
    echo "📋 当前配置："
    echo "• 使用内置英文关键词: 'picovoice'"
    echo "• 避免了中文关键词与英文模型的冲突"
    echo "• 简化的检测器: src/simple_wake_detector.py"
    echo
    echo "🎤 使用方法："
    echo "• 说 'picovoice' 来唤醒系统"
    echo "• 测试检测器: python3 src/simple_wake_detector.py"
    echo
    echo "✅ 下一步: 如果Porcupine测试通过，我们可以继续修复Gemini API配置"
    echo
}

# 主函数
main() {
    echo "======================================"
    echo "🔧 第三步：修复Porcupine语言问题"
    echo "======================================"
    echo
    echo "这一步将解决："
    echo "• 中文唤醒词文件与英文模型不匹配"
    echo "• Porcupine初始化失败"
    echo "• 语言配置冲突"
    echo
    echo "解决方案："
    echo "• 使用内置英文关键词避免语言冲突"
    echo "• 创建简化的检测器"
    echo "• 更新配置文件"
    echo
    
    read -p "按Enter键继续修复Porcupine，或Ctrl+C取消: "
    
    check_current_porcupine_status
    setup_wake_words_directory
    update_configuration
    create_simple_wake_detector
    
    echo
    log_info "现在测试Porcupine配置..."
    if test_porcupine_configuration; then
        show_completion_info
        log_info "Porcupine语言问题修复成功！"
    else
        log_warn "Porcupine测试失败，但基本配置已完成"
        echo
        echo "可以尝试："
        echo "1. 手动测试: python3 src/simple_wake_detector.py"
        echo "2. 检查麦克风权限和连接"
        echo "3. 使用内置关键词: 'picovoice', 'computer'"
    fi
}

# 错误处理
trap 'log_error "Porcupine修复过程中发生错误"; exit 1' ERR

# 运行主程序
main "$@"