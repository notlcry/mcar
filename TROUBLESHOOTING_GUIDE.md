# AI桌宠故障排除指南

## 🔍 概述

本指南提供了AI桌宠系统常见问题的诊断和解决方案。按照问题类型分类，帮助您快速定位和解决问题。

## 📋 目录

1. [快速诊断](#快速诊断)
2. [安装问题](#安装问题)
3. [启动问题](#启动问题)
4. [AI对话问题](#ai对话问题)
5. [语音控制问题](#语音控制问题)
6. [硬件问题](#硬件问题)
7. [网络问题](#网络问题)
8. [性能问题](#性能问题)
9. [系统服务问题](#系统服务问题)
10. [日志分析](#日志分析)

## 🚀 快速诊断

### 系统健康检查

运行以下命令进行快速系统检查：

```bash
# 检查系统状态
cd src
python3 -c "
import sys
print(f'Python版本: {sys.version}')

try:
    import requests
    response = requests.get('http://localhost:5000/health', timeout=5)
    print(f'系统状态: {response.json()}')
except Exception as e:
    print(f'系统未运行或有问题: {e}')

# 检查关键组件
components = ['google.generativeai', 'pvporcupine', 'edge_tts', 'pygame', 'RPi.GPIO']
for comp in components:
    try:
        __import__(comp)
        print(f'✅ {comp}: 正常')
    except ImportError as e:
        print(f'❌ {comp}: 缺失 - {e}')
"
```

### 硬件连接检查

```bash
# 检查I2C设备
i2cdetect -y 1

# 检查音频设备
arecord -l
aplay -l

# 检查USB设备
lsusb

# 检查GPIO权限
groups $USER | grep -E "(gpio|i2c|spi|audio)"
```

## 🔧 安装问题

### 问题1: 安装脚本执行失败

**症状**: 运行`./install_ai_desktop_pet.sh`时出错

**可能原因**:
- 权限不足
- 网络连接问题
- 系统包管理器问题

**解决方案**:

```bash
# 1. 检查脚本权限
ls -la install_ai_desktop_pet.sh
chmod +x install_ai_desktop_pet.sh

# 2. 检查网络连接
ping -c 3 google.com
ping -c 3 pypi.org

# 3. 更新包管理器
sudo apt update
sudo apt upgrade

# 4. 清理apt缓存
sudo apt clean
sudo apt autoclean

# 5. 重新运行安装
./install_ai_desktop_pet.sh
```

### 问题2: Python依赖安装失败

**症状**: pip安装包时出现错误

**解决方案**:

```bash
# 1. 升级pip
python3 -m pip install --upgrade pip

# 2. 清理pip缓存
pip cache purge

# 3. 使用国内镜像源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ package_name

# 4. 安装系统依赖
sudo apt install python3-dev build-essential

# 5. 单独安装问题包
pip install --no-cache-dir --force-reinstall package_name
```

### 问题3: 虚拟环境创建失败

**症状**: 无法创建或激活虚拟环境

**解决方案**:

```bash
# 1. 安装venv模块
sudo apt install python3-venv

# 2. 删除现有虚拟环境
rm -rf .venv

# 3. 重新创建
python3 -m venv .venv

# 4. 激活虚拟环境
source .venv/bin/activate

# 5. 验证虚拟环境
which python
which pip
```

## 🚀 启动问题

### 问题1: 主程序无法启动

**症状**: 运行`python3 robot_voice_web_control.py`时出错

**诊断步骤**:

```bash
# 1. 检查当前目录
pwd
ls -la robot_voice_web_control.py

# 2. 检查Python路径
which python3
python3 --version

# 3. 检查虚拟环境
echo $VIRTUAL_ENV
source .venv/bin/activate

# 4. 检查依赖
pip list | grep -E "(flask|opencv|RPi.GPIO)"

# 5. 运行调试模式
python3 robot_voice_web_control.py --debug
```

**常见错误及解决方案**:

```bash
# ModuleNotFoundError: No module named 'xxx'
pip install xxx

# Permission denied (GPIO)
sudo usermod -a -G gpio $USER
# 重新登录

# Port already in use
sudo lsof -i :5000
sudo kill -9 PID

# Camera not found
sudo modprobe bcm2835-v4l2
ls /dev/video*
```

### 问题2: Web界面无法访问

**症状**: 浏览器无法打开`http://IP:5000`

**解决方案**:

```bash
# 1. 检查服务是否运行
ps aux | grep robot_voice_web_control

# 2. 检查端口占用
sudo netstat -tlnp | grep :5000

# 3. 检查防火墙
sudo ufw status
sudo ufw allow 5000

# 4. 检查IP地址
hostname -I
ip addr show

# 5. 测试本地连接
curl http://localhost:5000/status
```

## 🤖 AI对话问题

### 问题1: AI对话无响应

**症状**: 发送消息后AI不回复

**诊断步骤**:

```bash
# 1. 检查API密钥
echo $GEMINI_API_KEY
source ~/.ai_pet_env
echo $GEMINI_API_KEY

# 2. 测试API连接
python3 -c "
import google.generativeai as genai
import os
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')
try:
    response = model.generate_content('Hello')
    print('API连接正常:', response.text[:50])
except Exception as e:
    print('API连接失败:', e)
"

# 3. 检查网络连接
ping -c 3 generativelanguage.googleapis.com

# 4. 查看错误日志
tail -f src/data/logs/error.log
```

**解决方案**:

```bash
# 1. 配置正确的API密钥
nano ~/.ai_pet_env
# 填入正确的GEMINI_API_KEY

# 2. 重新加载环境变量
source ~/.ai_pet_env

# 3. 检查API配额
# 访问 https://makersuite.google.com/app/apikey

# 4. 重启服务
sudo systemctl restart ai-desktop-pet@$USER.service
```

### 问题2: AI回复异常

**症状**: AI回复内容不合理或出现错误

**解决方案**:

```bash
# 1. 检查个性提示配置
python3 -c "
from config import config_manager
config = config_manager.get_ai_settings()
print('当前配置:', config)
"

# 2. 重置AI配置
python3 -c "
from config import config_manager
config_manager.reset_ai_settings()
print('AI配置已重置')
"

# 3. 清理对话历史
python3 -c "
from memory_manager import MemoryManager
memory = MemoryManager()
memory.cleanup_old_data(days=0)
print('对话历史已清理')
"

# 4. 调整AI参数
python3 -c "
from config import config_manager
config_manager.update_ai_settings(
    temperature=0.7,
    max_tokens=150
)
print('AI参数已调整')
"
```

## 🎤 语音控制问题

### 问题1: 麦克风无法识别

**症状**: 系统检测不到麦克风

**解决方案**:

```bash
# 1. 检查USB麦克风连接
lsusb | grep -i audio
dmesg | grep -i audio

# 2. 检查音频设备
arecord -l
cat /proc/asound/cards

# 3. 重新加载音频模块
sudo modprobe -r snd-usb-audio
sudo modprobe snd-usb-audio

# 4. 检查权限
groups $USER | grep audio
sudo usermod -a -G audio $USER

# 5. 测试录音
arecord -d 3 test.wav
aplay test.wav
```

### 问题2: 语音识别不准确

**症状**: 语音命令识别错误或无响应

**解决方案**:

```bash
# 1. 调整麦克风音量
alsamixer
# 调整Capture音量

# 2. 测试语音识别
python3 -c "
import speech_recognition as sr
r = sr.Recognizer()
with sr.Microphone() as source:
    print('请说话...')
    audio = r.listen(source, timeout=5)
    try:
        text = r.recognize_sphinx(audio, language='zh-CN')
        print('识别结果:', text)
    except Exception as e:
        print('识别失败:', e)
"

# 3. 调整识别参数
python3 -c "
from config import config_manager
config_manager.update_voice_settings(
    energy_threshold=300,
    pause_threshold=0.8
)
print('语音参数已调整')
"

# 4. 检查环境噪音
# 在安静环境中测试
# 调整麦克风距离（10-20cm）
```

### 问题3: TTS语音合成无声音

**症状**: AI回复文本正常但无语音输出

**解决方案**:

```bash
# 1. 检查音频输出设备
aplay -l
speaker-test -c 2

# 2. 测试TTS功能
python3 -c "
import asyncio
import edge_tts

async def test_tts():
    communicate = edge_tts.Communicate('你好，这是测试', 'zh-CN-XiaoxiaoNeural')
    await communicate.save('test.wav')
    print('TTS文件已生成')

asyncio.run(test_tts())
"

# 播放测试文件
aplay test.wav

# 3. 检查音频系统
pulseaudio --check -v
systemctl --user status pulseaudio

# 4. 重启音频服务
pulseaudio -k
pulseaudio --start
```

## 🔧 硬件问题

### 问题1: OLED显示屏无显示

**症状**: 表情动画不显示

**解决方案**:

```bash
# 1. 检查I2C连接
i2cdetect -y 1
# 应该看到设备地址（通常是0x3C或0x3D）

# 2. 检查I2C是否启用
sudo raspi-config
# Interface Options -> I2C -> Enable

# 3. 测试OLED显示
python3 -c "
try:
    from luma.oled.device import ssd1306
    from luma.core.interface.serial import i2c
    
    serial = i2c(port=1, address=0x3C)
    device = ssd1306(serial)
    print('OLED设备初始化成功')
    
    from PIL import Image, ImageDraw
    image = Image.new('1', (128, 64))
    draw = ImageDraw.Draw(image)
    draw.text((0, 0), 'Test', fill=255)
    device.display(image)
    print('测试图像已显示')
except Exception as e:
    print('OLED测试失败:', e)
"

# 4. 检查接线
# VCC -> 3.3V
# GND -> GND  
# SDA -> GPIO 2 (Pin 3)
# SCL -> GPIO 3 (Pin 5)
```

### 问题2: 机器人运动异常

**症状**: 运动指令无响应或动作异常

**解决方案**:

```bash
# 1. 检查GPIO权限
groups $USER | grep gpio
sudo usermod -a -G gpio $USER

# 2. 测试GPIO功能
python3 -c "
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    print('GPIO初始化成功')
    GPIO.cleanup()
except Exception as e:
    print('GPIO测试失败:', e)
"

# 3. 检查I2C设备（PCA9685）
i2cdetect -y 1
# 应该看到0x40地址

# 4. 测试电机控制
python3 -c "
try:
    from LOBOROBOT import LOBOROBOT
    robot = LOBOROBOT()
    print('机器人控制器初始化成功')
    robot.t_up(0.5)  # 测试前进
    robot.t_stop()
    print('运动测试完成')
except Exception as e:
    print('机器人控制测试失败:', e)
"

# 5. 检查电源和接线
# 确保电机电源充足
# 检查接线是否松动
```

### 问题3: 摄像头无法工作

**症状**: 视频流无法显示

**解决方案**:

```bash
# 1. 检查摄像头连接
ls /dev/video*
lsusb | grep -i camera

# 2. 启用摄像头接口（树莓派）
sudo raspi-config
# Interface Options -> Camera -> Enable

# 3. 测试摄像头
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
if cap.isOpened():
    ret, frame = cap.read()
    if ret:
        print('摄像头工作正常，图像尺寸:', frame.shape)
    else:
        print('无法读取摄像头图像')
    cap.release()
else:
    print('无法打开摄像头')
"

# 4. 检查摄像头占用
sudo lsof /dev/video0
sudo pkill -f camera

# 5. 重新加载摄像头模块
sudo modprobe -r bcm2835-v4l2
sudo modprobe bcm2835-v4l2
```

## 🌐 网络问题

### 问题1: 无法访问外部API

**症状**: AI对话或TTS功能无法使用

**解决方案**:

```bash
# 1. 检查网络连接
ping -c 3 google.com
ping -c 3 generativelanguage.googleapis.com

# 2. 检查DNS解析
nslookup generativelanguage.googleapis.com
cat /etc/resolv.conf

# 3. 检查防火墙
sudo ufw status
sudo iptables -L

# 4. 测试HTTPS连接
curl -I https://generativelanguage.googleapis.com

# 5. 检查代理设置
echo $http_proxy
echo $https_proxy
```

### 问题2: Web界面无法访问

**症状**: 局域网内其他设备无法访问

**解决方案**:

```bash
# 1. 检查绑定地址
netstat -tlnp | grep :5000

# 2. 修改绑定地址
# 在robot_voice_web_control.py中确保:
# app.run(host='0.0.0.0', port=5000)

# 3. 检查防火墙规则
sudo ufw allow 5000
sudo ufw reload

# 4. 检查路由
ip route show
```

## ⚡ 性能问题

### 问题1: 系统响应缓慢

**症状**: AI回复延迟高，界面卡顿

**解决方案**:

```bash
# 1. 检查系统资源
top
htop
free -h
df -h

# 2. 检查内存使用
ps aux --sort=-%mem | head -10

# 3. 清理系统缓存
sudo sync
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'

# 4. 优化配置
python3 -c "
from config import config_manager
config_manager.update_ai_settings(
    max_history_length=20,  # 减少历史长度
    temperature=0.5         # 降低创造性
)
print('性能配置已优化')
"

# 5. 重启服务
sudo systemctl restart ai-desktop-pet@$USER.service
```

### 问题2: 内存不足

**症状**: 系统出现OOM错误

**解决方案**:

```bash
# 1. 检查内存使用
free -h
cat /proc/meminfo

# 2. 增加交换空间
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 3. 清理对话历史
python3 -c "
from memory_manager import MemoryManager
memory = MemoryManager()
memory.cleanup_old_data(days=7)
print('历史数据已清理')
"

# 4. 调整服务资源限制
sudo systemctl edit ai-desktop-pet@$USER.service
# 添加:
# [Service]
# MemoryMax=512M
```

## 🔄 系统服务问题

### 问题1: 服务无法启动

**症状**: systemctl start失败

**解决方案**:

```bash
# 1. 检查服务状态
systemctl status ai-desktop-pet@$USER.service

# 2. 查看详细日志
journalctl -u ai-desktop-pet@$USER.service -f

# 3. 检查服务文件
systemctl cat ai-desktop-pet@$USER.service

# 4. 重新加载配置
sudo systemctl daemon-reload

# 5. 手动测试启动
cd src
source ../.venv/bin/activate
python3 robot_voice_web_control.py
```

### 问题2: 服务频繁重启

**症状**: 服务不稳定，经常重启

**解决方案**:

```bash
# 1. 查看重启日志
journalctl -u ai-desktop-pet@$USER.service | grep -i restart

# 2. 检查错误日志
tail -f src/data/logs/error.log

# 3. 调整重启策略
sudo systemctl edit ai-desktop-pet@$USER.service
# 添加:
# [Service]
# RestartSec=30
# StartLimitBurst=3

# 4. 检查资源限制
systemctl show ai-desktop-pet@$USER.service | grep -i memory
```

## 📊 日志分析

### 系统日志位置

```bash
# systemd服务日志
journalctl -u ai-desktop-pet@$USER.service

# 应用程序日志
tail -f src/data/logs/error.log
tail -f src/data/logs/conversation.log
tail -f src/data/logs/voice.log

# 系统日志
tail -f /var/log/syslog
dmesg | tail -20
```

### 常见错误模式

**1. API调用失败**
```
ERROR: Failed to call Gemini API: 403 Forbidden
解决: 检查API密钥和配额
```

**2. 硬件访问失败**
```
ERROR: [Errno 13] Permission denied: '/dev/i2c-1'
解决: 添加用户到i2c组
```

**3. 内存不足**
```
ERROR: MemoryError: Unable to allocate array
解决: 增加交换空间或优化内存使用
```

**4. 网络连接超时**
```
ERROR: requests.exceptions.ConnectTimeout
解决: 检查网络连接和防火墙
```

### 调试模式

```bash
# 启用详细日志
export DEBUG=1
python3 robot_voice_web_control.py

# 启用特定组件调试
export AI_DEBUG=1
export VOICE_DEBUG=1
export HARDWARE_DEBUG=1
```

## 🆘 紧急恢复

### 完全重置系统

```bash
# 1. 停止所有服务
sudo systemctl stop ai-desktop-pet@$USER.service

# 2. 备份重要数据
cp -r src/data/ai_memory ~/ai_pet_backup_$(date +%Y%m%d)

# 3. 重置配置
rm -f ~/.ai_pet_env
rm -f src/ai_pet_config.json

# 4. 重新安装
./install_ai_desktop_pet.sh

# 5. 恢复数据
cp -r ~/ai_pet_backup_*/memory.db src/data/ai_memory/
```

### 恢复出厂设置

```bash
# 完全清理并重新开始
rm -rf .venv
rm -rf src/data
rm -f ~/.ai_pet_env
sudo systemctl disable ai-desktop-pet@$USER.service
sudo rm -f /etc/systemd/system/ai-desktop-pet@$USER.service

# 重新安装
./install_ai_desktop_pet.sh
./setup_systemd_service.sh
```

## 📞 获取帮助

### 收集诊断信息

运行以下脚本收集系统信息：

```bash
#!/bin/bash
# 诊断信息收集脚本

echo "=== AI桌宠系统诊断信息 ===" > diagnostic_info.txt
echo "时间: $(date)" >> diagnostic_info.txt
echo "" >> diagnostic_info.txt

echo "=== 系统信息 ===" >> diagnostic_info.txt
uname -a >> diagnostic_info.txt
cat /etc/os-release >> diagnostic_info.txt
echo "" >> diagnostic_info.txt

echo "=== Python环境 ===" >> diagnostic_info.txt
python3 --version >> diagnostic_info.txt
pip list >> diagnostic_info.txt
echo "" >> diagnostic_info.txt

echo "=== 硬件信息 ===" >> diagnostic_info.txt
lsusb >> diagnostic_info.txt
i2cdetect -y 1 >> diagnostic_info.txt
arecord -l >> diagnostic_info.txt
echo "" >> diagnostic_info.txt

echo "=== 服务状态 ===" >> diagnostic_info.txt
systemctl status ai-desktop-pet@$USER.service >> diagnostic_info.txt
echo "" >> diagnostic_info.txt

echo "=== 最近日志 ===" >> diagnostic_info.txt
journalctl -u ai-desktop-pet@$USER.service -n 50 >> diagnostic_info.txt

echo "诊断信息已保存到 diagnostic_info.txt"
```

### 联系支持

提交问题时请包含：
1. 问题详细描述
2. 错误日志
3. 系统诊断信息
4. 复现步骤

---

*本指南持续更新中，如遇到未覆盖的问题，请查看GitHub Issues或提交新问题。*