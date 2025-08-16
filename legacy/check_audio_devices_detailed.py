#!/usr/bin/env python3
"""
详细检查音频设备
"""

import os
import subprocess
import stat

def check_snd_devices():
    """详细检查/dev/snd设备"""
    print("🔍 详细检查 /dev/snd 设备")
    print("=" * 40)
    
    snd_dir = "/dev/snd"
    if not os.path.exists(snd_dir):
        print(f"❌ {snd_dir} 不存在")
        return
    
    try:
        files = os.listdir(snd_dir)
        print(f"📁 {snd_dir} 包含 {len(files)} 个文件:")
        
        for filename in sorted(files):
            filepath = os.path.join(snd_dir, filename)
            try:
                stat_info = os.stat(filepath)
                mode = stat.filemode(stat_info.st_mode)
                
                # 获取用户和组名
                import pwd, grp
                try:
                    user_name = pwd.getpwuid(stat_info.st_uid).pw_name
                except:
                    user_name = str(stat_info.st_uid)
                
                try:
                    group_name = grp.getgrgid(stat_info.st_gid).gr_name
                except:
                    group_name = str(stat_info.st_gid)
                
                # 检查当前用户访问权限
                can_read = os.access(filepath, os.R_OK)
                can_write = os.access(filepath, os.W_OK)
                
                print(f"  📱 {filename}:")
                print(f"     权限: {mode}")
                print(f"     所有者: {user_name}:{group_name}")
                print(f"     当前用户访问: 读{'✅' if can_read else '❌'} 写{'✅' if can_write else '❌'}")
                
            except Exception as e:
                print(f"  ❌ 无法检查 {filename}: {e}")
                
    except Exception as e:
        print(f"❌ 无法列出设备: {e}")

def test_specific_devices():
    """测试特定设备"""
    print("\n🧪 测试特定播放设备")
    print("=" * 40)
    
    # 可能的播放设备
    devices = [
        "/dev/snd/pcmC0D0p",  # Card 0, Device 0, Playback
        "/dev/snd/pcmC0D1p",  # Card 0, Device 1, Playback
        "/dev/snd/controlC0", # Control device
    ]
    
    for device in devices:
        if os.path.exists(device):
            print(f"📱 测试设备: {device}")
            
            # 检查权限
            can_read = os.access(device, os.R_OK)
            can_write = os.access(device, os.W_OK)
            print(f"   权限: 读{'✅' if can_read else '❌'} 写{'✅' if can_write else '❌'}")
            
            # 尝试打开
            try:
                with open(device, 'rb') as f:
                    print(f"   ✅ 可以读取打开")
            except Exception as e:
                print(f"   ❌ 读取打开失败: {e}")
            
            try:
                with open(device, 'wb') as f:
                    print(f"   ✅ 可以写入打开")
            except Exception as e:
                print(f"   ❌ 写入打开失败: {e}")
        else:
            print(f"❌ 设备不存在: {device}")

def check_user_groups():
    """检查用户组详情"""
    print("\n👤 检查用户组详情")
    print("=" * 40)
    
    import pwd, grp
    
    # 获取当前用户信息
    user_info = pwd.getpwuid(os.getuid())
    print(f"当前用户: {user_info.pw_name} (UID: {user_info.pw_uid})")
    print(f"主组: {user_info.pw_gid}")
    
    # 获取所有组
    groups = os.getgroups()
    print(f"所属组 (GID): {groups}")
    
    # 获取组名
    group_names = []
    for gid in groups:
        try:
            group_name = grp.getgrgid(gid).gr_name
            group_names.append(f"{group_name}({gid})")
        except:
            group_names.append(str(gid))
    
    print(f"所属组 (名称): {', '.join(group_names)}")
    
    # 检查audio组
    try:
        audio_group = grp.getgrnam('audio')
        print(f"\naudio组信息:")
        print(f"  GID: {audio_group.gr_gid}")
        print(f"  成员: {', '.join(audio_group.gr_mem)}")
        
        if audio_group.gr_gid in groups:
            print(f"  ✅ 当前用户在audio组中")
        else:
            print(f"  ❌ 当前用户不在audio组中")
    except:
        print("❌ 无法获取audio组信息")

def test_with_strace():
    """使用strace跟踪aplay调用"""
    print("\n🔍 使用strace跟踪aplay调用")
    print("=" * 40)
    
    try:
        # 运行strace跟踪aplay
        cmd = ['strace', '-e', 'trace=openat,open', 'aplay', os.path.expanduser('~/test.wav')]
        print(f"🔄 运行: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        print("📋 strace输出 (stderr):")
        print(result.stderr)
        
        if result.stdout:
            print("📋 标准输出:")
            print(result.stdout)
            
    except FileNotFoundError:
        print("❌ strace命令不可用")
        print("💡 安装: sudo apt install strace")
    except subprocess.TimeoutExpired:
        print("⏰ strace超时")
    except Exception as e:
        print(f"❌ strace失败: {e}")

if __name__ == "__main__":
    print("🔍 音频设备详细诊断")
    print("=" * 50)
    
    # 检查用户组
    check_user_groups()
    
    # 检查设备文件
    check_snd_devices()
    
    # 测试特定设备
    test_specific_devices()
    
    # 使用strace跟踪
    test_with_strace()
    
    print("\n" + "=" * 50)
    print("🎯 诊断完成")
    print("💡 如果设备权限都正常，可能是ALSA配置问题")