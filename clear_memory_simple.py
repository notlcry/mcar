#!/usr/bin/env python3
"""
简单清空AI记忆 - 直接删除数据库文件
"""

import os
from pathlib import Path

def clear_memory_simple():
    """简单清空记忆 - 删除数据库文件"""
    print("🧠 简单清空AI记忆")
    print("=" * 30)
    
    base_dir = Path(__file__).parent
    
    # 主要数据库文件路径
    db_files = [
        base_dir / "src" / "data" / "ai_memory" / "memory.db",
        base_dir / "data" / "memory" / "memory.db",
        # 测试数据库
        base_dir / "src" / "test_data" / "memory" / "memory.db",
        base_dir / "src" / "test_data" / "ai_integration" / "memory.db",
        base_dir / "src" / "test_data" / "complete_system" / "memory.db",
        base_dir / "src" / "test_data" / "persistence" / "memory.db",
    ]
    
    deleted_count = 0
    total_count = 0
    
    for db_file in db_files:
        total_count += 1
        if db_file.exists():
            try:
                db_file.unlink()
                print(f"✅ 已删除: {db_file}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ 删除失败: {db_file} - {e}")
        else:
            print(f"⚪ 不存在: {db_file}")
    
    print(f"\n📊 结果: 删除了 {deleted_count}/{total_count} 个数据库文件")
    
    if deleted_count > 0:
        print("\n🎉 记忆清空完成！")
        print("💡 下次启动时会自动创建新的空数据库")
    else:
        print("\n💡 没有找到需要删除的数据库文件")

if __name__ == "__main__":
    confirm = input("⚠️ 确认删除所有记忆数据库文件？(y/N): ")
    if confirm.lower() == 'y':
        clear_memory_simple()
    else:
        print("操作已取消")