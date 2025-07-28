#!/usr/bin/env python3
"""
清空AI对话系统记忆
用于测试时重置所有对话历史和用户数据
"""

import os
import sys
import json
import sqlite3
import shutil
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_memory_database(db_path):
    """清空记忆数据库"""
    if not os.path.exists(db_path):
        logger.info(f"数据库文件不存在: {db_path}")
        return True
    
    try:
        logger.info(f"清空数据库: {db_path}")
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 获取所有表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            # 清空所有表
            for table in tables:
                table_name = table[0]
                cursor.execute(f"DELETE FROM {table_name}")
                logger.info(f"已清空表: {table_name}")
            
            conn.commit()
        
        logger.info(f"✅ 数据库清空完成: {db_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 清空数据库失败: {e}")
        return False

def reset_user_config(config_path):
    """重置用户配置文件"""
    try:
        # 默认配置
        default_config = {
            "personality": {
                "name": "快快",
                "friendliness": 0.8,
                "energy_level": 0.7,
                "curiosity": 0.6,
                "playfulness": 0.9
            },
            "voice_preferences": {
                "voice": "zh-CN-XiaoxiaoNeural",
                "rate": "+0%",
                "volume": "+0%"
            },
            "behavior_preferences": {
                "movement_style": "bouncy",
                "response_style": "friendly",
                "interaction_frequency": "normal"
            }
        }
        
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # 写入默认配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 用户配置已重置: {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 重置用户配置失败: {e}")
        return False

def clear_cache_directory(cache_dir):
    """清空缓存目录"""
    if not os.path.exists(cache_dir):
        logger.info(f"缓存目录不存在: {cache_dir}")
        return True
    
    try:
        shutil.rmtree(cache_dir)
        logger.info(f"✅ 缓存目录已清空: {cache_dir}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 清空缓存目录失败: {e}")
        return False

def clear_all_memory():
    """清空所有记忆数据"""
    print("🧠 AI对话系统记忆清理工具")
    print("=" * 50)
    
    base_dir = Path(__file__).parent
    src_dir = base_dir / "src"
    
    success_count = 0
    total_count = 0
    
    # 1. 清空主数据库
    print("\n📊 清空主数据库...")
    db_paths = [
        src_dir / "data" / "ai_memory" / "memory.db",
        base_dir / "data" / "memory" / "memory.db"
    ]
    
    for db_path in db_paths:
        total_count += 1
        if clear_memory_database(str(db_path)):
            success_count += 1
    
    # 2. 清空测试数据库
    print("\n📊 清空测试数据库...")
    test_db_paths = [
        src_dir / "test_data" / "memory" / "memory.db",
        src_dir / "test_data" / "ai_integration" / "memory.db",
        src_dir / "test_data" / "complete_system" / "memory.db",
        src_dir / "test_data" / "persistence" / "memory.db",
        src_dir / "test_data" / "performance" / "memory.db"
    ]
    
    for db_path in test_db_paths:
        total_count += 1
        if clear_memory_database(str(db_path)):
            success_count += 1
    
    # 3. 重置用户配置
    print("\n⚙️ 重置用户配置...")
    config_paths = [
        src_dir / "data" / "ai_memory" / "user_config.json",
        base_dir / "data" / "memory" / "user_config.json"
    ]
    
    for config_path in config_paths:
        total_count += 1
        if reset_user_config(str(config_path)):
            success_count += 1
    
    # 4. 重置测试配置
    print("\n⚙️ 重置测试配置...")
    test_config_paths = [
        src_dir / "test_data" / "memory" / "user_config.json",
        src_dir / "test_data" / "ai_integration" / "user_config.json",
        src_dir / "test_data" / "complete_system" / "user_config.json",
        src_dir / "test_data" / "persistence" / "user_config.json"
    ]
    
    for config_path in test_config_paths:
        total_count += 1
        if reset_user_config(str(config_path)):
            success_count += 1
    
    # 5. 清空缓存目录（如果存在）
    print("\n🗂️ 清空缓存目录...")
    cache_dirs = [
        src_dir / "cache",
        src_dir / "temp",
        base_dir / "cache"
    ]
    
    for cache_dir in cache_dirs:
        total_count += 1
        if clear_cache_directory(str(cache_dir)):
            success_count += 1
    
    # 6. 删除临时文件
    print("\n🗑️ 清理临时文件...")
    temp_patterns = [
        "*.tmp",
        "*.temp",
        "*.log",
        "*.pid"
    ]
    
    temp_files_deleted = 0
    for pattern in temp_patterns:
        for temp_file in base_dir.rglob(pattern):
            try:
                temp_file.unlink()
                temp_files_deleted += 1
            except:
                pass
    
    if temp_files_deleted > 0:
        logger.info(f"✅ 已删除 {temp_files_deleted} 个临时文件")
    
    # 结果统计
    print("\n📋 清理结果统计:")
    print(f"   成功项: {success_count}/{total_count}")
    print(f"   成功率: {(success_count/total_count*100):.1f}%")
    
    if success_count == total_count:
        print("\n🎉 记忆清理完成！")
        print("💡 提示:")
        print("   - 所有对话历史已清空")
        print("   - 用户配置已重置为默认值")
        print("   - 系统缓存已清理")
        print("   - 可以重新开始测试AI对话系统")
        return True
    else:
        print(f"\n⚠️ 部分清理失败 ({total_count-success_count} 项)")
        print("请检查错误日志并手动处理失败的项目")
        return False

