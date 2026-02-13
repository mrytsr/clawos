#!/bin/bash
#
# Xiaomi Device Controller - 设备控制脚本
#
# 使用方法:
#   ./control_light.sh <设备名称或IP>
#
# 示例:
#   ./control_light.sh 台灯           # 按名称控制
#   ./control_light.sh 192.168.1.28  # 按IP控制
#   ./control_light.sh on 192.168.1.28  # 打开
#   ./control_light.sh off 192.168.1.28 # 关闭
#   ./control_light.sh status 192.168.1.28  # 查看状态
#

DEVICES_FILE="/home/tjx/.openclaw/workspace/mijia/devices.json"

# 查找设备IP和Token
find_device() {
    local name="$1"
    python3 -c "
import json
with open('$DEVICES_FILE') as f:
    data = json.load(f)
for home in data[0].get('homes', []):
    for dev in home.get('devices', []):
        if '$name' in dev.get('name', '') or dev.get('localip', '') == '$name':
            print(f\"{dev.get('localip', '')} {dev.get('token', '')} {dev.get('name', '')}\")
            break
"
}

# 控制设备
control_device() {
    local ip="$1"
    local token="$2"
    local action="$3"
    
    case "$action" in
        "on"|"打开")
            echo "打开设备: $ip"
            miotdevice "$ip" "$token" set_property_by 2 1 true
            ;;
        "off"|"关闭")
            echo "关闭设备: $ip"
            miotdevice "$ip" "$token" set_property_by 2 1 false
            ;;
        "status"|"状态")
            echo "查看状态: $ip"
            miotdevice "$ip" "$token" get_property_by 2 1
            ;;
        *)
            echo "未知操作: $action"
            ;;
    esac
}

# 主逻辑
if [ -z "$1" ]; then
    echo "用法: $0 <设备名称或IP> [on|off|status]"
    echo ""
    echo "可用设备 (在线且有IP):"
    python3 -c "
import json
with open('$DEVICES_FILE') as f:
    data = json.load(f)
for home in data[0].get('homes', []):
    for dev in home.get('devices', []):
        ip = dev.get('localip', '')
        online = dev.get('isOnline', False)
        name = dev.get('name', '')
        if online and ip and (ip.startswith('192.') or ip.startswith('10.')):
            print(f'  {name}: {ip}')
"
    exit 1
fi

# 查找设备
result=$(find_device "$1")
if [ -z "$result" ]; then
    echo "未找到设备: $1"
    exit 1
fi

ip=$(echo "$result" | cut -d' ' -f1)
token=$(echo "$result" | cut -d' ' -f2)
name=$(echo "$result" | cut -d' ' -f3-)

echo "设备: $name"
echo "IP: $ip"
echo ""

# 如果有第二个参数，执行操作
if [ -n "$2" ]; then
    control_device "$ip" "$token" "$2"
else
    # 默认查看状态
    control_device "$ip" "$token" "status"
fi
