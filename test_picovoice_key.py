#!/usr/bin/env python3
"""
测试Picovoice访问密钥
"""

import os
import sys

# 加载环境变量
def load_env():
    try:
        with open('.ai_pet_env', 'r') as f:
            for line in f:
                if line.startswith('export ') and '=' in line:
                    line = line.replace('export ', '').strip()
                    key, value = line.split('=', 1)
                    value = value.strip('"')
                    os.environ[key] = value
    except:
        pass

load_env()

def test_picovoice_key():
    """测试Picovoice访问密钥"""
    print("🔑 测试Picovoice访问密钥")
    print("=" * 40)
    
    # 检查环境变量
    access_key = os.getenv('PICOVOICE_ACCESS_KEY')
    
    if not access_key:
        print("❌ PICOVOICE_ACCESS_KEY 未设置")
        return False
    
    print(f"✅ 访问密钥已设置: {access_key[:20]}...")
    
    # 检查密钥格式
    if access_key == 'your_picovoice_access_key_here':
        print("❌ 访问密钥是默认值，需要替换为真实密钥")
        return False
    
    print("✅ 访问密钥格式正确")
    
    # 检查自定义唤醒词文件
    wake_words_paths = [
        'wake_words',
        '../wake_words'
    ]
    
    found_files = []
    for path in wake_words_paths:
        if os.path.exists(path):
            ppn_files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.ppn')]
            if ppn_files:
                found_files.extend(ppn_files)
                print(f"✅ 在 {path} 找到 {len(ppn_files)} 个唤醒词文件:")
                for f in ppn_files:
                    print(f"   - {f}")
    
    if not found_files:
        print("❌ 未找到自定义唤醒词文件 (.ppn)")
        return False
    
    # 尝试初始化Porcupine
    try:
        import pvporcupine
        
        print(f"\n🧪 测试Porcupine初始化...")
        
        porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=found_files[:1]  # 只测试第一个文件
        )
        
        print("✅ Porcupine初始化成功！")
        print(f"   采样率: {porcupine.sample_rate}")
        print(f"   帧长度: {porcupine.frame_length}")
        
        porcupine.delete()
        return True
        
    except Exception as e:
        print(f"❌ Porcupine初始化失败: {e}")
        return False

if __name__ == "__main__":
    if test_picovoice_key():
        print("\n🎉 Picovoice配置正常！")
        print("💡 警告可能是路径问题，让我们修复代码中的路径")
    else:
        print("\n❌ Picovoice配置有问题")