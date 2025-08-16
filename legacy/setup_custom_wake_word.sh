import os
import sys

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
    except Exception as e:
        print(f"警告: 无法加载环境变量: {e}")

load_env()

try:
    import pvporcupine
    access_key = os.getenv('PICOVOICE_ACCESS_KEY')
    
    if not access_key:
        print("❌ 未找到 PICOVOICE_ACCESS_KEY")
        sys.exit(1)
    
    print(f"🔑 使用 Access Key: {access_key[:10]}...")
    
    # 测试自定义唤醒词
    try:
        porcupine = pvporcupine.create(
            access_key=access_key,
            model_path='src/wake_words/porcupine_params_zh.pv',
            keyword_paths=['src/wake_words/kk_zh_raspberry-pi_v3_0_0.ppn']
        )
        print("✅ 自定义唤醒词 'kk' 配置成功！")
        print(f"📊 采样率: {porcupine.sample_rate}")
        print(f"📏 帧长度: {porcupine.frame_length}")
        porcupine.delete()
        
    except Exception as e:
        print(f"❌ 自定义唤醒词配置失败: {e}")
        
        # 尝试内置英文关键词作为备选
        try:
            porcupine = pvporcupine.create(
                access_key=access_key,
                keywords=['picovoice']
            )
            print("⚠️ 使用内置英文关键词 'picovoice' 作为备选")
            porcupine.delete()
        except Exception as e2:
            print(f"❌ 备选方案也失败: {e2}")

except ImportError as e:
    print(f"❌ 无法导入 pvporcupine: {e}")
except Exception as e:
    print(f"❌ 其他错误: {e}")