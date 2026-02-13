#!/usr/bin/env python3
"""
Xiaomi Device Controller - 设备控制脚本
"""

import json
import sys
import subprocess

DEVICES_FILE = "/home/tjx/.openclaw/workspace/mijia/devices.json"

def miiocli(ip, token, cmd, *args):
    """调用miiocli命令"""
    command = ["miiocli", "miotdevice", "--ip", ip, "--token", token] + [cmd] + list(args)
    result = subprocess.run(
        command,
        capture_output=True, text=True, timeout=30
    )
    return result.stdout + result.stderr

def find_device(query):
    """查找设备"""
    with open(DEVICES_FILE) as f:
        data = json.load(f)
    
    for home in data[0].get('homes', []):
        for dev in home.get('devices', []):
            name = dev.get('name', '')
            ip = dev.get('localip', '')
            token = dev.get('token', '')
            online = dev.get('isOnline', False)
            
            # 匹配名称或IP
            if query in name or query == ip:
                return {"name": name, "ip": ip, "token": token, "online": online}
    return None

def control(action="status"):
    """控制设备"""
    # 默认控制台灯
    query = sys.argv[1] if len(sys.argv) > 1 else "Desk Lamp 2"
    
    dev = find_device(query)
    if not dev:
        print(f"❌ 未找到设备: {query}")
        return
    
    print(f"📍 设备: {dev['name']}")
    print(f"   IP: {dev['ip']}")
    print(f"   在线: {'✅' if dev['online'] else '❌'}")
    print()
    
    if not dev['online']:
        print("⚠️ 设备离线，无法控制")
        return
    
    ip = dev['ip']
    token = dev['token']
    
    if action in ["status", "状态"]:
        print("📊 获取状态...")
        result = miiocli(ip, token, "get_property_by", "2", "1")
        print(result)
    elif action in ["on", "打开"]:
        print("💡 打开灯光...")
        result = miiocli(ip, token, "set_property_by", "2", "1", "true")
        print(result)
    elif action in ["off", "关闭"]:
        print("🌙 关闭灯光...")
        result = miiocli(ip, token, "set_property_by", "2", "1", "false")
        print(result)
    else:
        print(f"未知操作: {action}")

def list_online():
    """列出在线设备"""
    print("📱 在线设备列表 (有IP):")
    print("=" * 60)
    
    with open(DEVICES_FILE) as f:
        data = json.load(f)
    
    count = 0
    for home in data[0].get('homes', []):
        for dev in home.get('devices', []):
            name = dev.get('name', '')
            ip = dev.get('localip', '')
            token = dev.get('token', '')[:16]
            online = dev.get('isOnline', False)
            
            # 只显示在线且有IP的设备
            if online and ip and (ip.startswith('192.') or ip.startswith('10.')):
                count += 1
                print(f"{count}. {name}")
                print(f"   IP: {ip}")
                print(f"   Token: {token}...")
                print()
    
    print(f"共 {count} 台在线设备")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["list", "ls"]:
        list_online()
    elif len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print("用法:")
        print("  python3 control.py              # 查看在线设备")
        print("  python3 control.py 台灯       # 控制台灯(默认)")
        print("  python3 control.py 192.168.1.28 on   # 打开")
        print("  python3 control.py 192.168.1.28 off  # 关闭")
        print("  python3 control.py 192.168.1.28 status # 状态")
    else:
        action = sys.argv[2] if len(sys.argv) > 2 else "status"
        control(action)
