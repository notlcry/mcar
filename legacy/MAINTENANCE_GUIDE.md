# AI桌宠系统维护指南

## 📋 概述

本指南提供了AI桌宠系统的日常维护、定期检查、性能优化和长期运行的最佳实践。遵循本指南可以确保系统稳定运行并延长硬件寿命。

## 🗓️ 维护计划

### 日常维护（每天）

**自动化检查**：
```bash
#!/bin/bash
# daily_check.sh - 每日自动检查脚本

echo "=== $(date) 每日系统检查 ===" >> daily_check.log

# 检查服务状态
if systemctl is-active --quiet ai-desktop-pet@$USER.service; then
    echo "✅ 服务运行正常" >> daily_check.log
else
    echo "❌ 服务异常，尝试重启" >> daily_check.log
    sudo systemctl restart ai-desktop-pet@$USER.service
fi

# 检查磁盘空间
DISK_USAGE=$(df -h /home | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "⚠️ 磁盘使用率过高: ${DISK_USAGE}%" >> daily_check.log
fi

# 检查内存使用
MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ $MEM_USAGE -gt 85 ]; then
    echo "⚠️ 内存使用率过高: ${MEM_USAGE}%" >> daily_check.log
fi

# 检查API连接
python3 -c "
import requests
try:
    response = requests.get('http://localhost:5000/health', timeout=5)
    if response.status_code == 200:
        print('✅ API连接正常')
    else:
        print('❌ API响应异常')
except:
    print('❌ API连接失败')
" >> daily_check.log

echo "检查完成" >> daily_check.log
echo "" >> daily_check.log
```

**手动检查项目**：
- [ ] 检查Web界面是否正常访问
- [ ] 测试AI对话功能
- [ ] 验证语音识别和合成
- [ ] 检查OLED显示是否正常
- [ ] 测试机器人运动功能

### 周维护（每周）

```bash
#!/bin/bash
# weekly_maintenance.sh - 每周维护脚本

echo "=== $(date) 每周维护开始 ==="

# 1. 清理临时文件
echo "清理临时文件..."
find src/data/temp -type f -mtime +7 -delete
find /tmp -name "*ai_pet*" -mtime +7 -delete

# 2. 压缩旧日志
echo "压缩旧日志..."
find src/data/logs -name "*.log" -mtime +7 -exec gzip {} \;

# 3. 清理对话历史（保留30天）
echo "清理对话历史..."
python3 -c "
from memory_manager import MemoryManager
memory = MemoryManager()
cleaned = memory.cleanup_old_data(days=30)
print(f'清理了 {cleaned} 条旧记录')
"

# 4. 更新系统包
echo "更新系统包..."
sudo apt update
sudo apt list --upgradable

# 5. 检查硬件连接
echo "检查硬件连接..."
i2cdetect -y 1 > hardware_check.log
lsusb >> hardware_check.log
arecord -l >> hardware_check.log

# 6. 性能统计
echo "生成性能报告..."
python3 -c "
import psutil
import json
from datetime import datetime

stats = {
    'timestamp': datetime.now().isoformat(),
    'cpu_percent': psutil.cpu_percent(interval=1),
    'memory_percent': psutil.virtual_memory().percent,
    'disk_usage': psutil.disk_usage('/').percent,
    'temperature': psutil.sensors_temperatures().get('cpu_thermal', [{}])[0].get('current', 0)
}

with open('weekly_stats.json', 'a') as f:
    f.write(json.dumps(stats) + '\n')

print('性能统计已记录')
"

echo "每周维护完成"
```

### 月维护（每月）

