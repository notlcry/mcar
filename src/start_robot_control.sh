#!/bin/bash
# 启动机器人控制脚本 - 优化内存使用

# 清理内存缓存
echo "正在释放系统缓存..."
sudo sync
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'

# 停止可能占用摄像头的进程
echo "停止可能占用摄像头的进程..."
sudo pkill -f raspistill
sudo pkill -f raspivid
sudo pkill -f python.*camera

# 确保v4l2驱动加载
echo "加载摄像头驱动..."
sudo modprobe bcm2835-v4l2

# 等待系统稳定
sleep 2

# 使用较少的资源启动应用
echo "启动机器人控制服务..."
cd "$(dirname "$0")"
python3 robot_web_control.py

exit 0 