def clear_specific_session(session_id=None):
    """清空特定会话的记忆"""
    if not session_id:
        print("请提供会话ID")
        return False
    
    print(f"🎯 清空会话记忆: {session_id}")
    
    base_dir = Path(__file__).parent
    src_dir = base_dir / "src"
    
    db_paths = [
        src_dir / "data" / "ai_memory" / "memory.db",
        base_dir / "data" / "memory" / "memory.db"
    ]
    
    success = True
    
    for db_path in db_paths:
        if not os.path.exists(db_path):
            continue
            
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                
                # 删除特定会话的对话记录
                cursor.execute('DELETE FROM conversations WHERE session_id = ?', (session_id,))
                deleted_conversations = cursor.rowcount
                
                # 删除特定会话的上下文
                cursor.execute('DELETE FROM session_contexts WHERE session_id = ?', (session_id,))
                deleted_contexts = cursor.rowcount
                
                conn.commit()
                
                logger.info(f"会话 {session_id}: 删除 {deleted_conversations} 条对话, {deleted_contexts} 条上下文")
                
        except Exception as e:
            logger.error(f"清空会话记忆失败: {e}")
            success = False
    
    if success:
        print(f"✅ 会话 {session_id} 的记忆已清空")
    else:
        print(f"❌ 清空会话 {session_id} 记忆时出现错误")
    
    return success

def show_memory_status():
    """显示记忆状态"""
    print("📊 记忆状态检查")
    print("=" * 30)
    
    base_dir = Path(__file__).parent
    src_dir = base_dir / "src"
    
    # 检查数据库
    db_paths = [
        ("主数据库", src_dir / "data" / "ai_memory" / "memory.db"),
        ("备用数据库", base_dir / "data" / "memory" / "memory.db")
    ]
    
    for name, db_path in db_paths:
        if os.path.exists(db_path):
            try:
                with sqlite3.connect(str(db_path)) as conn:
                    cursor = conn.cursor()
                    
                    # 统计对话数量
                    cursor.execute('SELECT COUNT(*) FROM conversations')
                    conv_count = cursor.fetchone()[0]
                    
                    # 统计会话数量
                    cursor.execute('SELECT COUNT(*) FROM session_contexts')
                    session_count = cursor.fetchone()[0]
                    
                    print(f"   {name}: {conv_count} 条对话, {session_count} 个会话")
                    
            except Exception as e:
                print(f"   {name}: 读取失败 - {e}")
        else:
            print(f"   {name}: 不存在")
    
    # 检查配置文件
    config_paths = [
        ("主配置", src_dir / "data" / "ai_memory" / "user_config.json"),
        ("备用配置", base_dir / "data" / "memory" / "user_config.json")
    ]
    
    for name, config_path in config_paths:
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    personality_name = config.get('personality', {}).get('name', '未知')
                    print(f"   {name}: 个性名称={personality_name}")
            except Exception as e:
                print(f"   {name}: 读取失败 - {e}")
        else:
            print(f"   {name}: 不存在")

def main():
    """主函数"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "status":
            show_memory_status()
        elif command == "session" and len(sys.argv) > 2:
            clear_specific_session(sys.argv[2])
        elif command == "all":
            clear_all_memory()
        else:
            print("用法:")
            print("  python3 clear_memory.py all        # 清空所有记忆")
            print("  python3 clear_memory.py status     # 显示记忆状态")
            print("  python3 clear_memory.py session ID # 清空特定会话")
    else:
        # 交互式模式
        print("🧠 AI对话系统记忆管理")
        print("选择操作:")
        print("1. 清空所有记忆（测试用）")
        print("2. 显示记忆状态")
        print("3. 清空特定会话")
        print("4. 退出")
        
        while True:
            choice = input("\n请选择 (1-4): ").strip()
            
            if choice == "1":
                confirm = input("⚠️ 确认清空所有记忆？这将删除所有对话历史！(y/N): ").strip().lower()
                if confirm == 'y':
                    clear_all_memory()
                else:
                    print("操作已取消")
                break
            elif choice == "2":
                show_memory_status()
                break
            elif choice == "3":
                session_id = input("请输入会话ID: ").strip()
                if session_id:
                    clear_specific_session(session_id)
                else:
                    print("无效的会话ID")
                break
            elif choice == "4":
                print("退出")
                break
            else:
                print("无效选择，请重新输入")

if __name__ == "__main__":
    main()