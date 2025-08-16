#!/usr/bin/python3
"""
Azure Speech TTS实现 - 使用REST API
作为edge-tts的备选方案
"""

import requests
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

class AzureTTS:
    """Azure Text-to-Speech服务"""
    
    def __init__(self, endpoint, api_key, region, voice="zh-CN-YunyangNeural", 
                 rate="medium", output_format="audio-24khz-48kbitrate-mono-mp3"):
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.region = region
        self.voice = voice
        self.rate = rate
        self.output_format = output_format
        
        # 构建完整的TTS endpoint
        self.tts_url = f"{self.endpoint}/cognitiveservices/v1"
        
    def _build_ssml(self, text):
        """构建SSML格式的文本"""
        ssml = f"""<speak version='1.0' xml:lang='zh-CN'>
            <voice xml:lang='zh-CN' name='{self.voice}'>
                <prosody rate='{self.rate}'>
                    {text}
                </prosody>
            </voice>
        </speak>"""
        return ssml
    
    def synthesize_to_file(self, text, output_path):
        """将文本合成为语音文件"""
        try:
            headers = {
                'Ocp-Apim-Subscription-Key': self.api_key,
                'Content-Type': 'application/ssml+xml',
                'X-Microsoft-OutputFormat': self.output_format,
                'User-Agent': 'MCAR-Robot-TTS'
            }
            
            ssml = self._build_ssml(text)
            
            logger.debug(f"发送Azure TTS请求: {self.tts_url}")
            response = requests.post(
                self.tts_url,
                headers=headers,
                data=ssml.encode('utf-8'),
                timeout=30
            )
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Azure TTS成功生成语音: {output_path}")
                return True
            else:
                logger.error(f"Azure TTS请求失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Azure TTS异常: {e}")
            return False

def test_azure_tts():
    """测试Azure TTS功能"""
    print("🗣️ 测试Azure TTS...")
    
    # 从环境变量获取Azure配置
    endpoint = os.getenv("AZURE_TTS_ENDPOINT", "https://eastus.tts.speech.microsoft.com/")
    api_key = os.getenv("AZURE_TTS_API_KEY")
    region = os.getenv("AZURE_TTS_REGION", "eastus")
    
    if not api_key:
        print("❌ 请设置AZURE_TTS_API_KEY环境变量")
        return
    
    # Azure配置
    config = {
        "endpoint": endpoint,
        "api_key": api_key,
        "region": region,
        "voice": "zh-CN-YunyangNeural",
        "rate": "medium",
        "output_format": "audio-24khz-48kbitrate-mono-mp3"
    }
    
    tts = AzureTTS(**config)
    
    # 测试文本
    text = "你好，我是快快，这是Azure语音合成测试"
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
        output_path = tmp_file.name
    
    try:
        if tts.synthesize_to_file(text, output_path):
            print("✅ Azure TTS生成成功")
            
            # 检查文件大小
            file_size = os.path.getsize(output_path)
            print(f"📁 文件大小: {file_size} 字节")
            
            if file_size > 0:
                # 播放测试
                import subprocess
                wav_path = output_path.replace(".mp3", ".wav")
                
                # 转换为WAV
                try:
                    result = subprocess.run(["/usr/bin/ffmpeg", "-i", output_path, "-y", wav_path], 
                                          capture_output=True)
                    
                    if result.returncode == 0:
                        # 播放
                        subprocess.run(["/usr/bin/aplay", "-D", "hw:0,0", wav_path], 
                                      capture_output=True)
                        print("✅ Azure TTS播放测试完成")
                    else:
                        print("⚠️ 音频转换失败，但Azure TTS生成成功")
                except FileNotFoundError:
                    print("⚠️ ffmpeg未找到，跳过播放测试，但Azure TTS生成成功")
                
                # 清理
                if os.path.exists(wav_path):
                    os.unlink(wav_path)
            else:
                print("❌ 生成的文件为空")
        else:
            print("❌ Azure TTS生成失败")
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理临时文件
        if os.path.exists(output_path):
            os.unlink(output_path)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_azure_tts()