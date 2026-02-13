#!/usr/bin/env python3
"""
Xiaomi Device Extractor - Simplified
从已发现的本地设备中读取并保存
"""

import json
from datetime import datetime

# 已发现的设备
DISCOVERED_DEVICES = [
    {"ip": "192.168.1.2", "did": "26b36f82"},
    {"ip": "192.168.1.3", "did": "3dcd4d32"},
    {"ip": "192.168.1.4", "did": "2406b079"},
    {"ip": "192.168.1.5", "did": "2b41c93d"},
    {"ip": "192.168.1.6", "did": "33a207fc"},
    {"ip": "192.168.1.7", "did": "461fda45"},
    {"ip": "192.168.1.8", "did": "1d75a7f2"},
    {"ip": "192.168.1.9", "did": "1da1fbd7"},
    {"ip": "192.168.1.12", "did": "2cbac28b"},
    {"ip": "192.168.1.13", "did": "1d9e8f94"},
    {"ip": "192.168.1.14", "did": "2a0a5a78"},
    {"ip": "192.168.1.15", "did": "235a33d3"},
    {"ip": "192.168.1.16", "did": "17385cde"},
    {"ip": "192.168.1.17", "did": "359417cf"},
    {"ip": "192.168.1.18", "did": "2e98ea63"},
    {"ip": "192.168.1.19", "did": "21456d1b"},
    {"ip": "192.168.1.20", "did": "28d9860d"},
    {"ip": "192.168.1.28", "did": "32844228"},
]

OUTPUT_FILE = "/home/tjx/.openclaw/workspace/mijia/devices.json"

def save_devices():
    """保存设备列表"""
    data = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(DISCOVERED_DEVICES),
        "source": "local_discovery",
        "note": "局域网发现的设备，需要Token才能控制",
        "devices": DISCOVERED_DEVICES
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"已保存 {len(DISCOVERED_DEVICES)} 台设备到: {OUTPUT_FILE}")
    return data

def main():
    print("=" * 50)
    print("Xiaomi Device Saver")
    print("=" * 50)
    print()
    print(f"发现设备: {len(DISCOVERED_DEVICES)} 台")
    print()
    
    save_devices()
    
    print()
    print("下一步:")
    print("  1. 运行: python3 /home/tjx/.openclaw/workspace/xiandan/xiaomi_home/auto_extract.py")
    print("     (输入验证码后自动获取完整设备列表)")
    print("  2. 或者从米家APP手动获取Token填入Excel")
    print("=" * 50)

if __name__ == "__main__":
    main()
