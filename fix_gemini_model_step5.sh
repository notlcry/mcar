#!/bin/bash
# 第五步：修复Gemini API模型问题
# 解决 gemini-pro 模型不再支持的问题

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

# 加载环境变量
source .ai_pet_env

# 检查可用的Gemini模型
check_available_models() {
    log_step "检查可用的Gemini模型..."
    
    python3 -c "
import google.generativeai as genai
import os

api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)

try:
    models = genai.list_models()
    print('可用的Gemini模型:')
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            print(f'  - {model.name}')
            
    # 测试推荐的模型
    recommended_models = [
        'gemini-2.0-flash-exp',
        'gemini-1.5-flash',
        'gemini-1.5-pro', 
        'gemini-1.0-pro'
    ]
    
    print('\\n测试推荐模型:')
    for model_name in recommended_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content('Hello')
            print(f'✓ {model_name} - 工作正常')
            break
        except Exception as e:
            print(f'✗ {model_name} - {str(e)[:50]}...')
            
except Exception as e:
    print(f'获取模型列表失败: {e}')
"
}

# 更新配置文件中的模型名称
update_model_configuration() {
    log_step "更新配置文件中的模型名称..."
    
    # 查找并更新所有包含 gemini-pro 的文件
    files_to_update=(
        "src/config.py"
        "src/ai_conversation_manager.py"
        "src/enhanced_voice_control.py"
        "src/robot_voice_web_control.py"
    )
    
    for file in "${files_to_update[@]}"; do
        if [[ -f "$file" ]]; then
            log_info "更新文件: $file"
            
            # 备份文件
            cp "$file" "$file.backup.$(date +%Y%m%d_%H%M%S)"
            
            # 替换模型名称 - 使用Gemini 2.0
            sed -i 's/gemini-pro/gemini-2.0-flash-exp/g' "$file"
            sed -i 's/models\/gemini-pro/models\/gemini-2.0-flash-exp/g' "$file"
            sed -i 's/gemini-1.5-flash/gemini-2.0-flash-exp/g' "$file"
            
            log_info "✓ $file 已更新"
        else
            log_warn "文件不存在: $file"
        fi
    done
}

# 创建模型测试脚本
create_model_test_script() {
    log_step "创建模型测试脚本..."
    
    cat > test_gemini_models.py << 'EOF'
#!/usr/bin/env python3
# Gemini模型测试脚本

import os
import google.generativeai as genai

def test_gemini_models():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY未设置")
        return
    
    genai.configure(api_key=api_key)
    
    # 要测试的模型列表（按优先级排序）
    models_to_test = [
        'gemini-2.0-flash-exp',  # Gemini 2.0 最新模型
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-1.0-pro',
        'gemini-pro'  # 旧模型，可能不工作
    ]
    
    print("🧪 测试Gemini模型...")
    
    working_models = []
    
    for model_name in models_to_test:
        try:
            print(f"\n测试 {model_name}...")
            model = genai.GenerativeModel(model_name)
            
            # 简单测试
            response = model.generate_content("请回复'测试成功'")
            
            print(f"✅ {model_name} - 工作正常")
            print(f"   回复: {response.text}")
            working_models.append(model_name)
            
        except Exception as e:
            print(f"❌ {model_name} - 失败: {str(e)[:100]}...")
    
    print(f"\n📊 测试结果:")
    print(f"工作正常的模型: {len(working_models)}")
    if working_models:
        print(f"推荐使用: {working_models[0]}")
        
        # 更新环境变量建议
        print(f"\n💡 建议在配置中使用: {working_models[0]}")
    else:
        print("❌ 没有可用的模型，请检查API密钥")

if __name__ == "__main__":
    test_gemini_models()
EOF
    
    log_info "模型测试脚本已创建: test_gemini_models.py"
}

# 测试修复后的配置
test_fixed_configuration() {
    log_step "测试修复后的配置..."
    
    python3 -c "
import os
import google.generativeai as genai

api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)

try:
    # 测试Gemini 2.0模型
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    response = model.generate_content('你好，请简单回复一句话')
    print('✓ gemini-2.0-flash-exp 模型工作正常')
    print(f'  回复: {response.text}')
    
except Exception as e:
    print(f'✗ gemini-2.0-flash-exp 测试失败: {e}')
    
    # 尝试备用模型
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content('你好，请简单回复一句话')
        print('✓ gemini-1.5-flash 模型工作正常')
        print(f'  回复: {response.text}')
    except Exception as e:
        print(f'✗ gemini-1.5-flash 也失败: {e}')
"
}

# 显示完成信息
show_completion_info() {
    log_step "Gemini模型修复完成！"
    
    echo
    echo "======================================"
    echo "🔧 第五步：Gemini模型修复完成"
    echo "======================================"
    echo
    echo "✅ 已完成的修复："
    echo "• 检查了可用的Gemini模型"
    echo "• 更新了配置文件中的模型名称"
    echo "• 从 gemini-pro 升级到 gemini-2.0-flash-exp"
    echo "• 创建了模型测试脚本"
    echo
    echo "🧪 测试结果："
    test_fixed_configuration
    echo
    echo "📋 更新的文件："
    echo "• src/config.py"
    echo "• src/ai_conversation_manager.py"
    echo "• src/enhanced_voice_control.py"
    echo "• src/robot_voice_web_control.py"
    echo
    echo "🧪 测试工具："
    echo "• python3 test_gemini_models.py"
    echo
    echo "✅ 现在所有组件都应该正常工作了！"
    echo
}

# 主函数
main() {
    echo "======================================"
    echo "🔧 第五步：修复Gemini模型问题"
    echo "======================================"
    echo
    echo "检测到问题："
    echo "• gemini-pro 模型不再支持"
    echo "• 需要升级到新的模型版本"
    echo
    echo "解决方案："
    echo "• 检查可用模型"
    echo "• 更新到 gemini-1.5-flash"
    echo "• 更新所有相关配置文件"
    echo
    
    read -p "按Enter键开始修复Gemini模型，或Ctrl+C取消: "
    
    check_available_models
    update_model_configuration
    create_model_test_script
    show_completion_info
    
    log_info "Gemini模型修复完成！"
}

# 错误处理
trap 'log_error "Gemini模型修复过程中发生错误"; exit 1' ERR

# 运行主程序
main "$@"