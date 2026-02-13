#!/usr/bin/env python3
"""
飞书日历Skill - 默认用户195

用法:
  python3 feishu_calendar.py add --title "标题" [--date YYYY-MM-DD] [--time HH:MM] [--duration 分钟] [--desc "描述"] [--uid 用户ID]
"""

import sys
import os
import json
from datetime import datetime, timedelta

# 添加xiandan路径
sys.path.insert(0, '/home/tjx/xiandan')

from lib.fs_calendar import create as fs_create
from lib.fs_access_token import get_valid_access_token


DEFAULT_UID = 195  # 唐君行


def add_event(
    user_id: int,
    summary: str,
    date: str = None,
    hour: int = 10,
    minute: int = 0,
    duration_minutes: int = 30,
    description: str = ""
) -> dict:
    """
    添加日历事件
    
    Args:
        user_id: 用户ID (默认195)
        summary: 事件标题
        date: 日期 (YYYY-MM-DD，默认明天)
        hour: 小时 (0-23)
        minute: 分钟
        duration_minutes: 持续时间
        description: 事件描述
    
    Returns:
        dict: 事件信息或错误
    """
    # 获取token
    token_info = get_valid_access_token(user_id)
    if not token_info:
        return {
            "success": False,
            "error": f"用户 {user_id} 未绑定飞书或token已过期"
        }
    
    user_access_token = token_info["access_token"]
    
    # 默认明天
    if not date:
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 创建事件
    try:
        result = fs_create(
            user_access_token=user_access_token,
            date=date,
            hour=hour,
            minute=minute,
            duration_minutes=duration_minutes,
            summary=summary,
            description=description,
            timezone_name="Asia/Shanghai"
        )
        
        if result.get("code") == 0:
            event = result.get("data", {}).get("event", {})
            return {
                "success": True,
                "event_id": event.get("event_id"),
                "summary": event.get("summary"),
                "start_time": event.get("start_time", {}).get("timestamp"),
                "end_time": event.get("end_time", {}).get("timestamp"),
                "url": event.get("app_link"),
                "organizer": event.get("event_organizer", {}).get("display_name")
            }
        else:
            return {
                "success": False,
                "error": result.get("msg", "创建失败")
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def parse_args():
    """解析命令行参数"""
    args = {
        "action": "add",
        "uid": DEFAULT_UID,
        "title": None,
        "date": None,
        "time": "10:00",
        "duration": 30,
        "desc": ""
    }
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg in ["add", "list", "delete"]:
            args["action"] = arg
        elif arg == "--title" and i + 1 < len(sys.argv):
            args["title"] = sys.argv[i + 1]
            i += 1
        elif arg == "--date" and i + 1 < len(sys.argv):
            args["date"] = sys.argv[i + 1]
            i += 1
        elif arg == "--time" and i + 1 < len(sys.argv):
            args["time"] = sys.argv[i + 1]
            i += 1
        elif arg == "--duration" and i + 1 < len(sys.argv):
            args["duration"] = int(sys.argv[i + 1])
            i += 1
        elif arg == "--desc" and i + 1 < len(sys.argv):
            args["desc"] = sys.argv[i + 1]
            i += 1
        elif arg == "--uid" and i + 1 < len(sys.argv):
            args["uid"] = int(sys.argv[i + 1])
            i += 1
        elif arg in ["-h", "--help"]:
            show_help()
            sys.exit(0)
        
        i += 1
    
    return args


def show_help():
    print(__doc__)


def main():
    args = parse_args()
    
    if args["action"] == "add":
        if not args["title"]:
            print("❌ 错误: 需要指定 --title 参数")
            print("\n用法: python3 feishu_calendar.py add --title '标题' [--date YYYY-MM-DD] [--time HH:MM] [--duration 分钟] [--desc '描述']")
            sys.exit(1)
        
        # 解析时间
        hour, minute = 10, 0
        if ":" in args["time"]:
            parts = args["time"].split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
        
        print(f"📅 添加日历事件")
        print(f"   用户: uid={args['uid']}")
        print(f"   标题: {args['title']}")
        print(f"   日期: {args['date'] or '明天'}")
        print(f"   时间: {hour:02d}:{minute:02d}")
        print(f"   时长: {args['duration']}分钟")
        print()
        
        result = add_event(
            user_id=args["uid"],
            summary=args["title"],
            date=args["date"],
            hour=hour,
            minute=minute,
            duration_minutes=args["duration"],
            description=args["desc"]
        )
        
        if result["success"]:
            print("✅ 日历事件创建成功!")
            print(f"\n📋 事件信息:")
            print(f"   标题: {result['summary']}")
            print(f"   ID: {result['event_id']}")
            if result.get("url"):
                print(f"   链接: {result['url']}")
        else:
            print(f"❌ 创建失败: {result['error']}")
        
        # 输出JSON供其他程序读取
        print("\n" + "=" * 40)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    else:
        print("🚧 仅支持 add 操作")
        sys.exit(1)


if __name__ == "__main__":
    main()
