#!/usr/bin/env python3
"""
Simple Xiaomi Cloud Token Extractor
"""

import json
import requests
import base64
import hashlib
import hmac
import time
import os

USERNAME = "16602136213"
PASSWORD = "T@xng060414"
OUTPUT_FILE = "/home/tjx/.openclaw/workspace/mijia/devices.json"

def md5_password():
    return hashlib.md5(PASSWORD.encode()).hexdigest().upper()

def login():
    session = requests.Session()
    
    # Step 1
    url1 = "https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true"
    resp1 = session.get(url1)
    data1 = resp1.text.replace("&&&START&&&", "")
    json1 = json.loads(data1)
    
    if "_sign" in json1:
        sign = json1["_sign"]
    else:
        print("Error: Cannot get _sign")
        return None
    
    # Step 2 - Login
    url2 = "https://account.xiaomi.com/pass/serviceLoginAuth2"
    data2 = {
        "sid": "xiaomiio",
        "hash": md5_password(),
        "callback": "https://sts.api.io.mi.com/sts",
        "qs": "%3Fsid%3Dxiaomiio%26_json%3Dtrue",
        "user": USERNAME,
        "_sign": sign,
        "_json": "true"
    }
    resp2 = session.post(url2, params=data2)
    text2 = resp2.text.replace("&&&START&&&", "")
    json2 = json.loads(text2)
    
    if "ssecurity" in json2:
        ssecurity = json2["ssecurity"]
        serviceToken = None
        
        # Check if 2FA needed
        if "notificationUrl" in json2:
            print("需要邮箱验证码，请手动处理...")
            return None
        
        # Step 3 - Get service token
        if "location" in json2:
            resp3 = session.get(json2["location"])
            serviceToken = resp3.cookies.get("serviceToken")
        
        return {
            "session": session,
            "ssecurity": ssecurity,
            "serviceToken": serviceToken,
            "userId": json2.get("userId")
        }
    else:
        print(f"Login failed: {json2}")
        return None

def get_devices(conn):
    if not conn:
        return []
    
    session = conn["session"]
    ssecurity = conn["ssecurity"]
    serviceToken = conn["serviceToken"]
    
    cookies = {
        "userId": str(conn["userId"]),
        "yetAnotherServiceToken": serviceToken,
        "serviceToken": serviceToken,
    }
    
    headers = {
        "Accept-Encoding": "identity",
        "User-Agent": "APP/com.xiaomi.mihome APPV/10.5.201",
        "Content-Type": "application/x-www-form-urlencoded",
        "x-xiaomi-protocal-flag-cli": "PROTOCAL-HTTP2",
    }
    
    # Get homes
    url = "https://api.io.mi.com/app/v2/homeroom/gethome"
    data = {"data": '{"fg": true, "fetch_share": true, "fetch_share_dev": true, "limit": 300}'}
    
    millis = int(time.time() * 1000)
    nonce = base64.b64encode(os.urandom(8) + (int(millis / 60000)).to_bytes(4, byteorder="big")).decode()
    
    # This is simplified - real implementation needs RC4 encryption
    print("需要完整的加密实现来获取设备...")
    return []

if __name__ == "__main__":
    print("尝试登录...")
    conn = login()
    if conn:
        print(f"登录成功! UserID: {conn['userId']}")
        print("注意：完整设备列表需要完整的 RC4 加密实现")
    else:
        print("登录失败或需要验证码")
