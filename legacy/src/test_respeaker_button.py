#!/usr/bin/python3
"""
ReSpeaker按钮测试脚本
"""

import os
import sys

# 确保脚本可以找到模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from respeaker_button import test_respeaker_button

if __name__ == "__main__":
    print("🔘 ReSpeaker按钮自动检测测试")
    print("=" * 40)
    
    # 运行自动检测
    test_respeaker_button()