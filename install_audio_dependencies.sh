#!/bin/bash
# 安装音频处理依赖 - 幂等脚本

echo "📦 安装音频处理依赖..."

# 检查Python版本
PYTHON_CMD="python3"
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "❌ Python3 未找到"
    exit 1
fi

echo "✅ 使用Python: $($PYTHON_CMD --version)"

# 检查pip
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo "❌ pip 未找到"
    exit 1
fi

echo "✅ pip 可用"

# 安装依赖
echo "🔄 安装 numpy..."
$PYTHON_CMD -m pip install numpy

echo "🔄 安装 scipy..."
$PYTHON_CMD -m pip install scipy

# 验证安装
echo "🧪 验证安装..."

if $PYTHON_CMD -c "import numpy; print(f'✅ numpy {numpy.__version__}')" 2>/dev/null; then
    echo "✅ numpy 安装成功"
else
    echo "❌ numpy 安装失败"
    exit 1
fi

if $PYTHON_CMD -c "import scipy; print(f'✅ scipy {scipy.__version__}')" 2>/dev/null; then
    echo "✅ scipy 安装成功"
else
    echo "❌ scipy 安装失败"
    exit 1
fi

echo "🎉 音频处理依赖安装完成！"
echo "💡 现在可以运行: python3 test_audio_fix.py"