# mcar 树莓派部署指南

从零开始在 Raspberry Pi 上部署 mcar Python Robot Service。

## 1. 硬件清单

### 必需

| 硬件 | 规格 | 备注 |
|------|------|------|
| Raspberry Pi 4B | 4GB+ RAM | 推荐 4GB 或 8GB |
| MicroSD 卡 | 32GB+ Class 10 | 推荐 64GB |
| 电源 | 5V/3A USB-C | 官方电源适配器推荐 |
| 网络 | Wi-Fi 或以太网 | 初始配置需要 |

### 可选硬件

| 硬件 | 型号 | 用途 | 需要的接口 |
|------|------|------|-----------|
| OLED 显示屏 | SSD1306 128x64 | 表情/文字显示 | I2C |
| 电机驱动板 | PCA9685 | 4 路电机 PWM 控制 | I2C |
| 超声波传感器 | HC-SR04 | 距离检测 | GPIO |
| 红外传感器 x2 | IR 避障模块 | 左右障碍物检测 | GPIO |
| 急停按钮 | 常开按钮 | 物理急停 | GPIO |
| USB 麦克风 | 任意 USB 麦克风 | 语音输入 | USB |
| 扬声器 | 3.5mm 或蓝牙 | 语音输出 | Audio Jack / BT |
| 直流电机 x4 | TT 马达 | 运动 | PCA9685 + GPIO |

## 2. GPIO 接线图

所有引脚使用 **BCM 编号**。

### 引脚映射表

| 设备 | BCM 引脚 | 物理引脚 | 方向 | 来源文件 |
|------|---------|---------|------|---------|
| 急停按钮 | GPIO17 | Pin 11 | IN (FALLING) | `modules/button/module.py` |
| 超声波 TRIG | GPIO27 | Pin 13 | OUT | `modules/sensor/driver.py` |
| 超声波 ECHO | GPIO22 | Pin 15 | IN | `modules/sensor/driver.py` |
| IR 左 | GPIO12 | Pin 32 | IN | `modules/sensor/driver.py` |
| IR 右 | GPIO16 | Pin 36 | IN | `modules/sensor/driver.py` |
| Motor D IN1 | GPIO25 | Pin 22 | OUT | `modules/motion/driver.py` |
| Motor D IN2 | GPIO24 | Pin 18 | OUT | `modules/motion/driver.py` |

### I2C 设备

| 设备 | I2C 总线 | 地址 | 来源文件 |
|------|---------|------|---------|
| SSD1306 OLED | Bus 1 | 0x3C | `modules/display/driver.py` |
| PCA9685 PWM | Bus 1 | 0x40 | `modules/motion/driver.py` |

I2C 使用 GPIO2 (SDA, Pin 3) 和 GPIO3 (SCL, Pin 5)。

### PCA9685 电机通道分配

| 电机 | PWM 通道 | Dir1 通道 | Dir2 通道 | 备注 |
|------|---------|----------|----------|------|
| Motor A (左前) | CH0 | CH2 | CH1 | 全 PCA9685 控制 |
| Motor B (右前) | CH5 | CH3 | CH4 | 全 PCA9685 控制 |
| Motor C (左后) | CH6 | CH8 | CH7 | 全 PCA9685 控制 |
| Motor D (右后) | CH11 | GPIO25 | GPIO24 | PWM + GPIO 方向控制 |

### 接线示意

```
Raspberry Pi 4B GPIO Header (BCM)
─────────────────────────────────
            3V3  [1 ] [2 ] 5V
    SDA (I2C) 2  [3 ] [4 ] 5V
    SCL (I2C) 3  [5 ] [6 ] GND
              4  [7 ] [8 ] 14
            GND  [9 ] [10] 15
  Button ← 17  [11] [12] 18
   U-TRIG ← 27  [13] [14] GND
   U-ECHO → 22  [15] [16] 23
            3V3  [17] [18] 24 → Motor D IN2
             10  [19] [20] GND
              9  [21] [22] 25 → Motor D IN1
             11  [23] [24] 8
            GND  [25] [26] 7
              0  [27] [28] 1
              5  [29] [30] GND
              6  [31] [32] 12 → IR Left
             13  [33] [34] GND
             19  [35] [36] 16 → IR Right
             26  [37] [38] 20
            GND  [39] [40] 21
```

