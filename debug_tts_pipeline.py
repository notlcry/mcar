#!/usr/bin/env python3
"""
调试TTS管道，找出杂音问题
"""

import os
import sys
import subprocess
import tempfile
import asyncio

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

def test_edge_tts_generation():
    """测试edge-tts生成"""
    print("🧪 测试edge-tts语音生成")
    print("=" * 40)
    
    try:
        import edge_tts
        
        async def generate_test_speech():
            text = "你好，这是测试语音"
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
            
            # 生成MP3文件
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                mp3_path = tmp_file.name
            
            await communicate.save(mp3_path)
            return mp3_path
        
        print("🔄 生成语音文件...")
        mp3_file = asyncio.run(generate_test_speech())
        
        print(f"✅ 生成成功: {mp3_file}")
        print(f"📊 文件大小: {os.path.getsize(mp3_file)} 字节")
        
        return mp3_file
        
    except Exception as e:
        print(f"❌ edge-tts生成失败: {e}")
        return None

def test_ffmpeg_conversion(mp3_file):
    """测试ffmpeg转换"""
    print("\n🧪 测试ffmpeg转换")
    print("=" * 40)
    
    if not mp3_file or not os.path.exists(mp3_file):
        print("❌ 没有MP3文件可转换")
        return None
    
    try:
        wav_file = mp3_file.replace('.mp3', '.wav')
        
        # 使用ffmpeg转换
        convert_cmd = [
            'ffmpeg', '-i', mp3_file,
            '-ar', '44100',  # 采样率44100Hz
            '-ac', '1',      # 单声道
            '-f', 'wav',     # WAV格式
            '-y',            # 覆盖输出文件
            wav_file
        ]
        
        print(f"🔄 转换命令: {' '.join(convert_cmd)}")
        
        result = subprocess.run(convert_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 转换成功: {wav_file}")
            print(f"📊 WAV文件大小: {os.path.getsize(wav_file)} 字节")
            
            # 显示ffmpeg输出信息
            if result.stderr:
                print("📋 ffmpeg信息:")
                for line in result.stderr.split('\n')[-10:]:  # 显示最后10行
                    if line.strip():
                        print(f"   {line}")
            
            return wav_file
        else:
            print(f"❌ 转换失败: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ ffmpeg转换异常: {e}")
        return None

def test_wav_file_info(wav_file):
    """检查WAV文件信息"""
    print("\n🧪 检查WAV文件信息")
    print("=" * 40)
    
    if not wav_file or not os.path.exists(wav_file):
        print("❌ 没有WAV文件可检查")
        return False
    
    try:
        # 使用ffprobe检查文件信息
        probe_cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', wav_file]
        
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            import json
            info = json.loads(result.stdout)
            
            print("📊 WAV文件信息:")
            if 'streams' in info and len(info['streams']) > 0:
                stream = info['streams'][0]
                print(f"   编解码器: {stream.get('codec_name', 'unknown')}")
                print(f"   采样率: {stream.get('sample_rate', 'unknown')} Hz")
                print(f"   声道数: {stream.get('channels', 'unknown')}")
                print(f"   位深度: {stream.get('bits_per_sample', 'unknown')} bit")
                print(f"   时长: {stream.get('duration', 'unknown')} 秒")
            
            if 'format' in info:
                format_info = info['format']
                print(f"   格式: {format_info.get('format_name', 'unknown')}")
                print(f"   比特率: {format_info.get('bit_rate', 'unknown')} bps")
            
            return True
        else:
            print(f"❌ 无法获取文件信息: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 检查文件信息失败: {e}")
        return False

def test_direct_aplay(wav_file):
    """测试直接aplay播放"""
    print("\n🧪 测试直接aplay播放")
    print("=" * 40)
    
    if not wav_file or not os.path.exists(wav_file):
        print("❌ 没有WAV文件可播放")
        return False
    
    try:
        print("🔊 播放WAV文件...")
        print("💡 如果听到杂音，说明转换有问题")
        print("💡 如果听到正常语音，说明转换正确")
        
        result = subprocess.run(['/usr/bin/aplay', '-D', 'hw:0,0', wav_file], 
                              capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print("✅ aplay播放完成")
            return True
        else:
            print(f"❌ aplay播放失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 播放测试失败: {e}")
        return False

def test_alternative_conversion():
    """测试替代转换方法"""
    print("\n🧪 测试替代转换方法")
    print("=" * 40)
    
    try:
        import edge_tts
        
        async def generate_wav_directly():
            text = "这是直接生成WAV格式的测试"
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
            
            # 先生成MP3
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                mp3_path = tmp_file.name
            
            await communicate.save(mp3_path)
            
            # 使用不同的ffmpeg参数转换
            wav_path = mp3_path.replace('.mp3', '_alt.wav')
            
            # 尝试不同的转换参数
            convert_cmd = [
                'ffmpeg', '-i', mp3_path,
                '-acodec', 'pcm_s16le',  # 明确指定PCM编码
                '-ar', '44100',          # 采样率
                '-ac', '1',              # 单声道
                '-y',                    # 覆盖文件
                wav_path
            ]
            
            result = subprocess.run(convert_cmd, capture_output=True, text=True)
            
            # 清理MP3文件
            os.unlink(mp3_path)
            
            if result.returncode == 0:
                return wav_path
            else:
                print(f"替代转换失败: {result.stderr}")
                return None
        
        print("🔄 使用替代参数转换...")
        wav_file = asyncio.run(generate_wav_directly())
        
        if wav_file:
            print(f"✅ 替代转换成功: {wav_file}")
            
            # 测试播放
            print("🔊 播放替代转换的文件...")
            result = subprocess.run(['/usr/bin/aplay', '-D', 'hw:0,0', wav_file], 
                                  capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                print("✅ 替代转换播放成功")
                return True
            else:
                print(f"❌ 替代转换播放失败: {result.stderr}")
        
        return False
        
    except Exception as e:
        print(f"❌ 替代转换测试失败: {e}")
        return False

def cleanup_temp_files():
    """清理临时文件"""
    try:
        import glob
        temp_files = glob.glob('/tmp/tmp*.mp3') + glob.glob('/tmp/tmp*.wav')
        for f in temp_files:
            try:
                os.unlink(f)
            except:
                pass
    except:
        pass

if __name__ == "__main__":
    print("🔍 TTS管道调试")
    print("=" * 60)
    
    try:
        # 1. 测试edge-tts生成
        mp3_file = test_edge_tts_generation()
        
        if mp3_file:
            # 2. 测试ffmpeg转换
            wav_file = test_ffmpeg_conversion(mp3_file)
            
            if wav_file:
                # 3. 检查WAV文件信息
                test_wav_file_info(wav_file)
                
                # 4. 测试播放
                test_direct_aplay(wav_file)
                
                # 清理文件
                try:
                    os.unlink(mp3_file)
                    os.unlink(wav_file)
                except:
                    pass
        
        # 5. 测试替代转换方法
        test_alternative_conversion()
        
    finally:
        # 清理临时文件
        cleanup_temp_files()
    
    print("\n" + "=" * 60)
    print("🎯 调试完成")
    print("💡 如果所有测试都是杂音，可能是:")
    print("• edge-tts生成的音频本身有问题")
    print("• ffmpeg转换参数不正确")
    print("• 硬件音频输出有问题")