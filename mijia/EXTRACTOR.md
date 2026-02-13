# Xiaomi Device Extractor

## 快速开始

### 方法1: 运行提取脚本（推荐）

```bash
cd /home/tjx/.openclaw/workspace/xiandan/xiaomi_home
bash run_extract.sh
```

流程：
1. 自动开始登录
2. 提示输入验证码（查看邮箱）
3. 自动完成并保存到 `/home/tjx/.openclaw/workspace/mijia/devices.json`

### 方法2: 手动运行

```bash
cd /home/tjx/.openclaw/workspace/xiandan/xiaomi_home
python3 scripts/token_extractor.py
```

## 输出文件

| 文件 | 说明 |
|------|------|
| `/home/tjx/.openclaw/workspace/mijia/devices.json` | 设备列表JSON |
| `/home/tjx/.openclaw/workspace/mijia/devices.xlsx` | Excel格式 |
| `/home/tjx/.openclaw/workspace/mijia/extract.log` | 日志文件 |

## 查看结果

```bash
# 查看JSON
cat /home/tjx/.openclaw/workspace/mijia/devices.json

# 查看Excel (需要openpyxl)
python3 -c "import openpyxl; wb=openpyxl.load_workbook('/home/tjx/.openclaw/workspace/mijia/devices.xlsx'); print(wb.active.title)"
```

## 已知问题

### 验证码
如果登录需要验证码：
1. 查看邮箱 `mrytsr@qq.com`
2. 输入验证码完成登录

### 账号信息位置
`/home/tjx/.openclaw/workspace/mijia/account.md`

## 下一步

获取设备Token后，可以：
1. 控制设备：`miiocli miotdevice --ip <IP> --token <TOKEN> status`
2. 查看所有支持的命令：`miiocli --help`