## 3. 系统准备

### 3.1 烧录 Raspberry Pi OS

1. 下载 [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. 选择 **Raspberry Pi OS (64-bit)** — Lite 或 Desktop 均可
3. 在高级选项中配置：
   - 启用 SSH
   - 设置 Wi-Fi
   - 设置用户名/密码
   - 设置 hostname（如 `mcar`）
4. 烧录到 SD 卡，插入树莓派启动

### 3.2 基础配置

SSH 连接后：

```bash
# 启用 I2C 和 SPI
sudo raspi-config
# → Interface Options → I2C → Enable
# → Interface Options → SPI → Enable
# 完成后重启
sudo reboot
```

### 3.3 安装 Python 3.12 与 venv

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
python3 --version
```

### 3.4 安装系统依赖

```bash
sudo apt update
sudo apt install -y \
  git \
  python3 python3-pip python3-venv \
  portaudio19-dev \
  libjpeg-dev \
  i2c-tools
```

### 3.5 验证 I2C

```bash
# 检查 I2C 设备
i2cdetect -y 1
# 预期看到:
#   0x3c — OLED 显示屏
#   0x40 — PCA9685 电机驱动
```

### 3.6 GPIO 权限

```bash
# 将用户加入 gpio 组（避免 sudo 运行）
sudo usermod -aG gpio $USER
# 重新登录生效
```

## 4. 一键部署

```bash
# 1. 克隆项目
git clone https://github.com/YOUR_USER/mcar.git
cd mcar

# 2. 配置环境变量
cp .ai_pet_env.example .ai_pet_env
nano .ai_pet_env
# 可选: GEMINI_API_KEY="your_key_here"
# 未配置时硬件/API 仍可用，/api/chat 会返回 LLM 降级回复
# LLM proxy 可选:
#   LLM_PROVIDER=openai-compatible
#   LLM_MODEL=gpt-5.5
#   LLM_BASE_URL=https://proxy.198437.xyz/v1
#   PROXY_API_KEY=your_proxy_api_key
#   LLM_HTTP_TRUST_ENV=false
# 语音 ASR 可选:
#   aliyun_funasr_realtime + DASHSCOPE_API_KEY
#   python scripts/create_aliyun_asr_hotwords.py --env-file .ai_pet_env --write-env
#   qwen3_asr_local + QWEN3_ASR_URL=http://<mac-lan-ip>:8765
#   aliyun_nls + ALIYUN_NLS_APPKEY/TOKEN
# 语音体验可选:
#   VOICE_ACK_ENABLED=false
#   VOICE_WAKE_PROMPT_ENABLED=true
#   VOICE_WAKE_PROMPT=wake
#   VOICE_REPLY_MAX_CHARS=30
#   VOICE_FOLLOW_UP_ENABLED=true
#   VOICE_FOLLOW_UP_TIMEOUT_S=3
#   VOICE_FOLLOW_UP_MAX_TURNS=4
#   VOICE_PAUSE_THRESHOLD=0.45
#   VOICE_PHRASE_TIME_LIMIT=6

# 3. 运行安装脚本
chmod +x deploy/install.sh
./deploy/install.sh
```

安装脚本会自动：
- 检查 Python3
- 检测并安装缺失的系统依赖
- 检查 I2C 是否启用
- 创建 `.venv`
- 安装 Python Robot Service 依赖（树莓派上自动安装硬件 extras）
- 创建 data/ 目录
- 可选安装 systemd 服务

## 5. 验证

### 5.1 启动服务

```bash
# systemd 方式
sudo systemctl start mcar
sudo systemctl status mcar

# 或手动方式
./scripts/start_mcar.sh
# 或
.venv/bin/python -m robot_service --mock
```

### 5.2 检查状态

```bash
# 系统状态
curl -s http://localhost:8080/api/status | python3 -m json.tool

# 能力列表（应看到 6 个模块的能力）
curl -s http://localhost:8080/api/capabilities | python3 -m json.tool

# 系统健康
curl -s http://localhost:8080/api/health | python3 -m json.tool
```

### 5.3 简单对话测试

```bash
# 发送文本消息
curl -s -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "你好"}' | python3 -m json.tool
```

### 5.4 语音链路增量部署

Mac 上本地改完语音链路后，可用下面的脚本同步到树莓派、执行远端 smoke、重启服务，并自动跑 2 轮 E2E 延迟采集：

```bash
./scripts/deploy_pi_voice_update.sh
```

常用覆盖项：

```bash
PI_HOST=root@192.168.2.201 \
PI_DIR=/root/mcar \
BASE_URL=http://192.168.2.201:8080 \
ROUNDS=2 \
./scripts/deploy_pi_voice_update.sh
```

只检查将执行的命令：

```bash
./scripts/deploy_pi_voice_update.sh --dry-run
```

### 5.5 语音 E2E 延迟验证

```bash
python3 scripts/voice_e2e_probe.py \
  --base-url http://localhost:8080 \
  --rounds 2
