# AI桌宠故障排除指南

## 🚨 常见问题快速诊断

### 问题分类索引
- [音频系统问题](#音频系统问题)
- [语音识别问题](#语音识别问题)
- [AI对话问题](#ai对话问题)
- [硬件连接问题](#硬件连接问题)
- [系统服务问题](#系统服务问题)
- [性能问题](#性能问题)

---

## 🔊 音频系统问题

### 问题1: ALSA音频设备错误
**症状:**
```
ALSA lib confmisc.c:1281:(snd_func_refer) Unable to find definition 'cards.bcm2835_headpho.pcm.front.0:CARD=0'
Unknown PCM front/rear/surround
```

**原因:** 树莓派音频配置不正确或音频设备未正确识别

**解决方案:**
```bash
# 1. 检查音频设备
aplay -l
arecord -l

# 2. 重新配置ALSA
sudo rm -f ~/.asoundrc
sudo rm -f /etc/asound.conf

# 3. 创建正确的ALSA配置
cat > ~/.asoundrc << 'EOF'
pcm.!default {
    type pulse
}
ctl.!default {
    type pulse
}
EOF

# 4. 重启音频服务
sudo systemctl restart alsa-state
pulseaudio --kill
pulseaudio --start

# 5. 测试音频
speaker-test -t wav -c 2
```

### 问题2: SDL2 Mixer库缺失
**症状:**
```
libSDL2_mixer-2.0.so.0: cannot open shared object file: No such file or directory
音频播放系统初始化失败
```

**解决方案:**
```bash
# 安装SDL2音频库
sudo apt update
sudo apt install -y libsdl2-mixer-2.0-0 libsdl2-mixer-dev
sudo apt install -y libsdl2-2.0-0 libsdl2-dev

# 重新安装pygame
source .venv/bin/activate
pip uninstall pygame -y
pip install pygame --no-cache-dir

# 验证安装
python3 -c "import pygame; pygame.mixer.init(); print('SDL2 Mixer正常')"
```

### 问题3: 麦克风权限问题
**症状:** 无法录音或麦克风无响应

**解决方案:**
```bash
# 1. 检查用户权限
sudo usermod -a -G audio $USER
sudo usermod -a -G pulse-access $USER

# 2. 重新登录或重启
# 注销并重新登录，或者重启系统

# 3. 测试麦克风
arecord -d 5 -f cd test.wav
aplay test.wav
```

---

## 🎤 语音识别问题

### 问题4: Porcupine语言不匹配
**症状:**
```
Porcupine初始化失败: Keyword file (.ppn) and model file (.pv) should belong to the same language
File belongs to `zh` while model file (.pv) belongs to `en`
```

**解决方案:**
```bash
# 1. 检查唤醒词文件
ls -la src/wake_words/

# 2. 下载正确的中文模型
cd src/wake_words/
wget https://github.com/Picovoice/porcupine/raw/master/lib/common/porcupine_params_zh.pv

# 3. 更新配置文件
# 编辑 src/config.py，确保使用正确的模型文件
```

### 问题5: Whisper模型加载失败
**症状:**
```
WARNING - Whisper不可用，跳过模型加载
WARNING - Whisper初始化失败，将使用PocketSphinx
```

**解决方案:**
```bash
# 1. 重新安装Whisper
source .venv/bin/activate
pip uninstall openai-whisper -y
pip install openai-whisper --no-cache-dir

# 2. 下载模型（如果网络问题）
python3 -c "import whisper; whisper.load_model('base')"

# 3. 检查磁盘空间
df -h
# Whisper模型需要至少1GB空间

# 4. 降级到轻量级模型
# 编辑配置文件，使用'tiny'或'base'模型而不是'large'
```

---

## 🤖 AI对话问题

### 问题6: Gemini API未初始化
**症状:**
```
ERROR - Gemini模型未初始化，无法启动对话模式
ERROR - AI对话管理器启动失败
```

**解决方案:**
```bash
# 1. 检查API密钥配置
cat ~/.ai_pet_env | grep GEMINI_API_KEY

# 2. 设置正确的API密钥
nano ~/.ai_pet_env
# 添加或修改：
# export GEMINI_API_KEY="your_actual_api_key_here"

# 3. 重新加载环境变量
source ~/.ai_pet_env

# 4. 测试API连接
python3 -c "
import os
import google.generativeai as genai
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-pro')
print('Gemini API连接正常')
"

# 5. 获取API密钥
echo "请访问 https://makersuite.google.com/app/apikey 获取API密钥"
```

### 问题7: 网络连接问题
**症状:** AI响应超时或连接失败

**解决方案:**
```bash
# 1. 检查网络连接
ping -c 4 8.8.8.8
curl -I https://generativelanguage.googleapis.com

# 2. 检查防火墙设置
sudo ufw status
# 如果启用了防火墙，确保允许HTTPS出站连接

# 3. 配置代理（如果需要）
# 在 ~/.ai_pet_env 中添加：
# export HTTP_PROXY="http://proxy:port"
# export HTTPS_PROXY="https://proxy:port"

# 4. 测试DNS解析
nslookup generativelanguage.googleapis.com
```

---

## 🔌 硬件连接问题

### 问题8: OLED显示屏无响应
**症状:** 屏幕黑屏或显示异常

**解决方案:**
```bash
# 1. 检查I2C连接
sudo i2cdetect -y 1
# 应该看到设备地址（通常是0x3c或0x3d）

# 2. 检查I2C是否启用
sudo raspi-config
# Interface Options -> I2C -> Enable

# 3. 检查连线
# VCC -> 3.3V
# GND -> GND  
# SDA -> GPIO 2 (Pin 3)
# SCL -> GPIO 3 (Pin 5)

# 4. 测试OLED
python3 -c "
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial)
print('OLED连接正常')
"
```

### 问题9: 舵机控制异常
**症状:** 机器人动作不响应或异常

**解决方案:**
```bash
# 1. 检查GPIO权限
sudo usermod -a -G gpio $USER

# 2. 检查舵机电源
# 确保外部电源供应充足（5V 2A以上）

# 3. 测试舵机
python3 -c "
import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)
pwm = GPIO.PWM(18, 50)
pwm.start(7.5)
time.sleep(1)
pwm.stop()
GPIO.cleanup()
print('舵机测试完成')
"
```

---

## ⚙️ 系统服务问题

### 问题10: systemd服务启动失败
**症状:** 服务无法启动或频繁重启

**解决方案:**
```bash
# 1. 检查服务状态
sudo systemctl status ai-desktop-pet

# 2. 查看详细日志
sudo journalctl -u ai-desktop-pet -f

# 3. 检查服务文件
sudo systemctl cat ai-desktop-pet

# 4. 重新创建服务
sudo systemctl stop ai-desktop-pet
sudo systemctl disable ai-desktop-pet
sudo rm /etc/systemd/system/ai-desktop-pet.service

# 重新运行安装脚本创建服务
./install_ai_desktop_pet.sh

# 5. 手动测试
cd src
python3 robot_voice_web_control.py
```

### 问题11: 权限问题
**症状:** 文件访问被拒绝或设备无法打开

**解决方案:**
```bash
# 1. 检查文件权限
ls -la src/
ls -la src/data/

# 2. 修复权限
sudo chown -R $USER:$USER .
chmod +x *.sh
chmod -R 755 src/

# 3. 检查设备权限
ls -la /dev/i2c-*
ls -la /dev/snd/

# 4. 添加用户到相关组
sudo usermod -a -G audio,gpio,i2c,spi,dialout $USER
```

---

## 🚀 性能问题

### 问题12: 响应延迟过高
**症状:** AI回复慢，动作延迟

**解决方案:**
```bash
# 1. 检查系统资源
htop
free -h
df -h

# 2. 优化Python环境
source .venv/bin/activate
pip install --upgrade pip
pip install psutil

# 3. 调整配置参数
# 编辑 src/config.py
# 减少WHISPER_MODEL_SIZE = "tiny"
# 增加RESPONSE_TIMEOUT = 30

# 4. 清理临时文件
rm -rf src/data/temp/*
rm -rf ~/.cache/whisper/

# 5. 重启系统
sudo reboot
```

### 问题13: 内存不足
**症状:** 系统卡顿，进程被杀死

**解决方案:**
```bash
# 1. 增加交换空间
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# 设置 CONF_SWAPSIZE=1024
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# 2. 优化内存使用
# 在 ~/.ai_pet_env 中添加：
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128

# 3. 使用轻量级模型
# 编辑配置，使用更小的AI模型
```

---

## 🔧 诊断工具

### 系统健康检查脚本
```bash
#!/bin/bash
# 保存为 health_check.sh

echo "=== AI桌宠系统健康检查 ==="

# 检查Python环境
echo "1. Python环境检查..."
source .venv/bin/activate
python3 --version
pip list | grep -E "(google-generativeai|pvporcupine|pygame|whisper)"

# 检查音频系统
echo "2. 音频系统检查..."
aplay -l | head -5
arecord -l | head -5

# 检查硬件接口
echo "3. 硬件接口检查..."
sudo i2cdetect -y 1

# 检查API配置
echo "4. API配置检查..."
if [ -n "$GEMINI_API_KEY" ]; then
    echo "Gemini API密钥已配置"
else
    echo "⚠️  Gemini API密钥未配置"
fi

# 检查系统资源
echo "5. 系统资源检查..."
free -h
df -h /

# 检查服务状态
echo "6. 服务状态检查..."
sudo systemctl is-active ai-desktop-pet

echo "=== 检查完成 ==="
```

### 日志分析工具
```bash
#!/bin/bash
# 保存为 analyze_logs.sh

echo "=== 日志分析 ==="

# 系统服务日志
echo "1. 系统服务日志（最近50行）:"
sudo journalctl -u ai-desktop-pet -n 50 --no-pager

# 应用程序日志
echo "2. 应用程序日志:"
if [ -f "src/data/logs/ai_pet.log" ]; then
    tail -50 src/data/logs/ai_pet.log
else
    echo "应用程序日志文件不存在"
fi

# 错误统计
echo "3. 错误统计:"
sudo journalctl -u ai-desktop-pet --since "1 hour ago" | grep -i error | wc -l
echo "最近1小时内的错误数量"

echo "=== 分析完成 ==="
```

---

## 📞 获取帮助

### 联系方式
- 查看项目文档：`cat README.md`
- 检查配置文件：`cat src/config.py`
- 运行健康检查：`bash health_check.sh`
- 分析日志：`bash analyze_logs.sh`

### 报告问题时请提供
1. 错误日志：`sudo journalctl -u ai-desktop-pet -n 100`
2. 系统信息：`uname -a && cat /etc/os-release`
3. 硬件信息：`lscpu && free -h`
4. 配置信息：`cat ~/.ai_pet_env`（隐藏敏感信息）

### 重置系统
如果问题无法解决，可以完全重置：
```bash
# 停止服务
sudo systemctl stop ai-desktop-pet
sudo systemctl disable ai-desktop-pet

# 清理环境
rm -rf .venv
rm -rf src/data/temp/*
rm ~/.ai_pet_env

# 重新安装
./install_ai_desktop_pet.sh
```

---

**最后更新:** 2025年7月26日  
**版本:** 1.0  
**适用系统:** 树莓派4B, Ubuntu 20.04+