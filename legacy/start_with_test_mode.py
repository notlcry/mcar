#!/usr/bin/env python3
"""
使用测试模式启动主程序
避免音频流冲突，但保持AI对话功能
"""

import os
import sys
import subprocess

def start_main_program_with_test_mode():
    """使用测试模式启动主程序"""
    print("🚀 使用测试模式启动AI语音对话系统")
    print("=" * 50)
    
    # 设置环境变量启用测试模式
    env = os.environ.copy()
    env['VOICE_TEST_MODE'] = 'true'
    
    print("🔧 配置:")
    print("   - 测试模式: 启用")
    print("   - 音频流冲突: 避免")
    print("   - AI对话功能: 完整")
    print("   - 语音输入/输出: 禁用")
    
    print("\n💡 在测试模式下:")
    print("   ✅ 可以通过Web界面进行AI对话")
    print("   ✅ 系统稳定运行，无段错误")
    print("   ❌ 无法使用语音唤醒和语音输入")
    
    print("\n🌐 启动Web服务器...")
    
    try:
        # 切换到src目录并启动主程序
        os.chdir('src')
        result = subprocess.run(['python3', 'robot_voice_web_control.py'], 
                              env=env)
        return result.returncode == 0
        
    except KeyboardInterrupt:
        print("\n🛑 用户终止程序")
        return True
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        return False

def start_normal_mode():
    """尝试正常模式启动"""
    print("🎙️ 尝试正常模式启动")
    print("=" * 50)
    
    print("⚠️ 警告: 正常模式可能出现音频流段错误")
    
    choice = input("是否继续？(y/n): ").strip().lower()
    if choice != 'y':
        print("已取消")
        return False
    
    try:
        os.chdir('src')
        result = subprocess.run(['python3', 'robot_voice_web_control.py'])
        return result.returncode == 0
        
    except KeyboardInterrupt:
        print("\n🛑 用户终止程序")
        return True
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        return False

def show_usage_guide():
    """显示使用指南"""
    print("\n📋 使用指南:")
    print("=" * 30)
    
    print("🌐 Web界面访问:")
    print("   http://树莓派IP:5000")
    
    print("\n💬 AI对话使用:")
    print("   1. 点击 'AI对话模式' 开关")
    print("   2. 使用文本输入进行AI对话")
    print("   3. 或通过API接口调用")
    
    print("\n🔧 测试模式说明:")
    print("   - 避免音频流冲突段错误")
    print("   - 保持所有AI对话功能")
    print("   - 可用于开发和测试")
    
    print("\n🚀 完整功能启用:")
    print("   - 解决音频设备问题后")
    print("   - 使用正常模式启动")

def main():
    """主函数"""
    print("🤖 AI语音对话系统启动器")
    print("=" * 60)
    
    print("选择启动模式:")
    print("1. 测试模式 (推荐) - 稳定但无语音输入")
    print("2. 正常模式 - 完整功能但可能段错误")
    print("3. 显示使用指南")
    
    while True:
        choice = input("\n请选择 (1/2/3): ").strip()
        
        if choice == '1':
            success = start_main_program_with_test_mode()
            break
        elif choice == '2':
            success = start_normal_mode()
            break
        elif choice == '3':
            show_usage_guide()
            continue
        else:
            print("无效选择，请重新输入")
            continue
    
    if choice in ['1', '2']:
        if success:
            print("\n✅ 程序正常结束")
        else:
            print("\n❌ 程序异常结束")

if __name__ == "__main__":
    main()