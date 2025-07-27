#!/usr/bin/env python3
"""
创建简化的ALSA配置
"""

import os
import subprocess

def detect_audio_cards():
    """检测音频卡"""
    print("🔍 检测音频卡...")
    
    try:
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            print("📱 可用的音频设备:")
            print(result.stdout)
            
            # 解析输出找到设备
            lines = result.stdout.split('\n')
            cards = []
            
            for line in lines:
                if 'card' in line and ':' in line:
                    # 解析类似 "card 0: bcm2835_headpho [bcm2835 Headphones], device 0: bcm2835 Headphones [bcm2835 Headphones]"
                    parts = line.split(':')
                    if len(parts) >= 2:
                        card_part = parts[0].strip()
                        if 'card' in card_part:
                            card_num = card_part.split()[-1]
                            device_name = parts[1].split(',')[0].strip()
                            cards.append((card_num, device_name))
            
            return cards
        else:
            print("❌ 无法获取音频设备列表")
            return []
            
    except FileNotFoundError:
        print("❌ aplay命令不可用")
        return []

def create_working_asoundrc():
    """创建可工作的ALSA配置"""
    print("\n🔧 创建简化的ALSA配置...")
    
    # 检测音频卡
    cards = detect_audio_cards()
    
    if not cards:
        print("❌ 未检测到音频设备")
        return False
    
    print(f"✅ 检测到 {len(cards)} 个音频设备")
    
    # 选择第一个设备作为默认播放设备
    play_card = cards[0][0]
    print(f"🔊 使用卡 {play_card} 作为播放设备")
    
    # 创建配置
    config = f"""# 简化的ALSA配置 - 自动生成
# 播放设备
pcm.!default {{
    type plug
    slave {{
        pcm "hw:{play_card},0"
        rate 44100
        channels 2
        format S16_LE
    }}
}}

# 控制设备
ctl.!default {{
    type hw
    card {play_card}
}}

# 录音设备 (如果有USB麦克风)
pcm.mic {{
    type plug
    slave {{
        pcm "hw:1,0"
        rate 16000
        channels 1
        format S16_LE
    }}
}}

# 备用单声道播放
pcm.mono {{
    type plug
    slave {{
        pcm "hw:{play_card},0"
        rate 22050
        channels 1
        format S16_LE
    }}
}}
"""
    
    try:
        with open('.asoundrc', 'w') as f:
            f.write(config)
        
        print("✅ ALSA配置已更新")
        print(f"📄 配置文件: .asoundrc")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建配置失败: {e}")
        return False

if __name__ == "__main__":
    print("🔧 ALSA配置自动修复工具")
    print("=" * 40)
    
    if create_working_asoundrc():
        print("\n🎉 ALSA配置修复完成！")
        print("💡 现在可以测试音频输出:")
        print("   python3 test_audio_output_fixed.py")
    else:
        print("\n❌ ALSA配置修复失败")