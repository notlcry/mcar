# AI桌宠安装脚本选择指南

## 🎯 快速选择

**树莓派4B用户（推荐）**：
```bash
./install_pi_system.sh
```

## 📋 所有安装脚本说明

### 主要安装脚本

| 脚本名称 | 适用场景 | 特点 | 推荐度 |
|---------|----------|------|--------|
| **install_pi_system.sh** | 树莓派4B | 系统级安装，解决OpenCV问题 | ⭐⭐⭐⭐⭐ |
| install_ai_desktop_pet.sh | 通用安装 | 完整功能，使用虚拟环境 | ⭐⭐⭐ |
| install_no_torch.sh | 快速体验 | 跳过torch，轻量级 | ⭐⭐⭐⭐ |

### 修复和特殊用途脚本

| 脚本名称 | 用途 | 何时使用 |
|---------|------|----------|
| fix_pi4b_install.sh | 修复torch问题 | 遇到torch安装失败时 |
| fix_opencv_install.sh | 修复OpenCV问题 | 遇到OpenCV编译失败时 |
| install_torch_raspberry_pi.sh | 可选安装torch | 需要Whisper高质量识别时 |

### 配置脚本

| 脚本名称 | 用途 | 必需性 |
|---------|------|--------|
| setup_api_keys.sh | 配置API密钥 | ✅ 必需 |
| setup_custom_wake_word.sh | 配置自定义唤醒词 | 🔄 可选 |
| setup_systemd_service.sh | 设置系统服务 | 🔄 可选 |

## 🚀 推荐安装流程

### 对于树莓派4B（你的情况）

```bash
# 1. 主安装（解决所有依赖问题）
chmod +x install_pi_system.sh
./install_pi_system.sh

# 2. 配置API密钥（必需）
chmod +x setup_api_keys.sh
./setup_api_keys.sh

# 3. 测试硬件（推荐）
python3 src/test_hardware.py

# 4. 启动系统
cd src
python3 robot_voice_web_control.py
```

### 可选步骤

```bash
# 配置自定义唤醒词（如果你训练了）
./setup_custom_wake_word.sh

# 设置系统服务（开机自启）
./setup_systemd_service.sh

# 安装Whisper（如果需要高质量语音识别）
./install_torch_raspberry_pi.sh
```

## ❌ 不推荐的脚本（针对你的情况）

- ~~install_ai_desktop_pet.sh~~ - 会遇到OpenCV编译问题
- ~~install_no_torch.sh~~ - 仍然会遇到OpenCV问题
- ~~fix_opencv_install.sh~~ - 已集成到install_pi_system.sh中

## 🔧 如果遇到问题

### 问题1：权限错误
```bash
chmod +x *.sh
```

### 问题2：之前安装失败
```bash
# 清理环境
rm -rf .venv
sudo pkill -f "pip install" || true
pip3 cache purge

# 重新安装
./install_pi_system.sh
```

### 问题3：系统包冲突
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 重新安装
./install_pi_system.sh
```

## 📊 安装后验证

运行以下命令验证安装：

```bash
# 硬件测试
python3 src/test_hardware.py

# 配置测试
python3 test_config.py

# 启动测试
cd src
python3 robot_voice_web_control.py
```

## 🎯 总结

**对于你的树莓派4B，最佳选择是**：

1. **install_pi_system.sh** - 主安装脚本
2. **setup_api_keys.sh** - 配置API密钥
3. **setup_custom_wake_word.sh** - 配置你训练的唤醒词

这个组合能解决所有已知问题，让你快速开始使用AI桌宠！🤖✨