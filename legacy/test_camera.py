#!/usr/bin/python3
"""
摄像头测试脚本 - 用于检测和测试树莓派摄像头
"""
import cv2
import time
import os

def test_normal_camera():
    """测试普通USB摄像头"""
    print("尝试打开普通USB摄像头...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("无法打开普通USB摄像头")
        return False
    
    print("USB摄像头打开成功")
    ret, frame = cap.read()
    
    if not ret:
        print("无法从USB摄像头读取图像")
        cap.release()
        return False
    
    print(f"成功读取USB摄像头图像: {frame.shape[1]}x{frame.shape[0]}")
    cv2.imwrite("usb_camera_test.jpg", frame)
    print("图像已保存到 usb_camera_test.jpg")
    cap.release()
    return True

def test_v4l2_camera():
    """测试使用V4L2接口的摄像头"""
    print("尝试使用V4L2打开摄像头...")
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        
        if not cap.isOpened():
            print("无法使用V4L2打开摄像头")
            return False
        
        print("V4L2摄像头打开成功")
        ret, frame = cap.read()
        
        if not ret:
            print("无法从V4L2摄像头读取图像")
            cap.release()
            return False
        
        print(f"成功读取V4L2摄像头图像: {frame.shape[1]}x{frame.shape[0]}")
        cv2.imwrite("v4l2_camera_test.jpg", frame)
        print("图像已保存到 v4l2_camera_test.jpg")
        cap.release()
        return True
    except Exception as e:
        print(f"V4L2测试异常: {e}")
        return False

def list_video_devices():
    """列出系统中的视频设备"""
    print("\n可用视频设备:")
    try:
        for i in range(10):
            device_path = f"/dev/video{i}"
            if os.path.exists(device_path):
                print(f"  发现设备: {device_path}")
    except Exception as e:
        print(f"列出视频设备时出错: {e}")

if __name__ == "__main__":
    print("====== 树莓派摄像头测试工具 ======")
    
    # 列出视频设备
    list_video_devices()
    
    # 测试普通摄像头
    normal_success = test_normal_camera()
    
    # 如果普通摄像头失败，尝试V4L2
    if not normal_success:
        v4l2_success = test_v4l2_camera()
        
    print("\n测试完成。")
    
    if normal_success or v4l2_success:
        print("结果: 摄像头测试成功！")
    else:
        print("结果: 所有摄像头测试均失败，请检查硬件连接和驱动。")
        print("\n故障排除提示:")
        print("1. 检查摄像头是否正确连接")
        print("2. 对于树莓派官方摄像头，确保在raspi-config中启用了摄像头")
        print("3. 尝试重启树莓派")
        print("4. 检查摄像头是否被其他程序占用") 