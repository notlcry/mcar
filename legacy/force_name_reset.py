#!/usr/bin/env python3
"""
强制重置AI名字 - 彻底清除所有缓存和历史
"""

import sys
import os
import json
import shutil
from pathlib import Path

# 添加src目录到路径
sys.path.append('src')

def force_reset_name():
    """强制重置AI名字"""
    print("🔄 强制重置AI名字")
    print("=" * 50)
    
    # 1. 删除所有可能的数据库和缓存文件
    files_to_delete = [
        # 数据库文件
        "data/memory/memory.db",
        "src/data/ai_memory/memory.db",
        "src/test_data/memory/memory.db",
        "src/test_data/ai_integration/memory.db",
        "src/test_data/complete_system/memory.db",
        "src/test_data/persistence/memory.db",
        
        # 可能的缓存文件
        "data/memory/.cache",
        "src/data/ai_memory/.cache",
        
        # 会话文件
        "data/memory/sessions.json",
        "src/data/ai_memory/sessions.json",
    ]
    
    print("1. 清理数据库和缓存文件:")
    deleted_count = 0
    for file_path in files_to_delete:
        path = Path(file_path)
        if path.exists():
            try:
                if path.is_file():
                    path.unlink()
                else:
                    shutil.rmtree(path)
                print(f"✅ 已删除: {file_path}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ 删除失败: {file_path} - {e}")
        else:
            print(f"⚪ 不存在: {file_path}")
    
    # 2. 清理Python缓存
    print("\n2. 清理Python缓存:")
    cache_dirs = ["src/__pycache__", "__pycache__", ".pytest_cache"]
    for cache_dir in cache_dirs:
        cache_path = Path(cache_dir)
        if cache_path.exists():
            try:
                shutil.rmtree(cache_path)
                print(f"✅ 已清理: {cache_dir}")
            except Exception as e:
                print(f"❌ 清理失败: {cache_dir} - {e}")
    
    # 3. 确保所有配置文件中的名字都是"快快"
    print("\n3. 确保配置文件正确:")
    config_files = [
        "data/memory/user_config.json",
        "src/data/ai_memory/user_config.json",
        "src/ai_pet_config.json"
    ]
    
    for config_file in config_files:
        config_path = Path(config_file)
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                updated = False
                if 'personality' in config and 'name' in config['personality']:
                    old_name = config['personality']['name']
                    if old_name != '快快':
                        config['personality']['name'] = '快快'
                        updated = True
                
                if 'ai' in config and 'personality_prompt' in config['ai']:
                    old_prompt = config['ai']['personality_prompt']
                    if '圆滚滚' in old_prompt:
                        config['ai']['personality_prompt'] = old_prompt.replace('圆滚滚', '快快')
                        updated = True
                
                if updated:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config, f, ensure_ascii=False, indent=2)
                    print(f"✅ 已更新: {config_file}")
                else:
                    print(f"✅ 已确认: {config_file} (名字正确)")
                    
            except Exception as e:
                print(f"❌ 处理失败: {config_file} - {e}")
        else:
            print(f"⚪ 不存在: {config_file}")
    
    # 4. 创建一个测试脚本来验证修复
    print("\n4. 创建验证脚本:")
    test_script = """#!/usr/bin/env python3
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
"""
    
    with open("verify_name_fix.py", "w", encoding='utf-8') as f:
        f.write(test_script)
    print("✅ 已创建验证脚本: verify_name_fix.py")
    
    print("\n" + "=" * 50)
    print("🎉 强制重置完成！")
    print("\n📋 接下来的步骤:")
    print("1. 运行: python verify_name_fix.py")
    print("2. 重启你的AI程序")
    print("3. 开始新的对话，问'你叫什么名字？'")
    print("4. 如果还有问题，可能需要重启整个系统")
    
    print(f"\n📊 统计: 删除了 {deleted_count} 个文件/目录")

if __name__ == "__main__":
    confirm = input("⚠️ 这将删除所有AI记忆和缓存，确认执行？(y/N): ")
    if confirm.lower() == 'y':
        force_reset_name()
    else:
        print("操作已取消")