```bash
#!/bin/bash
# monthly_maintenance.sh - 每月维护脚本

echo "=== $(date) 每月维护开始 ==="

# 1. 完整系统备份
echo "创建系统备份..."
BACKUP_DIR="backup_$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# 备份配置文件
cp ~/.ai_pet_env $BACKUP_DIR/
cp src/ai_pet_config.json $BACKUP_DIR/ 2>/dev/null || true

# 备份数据库
cp -r src/data/ai_memory $BACKUP_DIR/

# 备份重要日志
cp src/data/logs/*.log $BACKUP_DIR/ 2>/dev/null || true

# 压缩备份
tar -czf ${BACKUP_DIR}.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

echo "备份已创建: ${BACKUP_DIR}.tar.gz"

# 2. 系统更新
echo "执行系统更新..."
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y
sudo apt autoclean

# 3. Python包更新
echo "更新Python包..."
source .venv/bin/activate
pip list --outdated
# pip install --upgrade package_name  # 谨慎更新

# 4. 数据库优化
echo "优化数据库..."
python3 -c "
from memory_manager import MemoryManager
memory = MemoryManager()
memory.optimize_database()
print('数据库优化完成')
"

# 5. 硬件健康检查
echo "硬件健康检查..."
python3 -c "
import subprocess
import json

# 检查温度
try:
    temp = subprocess.check_output(['vcgencmd', 'measure_temp']).decode().strip()
    print(f'CPU温度: {temp}')
except:
    print('无法获取CPU温度')

# 检查电压
try:
    volt = subprocess.check_output(['vcgencmd', 'measure_volts']).decode().strip()
    print(f'电压: {volt}')
except:
    print('无法获取电压信息')

# 检查内存分配
try:
    mem_arm = subprocess.check_output(['vcgencmd', 'get_mem', 'arm']).decode().strip()
    mem_gpu = subprocess.check_output(['vcgencmd', 'get_mem', 'gpu']).decode().strip()
    print(f'ARM内存: {mem_arm}')
    print(f'GPU内存: {mem_gpu}')
except:
    print('无法获取内存分配信息')
"

echo "每月维护完成"
```

## 🔧 性能优化

### 系统性能调优

**1. 内存优化**：
```bash
# 调整交换空间使用策略
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# 优化内存回收
echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.conf

# 应用设置
sudo sysctl -p
```

**2. CPU优化**：
```bash
# 设置CPU调度器
echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 或者使用节能模式
echo 'powersave' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

**3. I/O优化**：
```bash
# 优化SD卡性能
echo 'deadline' | sudo tee /sys/block/mmcblk0/queue/scheduler

# 减少写入频率
sudo mount -o remount,noatime /
```

### 应用程序优化

**1. AI配置优化**：
```python
# 在config.py中调整
AI_SETTINGS = {
    "model": "gemini-1.5-flash",  # 使用更快的模型
    "temperature": 0.7,           # 适中的创造性
    "max_tokens": 150,            # 限制回复长度
    "max_history_length": 20,     # 减少历史长度
    "response_timeout": 10        # 设置超时时间
}
```

**2. 语音处理优化**：
```python
# 语音识别优化
VOICE_SETTINGS = {
    "energy_threshold": 300,      # 调整识别灵敏度
    "pause_threshold": 0.8,       # 优化暂停检测
    "phrase_threshold": 0.3,      # 短语检测阈值
    "sample_rate": 16000,         # 降低采样率
    "chunk_size": 1024           # 优化缓冲区大小
}
```

**3. 数据库优化**：
```python
# 定期优化数据库
def optimize_database():
    """优化SQLite数据库性能"""
    import sqlite3
    
    conn = sqlite3.connect('src/data/ai_memory/memory.db')
    cursor = conn.cursor()
    
    # 重建索引
    cursor.execute('REINDEX')
    
    # 清理碎片
    cursor.execute('VACUUM')
    
    # 更新统计信息
    cursor.execute('ANALYZE')
    
    conn.close()
    print("数据库优化完成")
```

## 📊 监控和告警

### 系统监控脚本

```bash
#!/bin/bash
# monitor.sh - 系统监控脚本

# 配置告警阈值
CPU_THRESHOLD=80
MEMORY_THRESHOLD=85
DISK_THRESHOLD=90
TEMP_THRESHOLD=70

# 获取系统指标
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
TEMP=$(vcgencmd measure_temp | sed 's/temp=//' | sed 's/°C//')

# 检查告警条件
ALERTS=""

