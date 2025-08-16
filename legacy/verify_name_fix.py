#!/usr/bin/env python3
import sys
sys.path.append('src')

from memory_manager import MemoryManager
import json

# 测试配置
memory_manager = MemoryManager(data_dir="data/memory")
config = memory_manager.load_user_config()
print(f"当前配置中的名字: {config.get('personality', {}).get('name', '未设置')}")

# 强制保存正确的名字
config['personality']['name'] = '快快'
memory_manager.save_user_config(config)
print("已强制设置名字为: 快快")