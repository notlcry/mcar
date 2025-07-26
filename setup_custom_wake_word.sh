#!/bin/bash
# 配置自定义唤醒词脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 加载环境变量
source .ai_pet_env

echo "======================================"
echo "🎤 配置自定义唤醒词"
echo "======================================"

log_step "创建wake_words目录..."
mkdir -p src/wake_words

log_step "复制唤醒词文件..."
cp wake_words/kk_zh_raspberry-pi_v3_0_0.ppn src/wake_words/

log_step "下载中文模型文件..."
cd src/wake_words
if [[ ! -f "porcupine_params_zh.pv" ]]; then
    wget -O porcupine_params_zh.pv \
        "https://github.com/Picovoice/porcupine/raw/master/lib/common/porcupine_params_zh.pv" || \
    curl -L -o porcupine_params_zh.pv \
        "https://github.com/Picovoice/porcupine/raw/master/lib/common/porcupine_params_zh.pv"
fi
cd ../..

log_step "测试自定义唤醒词..."
python3 << 'EOF'
import os
import sys
sys.path.insert(0, 'src')

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

try:
    import pvporcupine
    
    access_key = os.getenv('PICOVOICE_ACCESS_KEY')
    
    # 测试自定义唤醒词
    porcupine = pvporcupine.create(
        access_key=access_key,
        model_path='src/wake_words/porcupine_params_zh.pv',
        keyword_paths=['src/wake_words/kk_zh_raspberry-pi_v3_0_0.ppn']
    )
    
    print("✅ 自定义唤醒词 'kk' 配置成功！")
    print(f"   采样率: {porcupine.sample_rate}")
    print(f"   帧长度: {porcupine.frame_length}")
    
    porcupine.delete()
    
except Exception as e:
    print(f"❌ 自定义唤醒词配置失败: {e}")
    
    # 尝试内置英文关键词作为备选
    try:
        porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=['picovoice']
        )
        print("⚠️  使用内置英文关键词 'picovoice' 作为备选")
        porcupine.delete()
    except Exception as e2:
        print(f"❌ 备选方案也失败: {e2}")
EOF

echo
echo "======================================"
echo "✅ 自定义唤醒词配置完成"
echo "======================================"
echo
echo "🎤 使用方法："
echo "• 说中文 'kk' 来唤醒系统"
echo "• 如果不工作，可以说英文 'picovoice'"
echo
echo "🧪 测试唤醒词："
echo "python3 test_custom_wake_word.py"
echo
echo "🚀 启动系统："
echo "cd src && python3 robot_voice_web_control.py"
echo