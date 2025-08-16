# AI桌宠依赖版本说明

## 🔧 关键版本修复

### Google Generative AI 兼容性问题

**问题**：
- 最新版本的`google-generativeai`依赖较新的`grpcio`版本
- 树莓派ARM架构的`grpcio`编译版本存在GLIBC兼容性问题

**解决方案**：
- 使用`google-generativeai==0.3.2`（稳定版本）
- 使用`grpcio==1.44.0`（兼容ARM架构）
- 使用`grpcio-status==1.44.0`（匹配grpcio版本）

## 📋 固定版本列表

### 核心AI依赖
```
google-generativeai==0.3.2
grpcio==1.44.0
grpcio-status==1.44.0
```

### 语音处理依赖
```
pvporcupine>=3.0.0
edge-tts>=6.1.0
SpeechRecognition>=3.8.1
pocketsphinx>=0.1.15
```

### Web框架依赖
```
flask>=2.0.1,<3.0.0
jinja2>=3.0.0,<4.0.0
werkzeug>=2.0.0,<3.0.0
```

## 🎯 版本选择原则

### 固定版本（==）
用于已知有兼容性问题的包：
- `google-generativeai==0.3.2`
- `grpcio==1.44.0`
- `grpcio-status==1.44.0`

### 最低版本（>=）
用于稳定且向后兼容的包：
- `pvporcupine>=3.0.0`
- `edge-tts>=6.1.0`
- `flask>=2.0.1`

### 版本范围（>=,<）
用于需要控制上限的包：
- `flask>=2.0.1,<3.0.0`
- `numpy>=1.19.0,<2.0.0`

## 🔄 更新策略

### 何时更新版本
1. **安全更新**：立即更新
2. **功能更新**：测试后更新
3. **主版本更新**：谨慎评估

### 测试流程
1. 在开发环境测试
2. 在树莓派环境验证
3. 更新文档和脚本
4. 发布更新

## 🐛 已知问题和解决方案

### 问题1：GLIBC版本不兼容
**错误信息**：
```
GLIBCXX_3.4.29' not found
```

**解决方案**：
```bash
pip3 uninstall -y google-generativeai grpcio grpcio-status
pip3 install google-generativeai==0.3.2 grpcio==1.44.0 grpcio-status==1.44.0
```

### 问题2：OpenCV编译失败
**错误信息**：
```
Failed building wheel for opencv-python-headless
```

**解决方案**：
```bash
sudo apt install python3-opencv  # 使用系统版本
```

### 问题3：PyAudio安装失败
**错误信息**：
```
Failed building wheel for pyaudio
```

**解决方案**：
```bash
sudo apt install python3-pyaudio portaudio19-dev
```

## 📊 兼容性矩阵

| 组件 | 树莓派3B+ | 树莓派4B | Ubuntu ARM | 状态 |
|------|-----------|----------|------------|------|
| google-generativeai==0.3.2 | ✅ | ✅ | ✅ | 稳定 |
| grpcio==1.44.0 | ✅ | ✅ | ✅ | 稳定 |
| pvporcupine>=3.0.0 | ✅ | ✅ | ✅ | 稳定 |
| edge-tts>=6.1.0 | ✅ | ✅ | ✅ | 稳定 |
| opencv-python-headless | ❌ | ❌ | ⚠️ | 使用系统版本 |

## 🔧 维护命令

### 检查当前版本
```bash
pip3 list | grep -E "(google-generativeai|grpcio|pvporcupine|edge-tts)"
```

### 强制重装兼容版本
```bash
pip3 install --force-reinstall --no-cache-dir \
    google-generativeai==0.3.2 \
    grpcio==1.44.0 \
    grpcio-status==1.44.0
```

### 验证安装
```bash
python3 -c "
import google.generativeai as genai
import grpc
print(f'Google AI: {genai.__version__}')
print(f'gRPC: {grpc.__version__}')
print('✅ 兼容版本安装成功')
"
```

## 📝 更新日志

### v1.1.0 (2024-01-XX)
- 修复Google Generative AI兼容性问题
- 固定grpcio版本为1.44.0
- 更新所有安装脚本使用兼容版本

### v1.0.0 (2024-01-XX)
- 初始版本发布
- 支持基础AI对话功能