if (( $(echo "$CPU_USAGE > $CPU_THRESHOLD" | bc -l) )); then
    ALERTS="$ALERTS\n⚠️ CPU使用率过高: ${CPU_USAGE}%"
fi

if [ $MEMORY_USAGE -gt $MEMORY_THRESHOLD ]; then
    ALERTS="$ALERTS\n⚠️ 内存使用率过高: ${MEMORY_USAGE}%"
fi

if [ $DISK_USAGE -gt $DISK_THRESHOLD ]; then
    ALERTS="$ALERTS\n⚠️ 磁盘使用率过高: ${DISK_USAGE}%"
fi

if (( $(echo "$TEMP > $TEMP_THRESHOLD" | bc -l) )); then
    ALERTS="$ALERTS\n🌡️ CPU温度过高: ${TEMP}°C"
fi

# 发送告警
if [ ! -z "$ALERTS" ]; then
    echo -e "$(date): 系统告警$ALERTS" >> alerts.log
    # 可以添加邮件或其他通知方式
fi

# 记录监控数据
echo "$(date),$CPU_USAGE,$MEMORY_USAGE,$DISK_USAGE,$TEMP" >> monitoring.csv
```

### 服务健康检查

```python
#!/usr/bin/env python3
# health_check.py - 服务健康检查

import requests
import json
import time
from datetime import datetime

