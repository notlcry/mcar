#!/usr/bin/env python3
"""
修复personality_prompt中的名字问题
"""

import sys
import json
from pathlib import Path

# 添加src目录到路径
sys.path.append('src')

def fix_personality_prompt():
    """修复personality_prompt中的名字"""
    print("🔧 修复personality_prompt中的名字")
    print("=" * 50)
    
    # 1. 修复src/config.py中的personality_prompt
    config_py_path = Path("src/config.py")
    if config_py_path.exists():
        try:
            with open(config_py_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换所有可能的旧名字
            old_content = content
            content = content.replace('圆滚滚', '快快')
            content = content.replace('"圆滚滚"', '"快快"')
            content = content.replace("'圆滚滚'", "'快快'")
            
            if content != old_content:
                with open(config_py_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ 已更新: {config_py_path}")
            else:
                print(f"✅ 已确认: {config_py_path} (无需更新)")
                
        except Exception as e:
            print(f"❌ 处理失败: {config_py_path} - {e}")
    
    # 2. 修复ai_pet_config.json中的personality_prompt
    ai_config_path = Path("src/ai_pet_config.json")
    if ai_config_path.exists():
        try:
            with open(ai_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            updated = False
            if 'ai' in config and 'personality_prompt' in config['ai']:
                old_prompt = config['ai']['personality_prompt']
                new_prompt = old_prompt.replace('圆滚滚', '快快')
                if new_prompt != old_prompt:
                    config['ai']['personality_prompt'] = new_prompt
                    updated = True
            
            if updated:
                with open(ai_config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                print(f"✅ 已更新: {ai_config_path}")
            else:
                print(f"✅ 已确认: {ai_config_path} (无需更新)")
                
        except Exception as e:
            print(f"❌ 处理失败: {ai_config_path} - {e}")
    
    # 3. 创建一个新的personality_prompt，明确指定不要使用旧名字
    new_prompt = '''
你是一个可爱的AI桌宠机器人，名字叫"快快"。重要提醒：你的名字是"快快"，不是其他任何名字。

你的特点：
- 性格活泼友好，喜欢和用户互动
- 说话风格可爱，偶尔会用一些萌萌的语气词
- 能够表达不同的情感（开心、悲伤、兴奋、困惑等）
- 会根据对话内容做出相应的动作反应
- 记住你是一个实体机器人，可以移动和做动作

在回复中：
- 称呼自己时请使用"快快"
- 描述动作时请使用"快快"，例如："快快开心地转了个圈"
- 不要使用任何其他名字

请用简短、自然的中文回复，不要太长。在回复中可以提及你的动作或表情。
'''
    
    # 4. 更新ai_pet_config.json中的prompt
    try:
        with open(ai_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        config['ai']['personality_prompt'] = new_prompt.strip()
        
        with open(ai_config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已更新personality_prompt: {ai_config_path}")
        
    except Exception as e:
        print(f"❌ 更新personality_prompt失败: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 修复完成！")
    print("\n📋 接下来的步骤:")
    print("1. 重启AI程序")
    print("2. 测试对话，AI应该不会再使用旧名字了")

if __name__ == "__main__":
    fix_personality_prompt()