```

**预期**: 输出每轮 `prompt/asr/llm/tts/action/total` 耗时，以及 ASR/LLM/TTS provider/model。远程从 Mac 验证时把 `--base-url` 改成 `http://<pi-ip>:8080`。

### 5.6 查看日志

```bash
# systemd 日志
journalctl -u mcar -f

# 或查看控制台输出（手动启动时直接可见）
```

## 6. 常见问题排查

### GPIO permission denied

```
RuntimeError: No access to /dev/mem
```

**解决**: 将用户加入 gpio 组并重新登录：

```bash
sudo usermod -aG gpio $USER
logout
# 重新 SSH 连接
```

### I2C 设备未识别

```bash
# 检查 I2C 是否启用
ls /dev/i2c-*
# 如果没有输出，启用 I2C:
sudo raspi-config  # → Interface Options → I2C → Enable
sudo reboot

# 检查设备连接
i2cdetect -y 1
# 看不到 0x3c 或 0x40 → 检查接线
```

### OLED 无显示

```bash
# 1. 检查 I2C 地址
i2cdetect -y 1
# 应该在 0x3c 位置看到设备

# 2. 检查中文字体
ls /usr/share/fonts/truetype/wqy/wqy-microhei.ttc
# 如果不存在，安装:
sudo apt install -y fonts-wqy-microhei

# 3. 检查 luma.oled 安装
python3 -c "from luma.oled.device import ssd1306; print('OK')"
```

### 语音模块不工作

```bash
# 检查麦克风
arecord -l
# 应该列出 USB 麦克风设备

# 检查扬声器
aplay -l
# 应该列出音频输出设备

# 测试录音
arecord -d 3 test.wav && aplay test.wav

# 检查 pyaudio
python3 -c "import pyaudio; print('OK')"

# 检查 openWakeWord provider
python3 -c "import openwakeword.model; print('OK')"

# 首次使用内置唤醒词模型时下载资源
python3 -c "from openwakeword.utils import download_models; download_models(['hey_jarvis_v0.1'])"
```

### 服务启动失败

```bash
# 查看详细错误
journalctl -u mcar --no-pager -n 50

# 常见原因:
# 1. LLM 回复降级 → 检查 GEMINI_API_KEY
# 2. venv 未创建 → ./deploy/install.sh
# 3. 依赖缺失 → .venv/bin/python -m pip install -e "modules[hw,voice,display,dev]"
```

## 7. 服务管理

```bash
# 启动/停止/重启
sudo systemctl start mcar
sudo systemctl stop mcar
sudo systemctl restart mcar

# 查看状态
sudo systemctl status mcar

# 开机自启
sudo systemctl enable mcar
sudo systemctl disable mcar

# 实时日志
journalctl -u mcar -f
```
