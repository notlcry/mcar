#!/bin/bash
# 彻底修复Picovoice问题

echo "🔧 彻底修复Picovoice问题"
echo "======================="
echo

# 方法1: 重新安装Picovoice
echo "方法1: 重新安装Picovoice..."
pip3 uninstall -y pvporcupine
pip3 install --no-cache-dir pvporcupine==3.0.5

echo "测试重新安装后的Picovoice..."
python3 -c "
import os
import subprocess
# 确保PATH正确
os.environ['PATH'] = '/usr/bin:/bin:/usr/local/bin:' + os.environ.get('PATH', '')
try:
    import pvporcupine
    print('✅ 重新安装成功')
except Exception as e:
    print(f'❌ 重新安装失败: {e}')
"

# 如果重新安装失败，尝试方法2
if [ $? -ne 0 ]; then
    echo
    echo "方法2: 修补Picovoice源码..."
    
    # 找到Picovoice安装位置
    PICOVOICE_PATH=$(python3 -c "import pvporcupine; print(pvporcupine.__file__)" 2>/dev/null | sed 's/__init__.py//')
    
    if [ -n "$PICOVOICE_PATH" ]; then
        echo "Picovoice路径: $PICOVOICE_PATH"
        
        # 备份原文件
        sudo cp "${PICOVOICE_PATH}_util.py" "${PICOVOICE_PATH}_util.py.backup"
        
        # 修补_util.py文件
        sudo python3 -c "
import re

util_file = '${PICOVOICE_PATH}_util.py'
with open(util_file, 'r') as f:
    content = f.read()

# 替换有问题的subprocess调用
old_pattern = r\"cpu_info = subprocess\.check_output\(\['cat', '/proc/cpuinfo'\]\)\.decode\(\)\"
new_pattern = r\"cpu_info = subprocess.check_output(['/usr/bin/cat', '/proc/cpuinfo']).decode()\"

content = re.sub(old_pattern, new_pattern, content)

with open(util_file, 'w') as f:
    f.write(content)

print('✅ Picovoice源码已修补')
"
    fi
fi

echo
echo "最终测试..."
python3 -c "
import os
os.environ['PATH'] = '/usr/bin:/bin:/usr/local/bin:' + os.environ.get('PATH', '')
try:
    import pvporcupine
    print('✅ Picovoice修复成功！')
    
    # 测试创建实例
    porcupine = pvporcupine.create(
        access_key='test',  # 使用测试密钥
        keywords=['computer']
    )
    print('✅ Picovoice实例创建成功')
    porcupine.delete()
    
except Exception as e:
    print(f'❌ Picovoice仍有问题: {e}')
"

echo
echo "=============================="
echo "🎉 修复完成！"
echo "=============================="
echo
echo "现在可以启动完整版本："
echo "cd src && python3 robot_voice_web_control.py"
echo