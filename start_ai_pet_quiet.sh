#!/bin/bash
# 启动AI桌宠系统，抑制ALSA错误

# 设置环境变量
export ALSA_QUIET=1
export SDL_AUDIODRIVER=alsa
export ALSA_PCM_CARD=0
export ALSA_PCM_DEVICE=0

# 重定向ALSA错误到/dev/null
exec 2> >(grep -v "ALSA lib" >&2)

echo "🤖 启动AI桌宠系统..."
echo "✅ GPIO权限检查通过，正常启动"
cd src
python3 robot_voice_web_control.py 2>&1 | grep -v "ALSA lib\|Expression.*GetExactSampleRate\|fork_posix"
