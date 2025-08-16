#!/usr/bin/env python3
# 修复Gemini初始化问题并添加唤醒日志

import os
import sys

def fix_gemini_initialization():
    """修复Gemini初始化问题"""
    
    print("🔧 修复Gemini初始化问题...")
    
    # 读取AI对话管理器文件
    ai_conversation_file = 'src/ai_conversation.py'
    
    if not os.path.exists(ai_conversation_file):
        print(f"❌ 文件不存在: {ai_conversation_file}")
        return False
    
    with open(ai_conversation_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 备份原文件
    backup_file = f"{ai_conversation_file}.backup.{int(time.time())}"
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ 已备份原文件: {backup_file}")
    
    # 修复初始化问题
    fixes = [
        # 确保从环境变量加载API密钥
        (
            "self.api_key = self.ai_config.gemini_api_key",
            """self.api_key = self.ai_config.gemini_api_key
        
        # 如果配置中没有API密钥，尝试从环境变量加载
        if not self.api_key:
            self.api_key = os.getenv('GEMINI_API_KEY')
            if self.api_key:
                logger.info("从环境变量加载Gemini API密钥")
            else:
                logger.warning("未找到Gemini API密钥")"""
        ),
        
        # 添加更详细的初始化日志
        (
            'logger.info("Gemini API初始化成功")',
            '''logger.info(f"Gemini API初始化成功，使用模型: {self.ai_config.model_name}")
                logger.info(f"API密钥: {self.api_key[:20]}..." if self.api_key else "API密钥: 未设置")'''
        )
    ]
    
    for old_text, new_text in fixes:
        if old_text in content:
            content = content.replace(old_text, new_text)
            print(f"✅ 已修复: {old_text[:50]}...")
    
    # 写回文件
    with open(ai_conversation_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Gemini初始化修复完成")
    return True

def add_wake_word_logs():
    """添加唤醒词检测日志"""
    
    print("📝 添加唤醒词检测日志...")
    
    # 查找唤醒词检测相关文件
    files_to_update = [
        'src/enhanced_voice_control.py',
        'src/wake_word_detector.py'
    ]
    
    for file_path in files_to_update:
        if not os.path.exists(file_path):
            print(f"⚠️  文件不存在: {file_path}")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 备份文件
        backup_file = f"{file_path}.backup.{int(time.time())}"
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 添加唤醒日志
        wake_word_logs = [
            # 在唤醒词检测回调中添加日志
            (
                'def _on_wake_word_detected(self, keyword_index):',
                '''def _on_wake_word_detected(self, keyword_index):
        """唤醒词检测回调"""
        logger.info(f"🎤 检测到唤醒词！索引: {keyword_index}")
        logger.info("🤖 AI桌宠已唤醒，准备开始对话...")'''
            ),
            
            # 添加唤醒成功的详细日志
            (
                'self.wake_word_detected = True',
                '''self.wake_word_detected = True
        logger.info("✅ 唤醒状态已设置，开始语音交互模式")'''
            ),
            
            # 添加录音开始日志
            (
                'def start_voice_recording(self):',
                '''def start_voice_recording(self):
        """开始语音录音"""
        logger.info("🎙️  开始录音，请说话...")'''
            )
        ]
        
        updated = False
        for old_text, new_text in wake_word_logs:
            if old_text in content and new_text not in content:
                content = content.replace(old_text, new_text)
                updated = True
                print(f"✅ 已添加日志到: {file_path}")
        
        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    print("✅ 唤醒词日志添加完成")

def create_debug_test_script():
    """创建调试测试脚本"""
    
    print("🧪 创建调试测试脚本...")
    
    debug_script = '''#!/usr/bin/env python3
# AI桌宠调试测试脚本

import os
import sys
import time

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
sys.path.insert(0, 'src')

def test_gemini_initialization():
    """测试Gemini初始化"""
    print("🤖 测试Gemini初始化...")
    
    try:
        from config import get_ai_config
        from ai_conversation import AIConversationManager
        
        # 获取配置
        ai_config = get_ai_config()
        print(f"   配置模型: {ai_config.model_name}")
        print(f"   配置API密钥: {'已设置' if ai_config.gemini_api_key else '未设置'}")
        print(f"   环境变量API密钥: {'已设置' if os.getenv('GEMINI_API_KEY') else '未设置'}")
        
        # 创建AI对话管理器
        ai_manager = AIConversationManager()
        
        if ai_manager.model:
            print("✅ Gemini初始化成功")
            
            # 测试简单对话
            response = ai_manager.model.generate_content("请简单回复'测试成功'")
            print(f"   测试回复: {response.text}")
            
        else:
            print("❌ Gemini初始化失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_wake_word_detection():
    """测试唤醒词检测"""
    print("🎤 测试唤醒词检测...")
    
    try:
        import pvporcupine
        
        access_key = os.getenv('PICOVOICE_ACCESS_KEY')
        if not access_key:
            print("❌ PICOVOICE_ACCESS_KEY未设置")
            return
        
        # 测试自定义唤醒词
        if os.path.exists('src/wake_words/kk_zh_raspberry-pi_v3_0_0.ppn'):
            print("   测试自定义唤醒词 'kk'...")
            porcupine = pvporcupine.create(
                access_key=access_key,
                model_path='src/wake_words/porcupine_params_zh.pv',
                keyword_paths=['src/wake_words/kk_zh_raspberry-pi_v3_0_0.ppn']
            )
            print("✅ 自定义唤醒词 'kk' 初始化成功")
            porcupine.delete()
        else:
            print("   测试内置唤醒词 'picovoice'...")
            porcupine = pvporcupine.create(
                access_key=access_key,
                keywords=['picovoice']
            )
            print("✅ 内置唤醒词 'picovoice' 初始化成功")
            porcupine.delete()
            
    except Exception as e:
        print(f"❌ 唤醒词测试失败: {e}")

if __name__ == "__main__":
    print("====================================")
    print("🔍 AI桌宠调试测试")
    print("====================================")
    
    test_gemini_initialization()
    print()
    test_wake_word_detection()
    
    print("\\n====================================")
    print("✅ 调试测试完成")
    print("====================================")
'''
    
    with open('debug_ai_pet.py', 'w', encoding='utf-8') as f:
        f.write(debug_script)
    
    print("✅ 调试测试脚本已创建: debug_ai_pet.py")

if __name__ == "__main__":
    import time
    
    print("====================================")
    print("🔧 修复Gemini初始化和添加日志")
    print("====================================")
    
    try:
        fix_gemini_initialization()
        print()
        add_wake_word_logs()
        print()
        create_debug_test_script()
        
        print("\\n✅ 所有修复完成！")
        print("\\n🧪 测试修复结果:")
        print("   python3 debug_ai_pet.py")
        print("\\n🚀 重新启动系统:")
        print("   cd src && python3 robot_voice_web_control.py")
        
    except Exception as e:
        print(f"❌ 修复过程中出错: {e}")
        import traceback
        traceback.print_exc()