def check_service_health():
    """检查服务健康状态"""
    health_status = {
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }
    
    # 检查Web服务
    try:
        response = requests.get('http://localhost:5000/health', timeout=5)
        health_status['checks']['web_service'] = {
            'status': 'ok' if response.status_code == 200 else 'error',
            'response_time': response.elapsed.total_seconds()
        }
    except Exception as e:
        health_status['checks']['web_service'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # 检查AI对话
    try:
        response = requests.post('http://localhost:5000/ai_chat', 
                               json={'message': 'health check'}, 
                               timeout=10)
        health_status['checks']['ai_conversation'] = {
            'status': 'ok' if response.status_code == 200 else 'error',
            'response_time': response.elapsed.total_seconds()
        }
    except Exception as e:
        health_status['checks']['ai_conversation'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # 检查语音控制
    try:
        response = requests.get('http://localhost:5000/voice_status', timeout=5)
        health_status['checks']['voice_control'] = {
            'status': 'ok' if response.status_code == 200 else 'error'
        }
    except Exception as e:
        health_status['checks']['voice_control'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # 保存健康检查结果
    with open('health_check.json', 'a') as f:
        f.write(json.dumps(health_status) + '\n')
    
    return health_status

if __name__ == '__main__':
    result = check_service_health()
    print(json.dumps(result, indent=2))
```

## 🔄 备份和恢复

### 自动备份策略

```bash
#!/bin/bash
# backup.sh - 自动备份脚本

BACKUP_BASE_DIR="/home/$USER/ai_pet_backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_BASE_DIR/backup_$DATE"

# 创建备份目录
mkdir -p $BACKUP_DIR

echo "开始备份到: $BACKUP_DIR"

# 1. 备份配置文件
echo "备份配置文件..."
cp ~/.ai_pet_env $BACKUP_DIR/ 2>/dev/null || echo "环境配置文件不存在"
cp src/ai_pet_config.json $BACKUP_DIR/ 2>/dev/null || echo "应用配置文件不存在"

# 2. 备份数据库
echo "备份数据库..."
if [ -d "src/data/ai_memory" ]; then
    cp -r src/data/ai_memory $BACKUP_DIR/
else
    echo "数据库目录不存在"
fi

# 3. 备份重要日志
echo "备份日志文件..."
if [ -d "src/data/logs" ]; then
    mkdir -p $BACKUP_DIR/logs
    cp src/data/logs/*.log $BACKUP_DIR/logs/ 2>/dev/null || echo "无日志文件"
fi

# 4. 备份自定义脚本
echo "备份自定义脚本..."
cp *.sh $BACKUP_DIR/ 2>/dev/null || echo "无自定义脚本"

# 5. 创建备份信息文件
cat > $BACKUP_DIR/backup_info.txt << EOF
备份时间: $(date)
系统版本: $(uname -a)
Python版本: $(python3 --version)
备份内容:
- 环境配置文件
- 应用配置文件
- AI记忆数据库
- 系统日志
- 自定义脚本

恢复说明:
1. 停止AI桌宠服务
2. 复制配置文件到对应位置
3. 恢复数据库文件
4. 重启服务
EOF

# 6. 压缩备份
echo "压缩备份文件..."
cd $BACKUP_BASE_DIR
tar -czf backup_$DATE.tar.gz backup_$DATE
rm -rf backup_$DATE

# 7. 清理旧备份（保留最近10个）
echo "清理旧备份..."
ls -t backup_*.tar.gz | tail -n +11 | xargs rm -f

echo "备份完成: $BACKUP_BASE_DIR/backup_$DATE.tar.gz"
```

### 恢复脚本

```bash
#!/bin/bash
# restore.sh - 系统恢复脚本

if [ $# -ne 1 ]; then
    echo "使用方法: $0 <backup_file.tar.gz>"
    echo "可用备份:"
    ls -la ~/ai_pet_backups/backup_*.tar.gz 2>/dev/null || echo "无可用备份"
    exit 1
fi

BACKUP_FILE=$1
TEMP_DIR="/tmp/ai_pet_restore_$$"

echo "开始恢复备份: $BACKUP_FILE"

# 1. 停止服务
echo "停止AI桌宠服务..."
sudo systemctl stop ai-desktop-pet@$USER.service

# 2. 解压备份
echo "解压备份文件..."
mkdir -p $TEMP_DIR
tar -xzf $BACKUP_FILE -C $TEMP_DIR

BACKUP_CONTENT=$(find $TEMP_DIR -name "backup_*" -type d | head -1)

if [ ! -d "$BACKUP_CONTENT" ]; then
    echo "错误: 无效的备份文件"
    rm -rf $TEMP_DIR
    exit 1
fi

# 3. 恢复配置文件
echo "恢复配置文件..."
if [ -f "$BACKUP_CONTENT/.ai_pet_env" ]; then
    cp "$BACKUP_CONTENT/.ai_pet_env" ~/.ai_pet_env
    echo "环境配置已恢复"
fi

if [ -f "$BACKUP_CONTENT/ai_pet_config.json" ]; then
    cp "$BACKUP_CONTENT/ai_pet_config.json" src/
    echo "应用配置已恢复"
fi

# 4. 恢复数据库
echo "恢复数据库..."
if [ -d "$BACKUP_CONTENT/ai_memory" ]; then
    rm -rf src/data/ai_memory
    cp -r "$BACKUP_CONTENT/ai_memory" src/data/
    echo "数据库已恢复"
fi

# 5. 恢复日志
echo "恢复日志文件..."
if [ -d "$BACKUP_CONTENT/logs" ]; then
    mkdir -p src/data/logs
    cp "$BACKUP_CONTENT/logs"/* src/data/logs/ 2>/dev/null || true
    echo "日志文件已恢复"
fi

# 6. 清理临时文件
rm -rf $TEMP_DIR

# 7. 重启服务
echo "重启AI桌宠服务..."
sudo systemctl start ai-desktop-pet@$USER.service

# 8. 检查服务状态
sleep 5
if systemctl is-active --quiet ai-desktop-pet@$USER.service; then
    echo "✅ 恢复成功，服务已启动"
else
    echo "❌ 恢复完成，但服务启动失败，请检查日志"
    systemctl status ai-desktop-pet@$USER.service
fi

echo "恢复完成"
```

## 🔐 安全维护

### 安全检查清单

**每月安全检查**：
- [ ] 更新系统安全补丁
- [ ] 检查用户权限设置
- [ ] 审查网络访问日志
- [ ] 验证API密钥安全性
- [ ] 检查文件权限设置

```bash
#!/bin/bash
# security_check.sh - 安全检查脚本

echo "=== AI桌宠安全检查 ==="

# 1. 检查文件权限
echo "检查关键文件权限..."
ls -la ~/.ai_pet_env
ls -la src/ai_pet_config.json
ls -la src/data/ai_memory/

# 2. 检查用户组
echo "检查用户组权限..."
groups $USER

# 3. 检查网络连接
echo "检查网络连接..."
netstat -tlnp | grep :5000

# 4. 检查进程
echo "检查运行进程..."
ps aux | grep -E "(python|robot_voice)"

# 5. 检查系统更新
echo "检查系统更新..."
apt list --upgradable 2>/dev/null | wc -l

# 6. 检查日志异常
echo "检查异常日志..."
grep -i "error\|fail\|exception" src/data/logs/*.log | tail -10

echo "安全检查完成"
```

### 数据隐私保护

```python
#!/usr/bin/env python3
# privacy_cleanup.py - 隐私数据清理

from memory_manager import MemoryManager
import os
import json

def cleanup_sensitive_data():
    """清理敏感数据"""
    memory = MemoryManager()
    
    # 1. 清理个人信息
    print("清理个人信息...")
    sensitive_keywords = ['姓名', '电话', '地址', '邮箱', '身份证']
    
    for keyword in sensitive_keywords:
        results = memory.search_conversations(keyword)
        for result in results:
            print(f"发现敏感信息: {result['user_input'][:50]}...")
            # 可以选择删除或匿名化
    
    # 2. 清理旧对话记录
    print("清理旧对话记录...")
    cleaned = memory.cleanup_old_data(days=90)
    print(f"清理了 {cleaned} 条旧记录")
    
    # 3. 匿名化用户偏好
    print("匿名化用户偏好...")
    preferences = memory.get_all_user_preferences()
    for pref in preferences:
        if pref['preference_type'] == 'user_info':
            # 匿名化处理
            memory.update_user_preference(
                pref['preference_type'],
                pref['key'],
                '***已匿名化***'
            )
    
    print("隐私数据清理完成")

if __name__ == '__main__':
    cleanup_sensitive_data()
```

## 📈 性能分析

### 性能监控脚本

```python
#!/usr/bin/env python3
# performance_analysis.py - 性能分析工具

import psutil
import time
import json
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

class PerformanceMonitor:
    def __init__(self):
        self.data = []
    
    def collect_metrics(self, duration=60):
        """收集性能指标"""
        print(f"收集性能数据，持续 {duration} 秒...")
        
        start_time = time.time()
        while time.time() - start_time < duration:
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_io': psutil.disk_io_counters()._asdict(),
                'network_io': psutil.net_io_counters()._asdict(),
                'process_count': len(psutil.pids())
            }
            
            # 获取AI桌宠进程信息
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                if 'robot_voice_web_control' in proc.info['name']:
                    metrics['ai_pet_process'] = proc.info
                    break
            
            self.data.append(metrics)
            time.sleep(5)
    
    def analyze_performance(self):
        """分析性能数据"""
        if not self.data:
            print("无性能数据")
            return
        
        # 计算平均值
        avg_cpu = sum(d['cpu_percent'] for d in self.data) / len(self.data)
        avg_memory = sum(d['memory_percent'] for d in self.data) / len(self.data)
        
        print(f"平均CPU使用率: {avg_cpu:.2f}%")
        print(f"平均内存使用率: {avg_memory:.2f}%")
        
        # 找出性能峰值
        max_cpu = max(self.data, key=lambda x: x['cpu_percent'])
        max_memory = max(self.data, key=lambda x: x['memory_percent'])
        
        print(f"CPU峰值: {max_cpu['cpu_percent']:.2f}% at {max_cpu['timestamp']}")
        print(f"内存峰值: {max_memory['memory_percent']:.2f}% at {max_memory['timestamp']}")
    
    def generate_report(self):
        """生成性能报告"""
        report = {
            'analysis_time': datetime.now().isoformat(),
            'data_points': len(self.data),
            'summary': {
                'avg_cpu': sum(d['cpu_percent'] for d in self.data) / len(self.data),
                'avg_memory': sum(d['memory_percent'] for d in self.data) / len(self.data),
                'max_cpu': max(d['cpu_percent'] for d in self.data),
                'max_memory': max(d['memory_percent'] for d in self.data)
            },
            'recommendations': []
        }
        
        # 生成建议
        if report['summary']['avg_cpu'] > 70:
            report['recommendations'].append("CPU使用率较高，建议优化AI模型参数")
        
        if report['summary']['avg_memory'] > 80:
            report['recommendations'].append("内存使用率较高，建议清理对话历史")
        
        with open('performance_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("性能报告已保存到 performance_report.json")

if __name__ == '__main__':
    monitor = PerformanceMonitor()
    monitor.collect_metrics(300)  # 收集5分钟数据
    monitor.analyze_performance()
    monitor.generate_report()
```

## 🔄 版本更新

### 更新检查脚本

```bash
#!/bin/bash
# update_check.sh - 检查更新

echo "检查AI桌宠系统更新..."

# 1. 检查Git更新
if [ -d ".git" ]; then
    echo "检查代码更新..."
    git fetch origin
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/main)
    
    if [ $LOCAL != $REMOTE ]; then
        echo "发现代码更新"
        git log --oneline $LOCAL..$REMOTE
        echo ""
        echo "运行以下命令更新:"
        echo "git pull origin main"
        echo "./install_ai_desktop_pet.sh"
    else
        echo "代码已是最新版本"
    fi
fi

# 2. 检查Python包更新
echo "检查Python包更新..."
source .venv/bin/activate
pip list --outdated

# 3. 检查系统包更新
echo "检查系统包更新..."
apt list --upgradable 2>/dev/null

echo "更新检查完成"
```

### 安全更新脚本

```bash
#!/bin/bash
# security_update.sh - 安全更新

echo "执行安全更新..."

# 1. 停止服务
sudo systemctl stop ai-desktop-pet@$USER.service

# 2. 备份当前配置
./backup.sh

# 3. 更新系统
sudo apt update
sudo apt upgrade -y

# 4. 更新Python包（谨慎）
source .venv/bin/activate
pip install --upgrade pip

# 只更新安全相关包
pip install --upgrade requests urllib3 certifi

# 5. 重启服务
sudo systemctl start ai-desktop-pet@$USER.service

# 6. 验证更新
sleep 10
if systemctl is-active --quiet ai-desktop-pet@$USER.service; then
    echo "✅ 安全更新完成，服务正常"
else
    echo "❌ 更新后服务异常，请检查"
fi
```

## 📋 维护检查清单

### 每日检查清单
- [ ] 服务运行状态正常
- [ ] Web界面可访问
- [ ] AI对话功能正常
- [ ] 语音识别工作正常
- [ ] 硬件连接正常
- [ ] 系统资源使用正常

### 每周检查清单
- [ ] 清理临时文件
- [ ] 压缩旧日志
- [ ] 清理对话历史
- [ ] 检查硬件连接
- [ ] 更新系统包列表
- [ ] 生成性能报告

### 每月检查清单
- [ ] 完整系统备份
- [ ] 系统安全更新
- [ ] 数据库优化
- [ ] 硬件健康检查
- [ ] 性能分析报告
- [ ] 安全检查
- [ ] 清理旧备份

### 季度检查清单
- [ ] 全面系统审计
- [ ] 硬件深度检查
- [ ] 性能基准测试
- [ ] 安全漏洞扫描
- [ ] 备份恢复测试
- [ ] 文档更新
- [ ] 用户培训

## 📞 维护支持

### 创建维护日志

```bash
# 创建维护日志模板
cat > maintenance_log.md << 'EOF'
# AI桌宠维护日志

## 维护记录

### YYYY-MM-DD - 维护类型
**执行人员**: 
**维护内容**: 
**发现问题**: 
**解决方案**: 
**后续建议**: 

---
EOF
```

### 联系支持

如需技术支持，请提供：
1. 系统诊断信息
2. 错误日志
3. 维护历史记录
4. 问题详细描述

---

*本维护指南将根据系统更新持续完善，建议定期查看最新版本。*