#!/usr/bin/python3
"""
AI集成测试脚本 - 测试AI对话管理器与主系统的集成
"""

import requests
import json
import time
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIIntegrationTester:
    """AI集成测试器"""
    
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session_id = None
    
    def test_system_status(self):
        """测试系统状态"""
        print("=== 测试系统状态 ===")
        try:
            response = requests.get(f"{self.base_url}/status")
            if response.status_code == 200:
                status = response.json()
                print(f"系统状态: {status['status']}")
                print(f"AI对话模式: {status.get('ai_conversation', False)}")
                print(f"活跃会话数: {status.get('session_stats', {}).get('active_sessions', 0)}")
                return True
            else:
                print(f"获取状态失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"测试系统状态错误: {e}")
            return False
    
    def test_ai_conversation_toggle(self):
        """测试AI对话模式切换"""
        print("\n=== 测试AI对话模式切换 ===")
        try:
            # 启动AI对话模式
            response = requests.post(f"{self.base_url}/ai_conversation")
            if response.status_code == 200:
                result = response.json()
                if result['status'] == 'success' and result['enabled']:
                    print("AI对话模式启动成功")
                    self.session_id = result.get('session_id')
                    print(f"会话ID: {self.session_id}")
                    return True
                else:
                    print(f"AI对话模式启动失败: {result.get('message', '未知错误')}")
                    return False
            else:
                print(f"请求失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"测试AI对话模式切换错误: {e}")
            return False
    
    def test_session_management(self):
        """测试会话管理"""
        print("\n=== 测试会话管理 ===")
        try:
            # 创建新会话
            response = requests.post(f"{self.base_url}/session/create")
            if response.status_code == 200:
                result = response.json()
                if result['status'] == 'success':
                    test_session_id = result['session_id']
                    print(f"创建新会话成功: {test_session_id}")
                    
                    # 获取会话信息
                    response = requests.get(f"{self.base_url}/session/{test_session_id}")
                    if response.status_code == 200:
                        session_info = response.json()
                        if session_info['status'] == 'success':
                            print(f"会话信息: {session_info['session']}")
                            return True
                    
            print("会话管理测试失败")
            return False
        except Exception as e:
            print(f"测试会话管理错误: {e}")
            return False
    
    def test_ai_chat(self):
        """测试AI对话功能"""
        print("\n=== 测试AI对话功能 ===")
        
        test_messages = [
            "你好，快快！",
            "你能前进吗？",
            "我很开心！",
            "转个圈给我看看"
        ]
        
        try:
            for message in test_messages:
                print(f"\n发送消息: {message}")
                
                data = {
                    'message': message,
                    'session_id': self.session_id
                }
                
                response = requests.post(f"{self.base_url}/ai_chat", json=data)
                
                if response.status_code == 200:
                    result = response.json()
                    if result['status'] == 'success':
                        print(f"AI回复: {result['response']}")
                        print(f"检测情感: {result['emotion']}")
                        print(f"时间戳: {result['timestamp']}")
                    else:
                        print(f"对话失败: {result.get('message', '未知错误')}")
                else:
                    print(f"请求失败: {response.status_code}")
                
                time.sleep(2)  # 避免请求过快
            
            return True
            
        except Exception as e:
            print(f"测试AI对话错误: {e}")
            return False
    
    def test_integrated_command(self):
        """测试集成命令接口"""
        print("\n=== 测试集成命令接口 ===")
        
        test_commands = [
            {'message': '你好，我想让你前进', 'type': 'conversation'},
            {'message': '转个圈', 'type': 'conversation'},
            {'message': '前进', 'type': 'command'},
            {'message': '停止', 'type': 'command'}
        ]
        
        try:
            for cmd in test_commands:
                print(f"\n测试命令: {cmd}")
                
                cmd['session_id'] = self.session_id
                response = requests.post(f"{self.base_url}/ai_integrated_command", json=cmd)
                
                if response.status_code == 200:
                    result = response.json()
                    if result['status'] == 'success':
                        print(f"执行成功: {result}")
                        if 'response' in result:
                            print(f"AI回复: {result['response']}")
                        if 'movement_executed' in result:
                            print(f"运动执行: {result['movement_executed']}")
                    else:
                        print(f"执行失败: {result.get('message', '未知错误')}")
                else:
                    print(f"请求失败: {response.status_code}")
                
                time.sleep(2)
            
            return True
            
        except Exception as e:
            print(f"测试集成命令错误: {e}")
            return False
    
    def test_emotion_and_personality(self):
        """测试情感和个性功能"""
        print("\n=== 测试情感和个性功能 ===")
        
        try:
            # 获取当前情感状态
            response = requests.get(f"{self.base_url}/ai_emotion")
            if response.status_code == 200:
                result = response.json()
                if result['status'] == 'success':
                    print(f"当前情感状态: {result['emotion']}")
                else:
                    print(f"获取情感状态失败: {result.get('message')}")
            
            # 获取个性设置
            response = requests.get(f"{self.base_url}/ai_personality")
            if response.status_code == 200:
                result = response.json()
                if result['status'] == 'success':
                    print(f"个性设置: {result['personality']}")
                else:
                    print(f"获取个性设置失败: {result.get('message')}")
            
            # 执行情感运动
            emotion_data = {
                'emotion': 'happy',
                'intensity': 0.8
            }
            response = requests.post(f"{self.base_url}/ai_execute_emotion", json=emotion_data)
            if response.status_code == 200:
                result = response.json()
                print(f"情感运动执行: {result}")
            
            return True
            
        except Exception as e:
            print(f"测试情感和个性功能错误: {e}")
            return False
    
    def test_session_history(self):
        """测试会话历史功能"""
        print("\n=== 测试会话历史功能 ===")
        
        try:
            if not self.session_id:
                print("没有活跃会话，跳过历史测试")
                return False
            
            # 获取会话历史
            response = requests.get(f"{self.base_url}/session/{self.session_id}/history")
            if response.status_code == 200:
                result = response.json()
                if result['status'] == 'success':
                    print(f"对话历史条数: {len(result['history'])}")
                    print(f"命令历史条数: {len(result['commands'])}")
                    print(f"情感状态记录: {len(result['emotions'])}")
                    
                    # 显示最近的对话
                    if result['history']:
                        print("\n最近的对话:")
                        for i, entry in enumerate(result['history'][-3:], 1):
                            print(f"{i}. 用户: {entry['user_input']}")
                            print(f"   AI: {entry['ai_response']}")
                            print(f"   情感: {entry['emotion']}")
                    
                    return True
                else:
                    print(f"获取会话历史失败: {result.get('message')}")
                    return False
            else:
                print(f"请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"测试会话历史错误: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("开始AI集成测试...")
        
        tests = [
            ("系统状态", self.test_system_status),
            ("AI对话模式切换", self.test_ai_conversation_toggle),
            ("会话管理", self.test_session_management),
            ("AI对话功能", self.test_ai_chat),
            ("集成命令接口", self.test_integrated_command),
            ("情感和个性功能", self.test_emotion_and_personality),
            ("会话历史功能", self.test_session_history)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                results[test_name] = result
                print(f"\n{test_name}: {'通过' if result else '失败'}")
            except Exception as e:
                results[test_name] = False
                print(f"\n{test_name}: 失败 - {e}")
        
        # 总结
        print("\n" + "="*50)
        print("测试结果总结:")
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✓ 通过" if result else "✗ 失败"
            print(f"  {test_name}: {status}")
        
        print(f"\n总计: {passed}/{total} 测试通过")
        
        if passed == total:
            print("🎉 所有测试通过！AI集成功能正常工作。")
        else:
            print("⚠️  部分测试失败，请检查系统配置和日志。")
        
        return passed == total

def main():
    """主函数"""
    print("AI集成测试工具")
    print("确保机器人Web控制服务正在运行 (python robot_voice_web_control.py)")
    print("按Enter键开始测试...")
    input()
    
    tester = AIIntegrationTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n测试完成！系统集成正常。")
    else:
        print("\n测试完成，但存在问题需要修复。")

if __name__ == "__main__":
    main()