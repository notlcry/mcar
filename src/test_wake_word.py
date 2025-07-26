#!/usr/bin/env python3
"""
唤醒词测试脚本
用于测试自定义唤醒词是否正常工作
"""

import os
import sys
import time
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_env_file():
    """加载环境变量文件"""
    env_file = '../.ai_pet_env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    if line.startswith('export '):
                        line = line[7:]
                    key, value = line.split('=', 1)
                    os.environ[key] = value.strip('"\'')
        logger.info("环境变量已加载")

def test_wake_word():
    """测试唤醒词检测"""
    print("🎤 唤醒词测试程序")
    print("==================")
    print()
    
    # 加载环境变量
    load_env_file()
    
    # 检查访问密钥
    access_key = os.getenv('PICOVOICE_ACCESS_KEY')
    if not access_key or access_key == 'your_picovoice_access_key_here':
        print("❌ Picovoice访问密钥未配置")
        print("请运行: ./setup_custom_wake_word.sh")
        return
    
    print(f"✅ 访问密钥: {access_key[:10]}...")
    
    # 检查自定义唤醒词文件
    wake_word_files = []
    wake_words_dir = '../wake_words'
    
    if os.path.exists(wake_words_dir):
        for file in os.listdir(wake_words_dir):
            if file.endswith('.ppn'):
                wake_word_files.append(os.path.join(wake_words_dir, file))
    
    if not wake_word_files:
        print("❌ 未找到自定义唤醒词文件(.ppn)")
        print("请将训练好的.ppn文件放到 wake_words/ 目录")
        return
    
    print(f"✅ 找到唤醒词文件: {len(wake_word_files)}个")
    for file in wake_word_files:
        print(f"   - {os.path.basename(file)}")
    
    # 导入唤醒词检测器
    try:
        from wake_word_detector import WakeWordDetector
        print("✅ 唤醒词检测器模块导入成功")
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return
    
    # 初始化检测器
    print("\n🔧 初始化唤醒词检测器...")
    try:
        detector = WakeWordDetector(
            access_key=access_key,
            keyword_paths=wake_word_files,
            sensitivities=[0.5] * len(wake_word_files)
        )
        
        if detector.initialize():
            print("✅ 检测器初始化成功")
        else:
            print("❌ 检测器初始化失败")
            return
            
    except Exception as e:
        print(f"❌ 初始化错误: {e}")
        return
    
    # 开始检测
    print("\n🎯 开始唤醒词检测...")
    print("请说出你训练的唤醒词...")
    print("按 Ctrl+C 停止测试")
    print()
    
    def on_wake_word_detected(keyword_index):
        """唤醒词检测回调"""
        wake_word_name = os.path.basename(wake_word_files[keyword_index])
        print(f"🎉 检测到唤醒词: {wake_word_name}")
        print(f"时间: {time.strftime('%H:%M:%S')}")
        print("继续监听...")
        print()
    
    try:
        detector.start_listening(on_wake_word_detected)
        
        # 保持运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  停止检测")
        detector.stop_listening()
        print("测试结束")
    
    except Exception as e:
        print(f"\n❌ 检测过程中出错: {e}")
        detector.stop_listening()

if __name__ == "__main__":
    test_wake_word()