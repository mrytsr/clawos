#!/usr/bin/env python3
"""
Xiaomi Cloud Token Extractor - Auto Version
自动登录并保存设备列表到JSON文件
"""

import json
import os
import sys

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.token_extractor import (
    PasswordXiaomiCloudConnector, 
    QrCodeXiaomiCloudConnector,
    print_if_interactive,
    get_servers_to_check
)

OUTPUT_FILE = "/home/tjx/.openclaw/workspace/mijia/cloud_devices.json"

def auto_login():
    """自动登录（支持2FA验证码输入）"""
    connector = PasswordXiaomiCloudConnector()
    
    print("=" * 50)
    print("Xiaomi Cloud - 自动登录模式")
    print("=" * 50)
    print()
    
    # 检查是否需要验证码
    print("正在尝试登录...")
    if not connector.login():
        print("❌ 登录失败")
        return None
    
    print("✅ 登录成功!")
    return connector

def get_all_devices(connector):
    """获取所有设备"""
    print()
    print("正在获取设备列表...")
    
    all_devices = []
    servers_to_check = ["cn"]  # 中国区
    
    for server in servers_to_check:
        try:
            homes = connector.get_homes(server)
            if homes is None:
                print(f"  ⚠️ 无法获取 {server} 区的家庭信息")
                continue
                
            for home in homes.get("result", {}).get("homelist", []):
                home_id = home.get("id")
                owner_id = connector.userId
                
                devices = connector.get_devices(server, home_id, owner_id)
                if devices and devices.get("result"):
                    for dev in devices["result"].get("device_info", []):
                        device_info = {
                            "name": dev.get("name", ""),
                            "did": dev.get("did", ""),
                            "mac": dev.get("mac", ""),
                            "localip": dev.get("localip", ""),
                            "token": dev.get("token", ""),
                            "model": dev.get("model", ""),
                            "server": server,
                            "home_id": home_id
                        }
                        all_devices.append(device_info)
                        print(f"  ✅ {device_info['name']} ({device_info['localip']})")
        except Exception as e:
            print(f"  ❌ 获取设备失败: {e}")
    
    return all_devices

def save_devices(devices, filename):
    """保存设备到JSON文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "count": len(devices),
            "devices": devices
        }, f, ensure_ascii=False, indent=2)
    print()
    print(f"✅ 已保存 {len(devices)} 台设备到: {filename}")

from datetime import datetime

if __name__ == "__main__":
    # 登录
    connector = auto_login()
    if not connector:
        sys.exit(1)
    
    # 获取设备
    devices = get_all_devices(connector)
    
    if devices:
        # 保存到文件
        save_devices(devices, OUTPUT_FILE)
        print()
        print("=" * 50)
        print("完成！运行以下命令查看设备：")
        print(f"  cat {OUTPUT_FILE}")
        print("=" * 50)
    else:
        print()
        print("⚠️ 未找到任何设备")
        # 即使没有设备也创建空文件
        save_devices([], OUTPUT_FILE)
