Xiaomi Home Devices - Token Extractor

This tool requires your Xiaomi account credentials to fetch device tokens.

## Usage

### Option 1: Interactive Mode (Recommended)
```bash
cd /home/tjx/.openclaw/workspace/xiandan/xiaomi_home
python3 scripts/token_extractor.py
```

### Option 2: Non-Interactive Mode
```bash
python3 scripts/token_extractor.py \
  -u "your_email_or_phone" \
  -p "your_password" \
  -s "cn" \
  -o "my_devices.json"
```

## Output Files
- `my_devices.json` - Raw JSON output
- Excel files will be generated from the JSON

## Notes
- Use `-s cn` for China server (most devices)
- Use `-s us` for United States server
- Other servers: de, ru, tw, sg, in, i2
