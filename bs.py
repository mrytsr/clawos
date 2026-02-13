#!/usr/bin/env python3
"""
Brave Search API 搜索脚本
"""

import os
import sys
import json
import requests
from urllib.parse import urlencode


def search(query, api_key=None, count=10, country="US", search_lang=None, freshness=None):
    """
    搜索

    Args:
        query: 搜索关键词
        api_key: Brave API key (默认从环境变量 BRAVE_API_KEY 读取)
        count: 返回结果数量 (1-10)
        country: 国家代码 (如 "US", "CN")
        search_lang: 搜索语言
        freshness: 时间过滤 (pd=24h, pw=7d, pm=30d, py=1y)
    """
    if not api_key:
        api_key = os.environ.get('BRAVE_API_KEY')
        if not api_key:
            print("Error: 请设置 BRAVE_API_KEY 环境变量", file=sys.stderr)
            sys.exit(1)

    base_url = "https://api.search.brave.com/res/v1/web/search"

    params = {
        "q": query,
        "count": min(count, 10),
        "country": country,
    }

    if search_lang:
        params["search_lang"] = search_lang

    if freshness:
        params["freshness"] = freshness

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
    }

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def print_results(results):
    """打印搜索结果"""
    web_results = results.get("web", {}).get("results", [])

    if not web_results:
        print("没有找到结果")
        return

    for i, result in enumerate(web_results, 1):
        print(f"\n{i}. {result.get('title', '无标题')}")
        print(f"   URL: {result.get('url', '')}")
        print(f"   描述: {result.get('description', '')[:150]}...")
        print(f"   发布时间: {result.get('date', '未知')}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Brave Search API 搜索工具")
    parser.add_argument("query", nargs="?", help="搜索关键词")
    parser.add_argument("-n", "--count", type=int, default=10, help="结果数量 (默认10)")
    parser.add_argument("-c", "--country", default="US", help="国家代码 (默认US)")
    parser.add_argument("-l", "--search-lang", help="搜索语言")
    parser.add_argument("-f", "--freshness", choices=["pd", "pw", "pm", "py"],
                        help="时间过滤: pd=24h, pw=7d, pm=30d, py=1y")
    parser.add_argument("-k", "--api-key", help="Brave API key (可选，从环境变量读取)")

    args = parser.parse_args()

    if not args.query:
        parser.print_help()
        sys.exit(0)

    results = search(
        query=args.query,
        api_key=args.api_key,
        count=args.count,
        country=args.country,
        search_lang=args.search_lang,
        freshness=args.freshness
    )

    print_results(results)


if __name__ == "__main__":
    main()