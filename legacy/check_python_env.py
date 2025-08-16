#!/usr/bin/env python3
"""
检查Python环境和依赖
"""

import sys
import os

print("🐍 Python环境检查")
print("=" * 40)

print(f"Python版本: {sys.version}")
print(f"Python路径: {sys.executable}")
print(f"当前工作目录: {os.getcwd()}")

print("\n📦 Python路径:")
for i, path in enumerate(sys.path):
    print(f"  {i}: {path}")

print("\n🔍 尝试导入依赖:")

# 测试numpy
try:
    import numpy
    print(f"✅ numpy {numpy.__version__} - 路径: {numpy.__file__}")
except ImportError as e:
    print(f"❌ numpy - {e}")

# 测试scipy
try:
    import scipy
    print(f"✅ scipy {scipy.__version__} - 路径: {scipy.__file__}")
except ImportError as e:
    print(f"❌ scipy - {e}")

# 测试vosk
try:
    import vosk
    print(f"✅ vosk - 路径: {vosk.__file__}")
except ImportError as e:
    print(f"❌ vosk - {e}")

# 测试pyaudio
try:
    import pyaudio
    print(f"✅ pyaudio {pyaudio.__version__}")
except ImportError as e:
    print(f"❌ pyaudio - {e}")

# 测试speech_recognition
try:
    import speech_recognition as sr
    print(f"✅ speech_recognition {sr.__version__}")
except ImportError as e:
    print(f"❌ speech_recognition - {e}")