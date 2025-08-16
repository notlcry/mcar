#!/usr/bin/python3
"""
双TTS系统测试 - 测试edge-tts和Azure TTS的集成
"""

import asyncio
import tempfile
import os
import logging
from enhanced_voice_control import EnhancedVoiceController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_dual_tts():
    """测试双TTS系统"""
    print("🎵 双TTS系统测试开始...")
    
    try:
        # 创建增强语音控制器（测试模式）
        controller = EnhancedVoiceController(test_mode=True)
        
        print("✅ 语音控制器初始化成功")
        
        # 测试文本
        test_text = "双TTS系统测试，我是快快机器人，现在Azure TTS为主要方案"
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # 调用异步语音生成（会自动尝试Azure TTS，失败时使用edge-tts）
            success = await controller._async_generate_speech(test_text, tmp_path)
            
            if success:
                # 检查文件
                file_size = os.path.getsize(tmp_path)
                print(f"✅ TTS生成成功，文件大小: {file_size} 字节")
                
                if file_size > 0:
                    print("🎵 文件生成正常")
                    return True
                else:
                    print("❌ 生成的文件为空")
                    return False
            else:
                print("❌ TTS生成失败")
                return False
                
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("🤖 MCAR双TTS系统测试")
    print("📋 Azure TTS (主要) + edge-tts (备选)")
    print("=" * 40)
    
    if await test_dual_tts():
        print("\n✅ 双TTS系统测试通过")
    else:
        print("\n❌ 双TTS系统测试失败")

if __name__ == "__main__":
    asyncio.run(main())