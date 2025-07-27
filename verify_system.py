#!/usr/bin/env python3
# 验证AI桌宠系统核心功能

import requests
import json
import time

def test_web_interface():
    """测试Web界面"""
    try:
        response = requests.get('http://localhost:5000/status', timeout=5)
        if response.status_code == 200:
            print("✅ Web界面正常")
            return True
    except Exception as e:
        print(f"❌ Web界面异常: {e}")
        return False

def test_robot_control():
    """测试机器人控制"""
    try:
        # 测试停止命令
        response = requests.post('http://localhost:5000/control', 
                               json={'command': 'stop', 'speed': 50, 'duration': 0}, 
                               timeout=5)
        if response.status_code == 200:
            print("✅ 机器人控制正常")
            return True
    except Exception as e:
        print(f"❌ 机器人控制异常: {e}")
        return False

def test_ai_conversation():
    """测试AI对话"""
    try:
        # 启动AI对话
        response = requests.post('http://localhost:5000/ai_conversation', timeout=5)
        if response.status_code == 200:
            data = response.json()
            session_id = data.get('session_id')
            
            if session_id:
                # 发送测试消息
                response = requests.post('http://localhost:5000/ai_chat', 
                                       json={'message': '你好，请简单回复'}, 
                                       timeout=15)
                if response.status_code == 200:
                    reply_data = response.json()
                    if reply_data.get('reply'):
                        print("✅ AI对话功能正常")
                        print(f"   AI回复: {reply_data['reply'][:50]}...")
                        return True
    except Exception as e:
        print(f"❌ AI对话异常: {e}")
        return False

def main():
    print("🔍 验证AI桌宠系统核心功能...")
    print("=" * 50)
    
    # 等待系统稳定
    time.sleep(2)
    
    web_ok = test_web_interface()
    robot_ok = test_robot_control()
    ai_ok = test_ai_conversation()
    
    print("=" * 50)
    print("📊 测试结果:")
    print(f"   Web界面: {'✅' if web_ok else '❌'}")
    print(f"   机器人控制: {'✅' if robot_ok else '❌'}")
    print(f"   AI对话: {'✅' if ai_ok else '❌'}")
    
    if web_ok and robot_ok:
        print("\n🎉 核心功能正常！系统可以使用")
        print("\n💡 使用建议:")
        print("   • 通过Web界面控制机器人")
        print("   • 使用AI对话功能")
        print("   • 语音功能可能受限，但不影响主要功能")
        print(f"\n🌐 访问地址: http://你的树莓派IP:5000")
        return True
    else:
        print("\n❌ 部分核心功能异常")
        return False

if __name__ == "__main__":
    main()