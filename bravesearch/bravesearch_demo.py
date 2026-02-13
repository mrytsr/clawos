#!/usr/bin/env python3
"""
Brave Search API Demo
演示如何使用Brave Search API进行网络搜索
"""

import requests
import json
import os
from typing import Dict, List, Optional


class BraveSearchAPI:
    def __init__(self, api_key: str):
        """
        初始化Brave Search API客户端
        
        Args:
            api_key: Brave Search API密钥
        """
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1"
        self.headers = {
            "X-Subscription-Token": api_key,
            "Accept": "application/json"
        }
    
    def search(self, query: str, count: int = 10, offset: int = 0) -> Dict:
        """
        执行搜索请求
        
        Args:
            query: 搜索关键词
            count: 返回结果数量 (最多20)
            offset: 结果偏移量
            
        Returns:
            搜索结果JSON
        """
        params = {
            "q": query,
            "count": min(count, 20),  # Brave API限制最多20个结果
            "offset": offset
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/web/search",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def get_news(self, query: str, count: int = 10) -> Dict:
        """
        搜索新闻
        
        Args:
            query: 搜索关键词
            count: 返回结果数量
            
        Returns:
            新闻搜索结果
        """
        params = {
            "q": query,
            "count": min(count, 20)
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/news/search",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}


def print_results(results: Dict, result_type: str = "web"):
    """
    格式化打印搜索结果
    
    Args:
        results: 搜索结果
        result_type: 结果类型 (web/news)
    """
    if "error" in results:
        print(f"❌ 错误: {results['error']}")
        return
    
    if result_type == "web":
        web_results = results.get("web", {}).get("results", [])
        print(f"🔍 找到 {len(web_results)} 个网页结果:\n")
        
        for i, result in enumerate(web_results, 1):
            title = result.get("title", "无标题")
            url = result.get("url", "")
            description = result.get("description", "无描述")
            
            print(f"{i}. {title}")
            print(f"   📍 {url}")
            print(f"   📝 {description[:100]}{'...' if len(description) > 100 else ''}")
            print()
    
    elif result_type == "news":
        news_results = results.get("news", {}).get("results", [])
        print(f"📰 找到 {len(news_results)} 条新闻:\n")
        
        for i, result in enumerate(news_results, 1):
            title = result.get("title", "无标题")
            url = result.get("url", "")
            description = result.get("description", "无描述")
            
            print(f"{i}. {title}")
            print(f"   🔗 {url}")
            print(f"   📄 {description[:100]}{'...' if len(description) > 100 else ''}")
            print()


def main():
    """
    主演示函数
    """
    print("🦁 Brave Search API Demo\n")
    
    # 获取API密钥
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        print("❌ 错误: 请设置环境变量 BRAVE_API_KEY")
        print("   获取API密钥: https://brave.com/search/api/")
        return
    
    # 初始化搜索API
    brave = BraveSearchAPI(api_key)
    
    # 演示1: 网页搜索
    print("🌐 === 网页搜索演示 ===")
    query = input("请输入搜索关键词 (默认: Python编程): ").strip()
    if not query:
        query = "Python编程"
    
    print(f"\n🔍 搜索: {query}")
    results = brave.search(query)
    print_results(results, "web")
    
    # 演示2: 新闻搜索
    print("\n📰 === 新闻搜索演示 ===")
    news_query = input("请输入新闻搜索关键词 (默认: 人工智能): ").strip()
    if not news_query:
        news_query = "人工智能"
    
    print(f"\n📰 搜索新闻: {news_query}")
    news_results = brave.get_news(news_query)
    print_results(news_results, "news")
    
    # 演示3: 搜索结果统计
    print("\n📊 === 搜索统计演示 ===")
    stats_query = "机器学习"
    print(f"📈 统计搜索: {stats_query}")
    stats_results = brave.search(stats_query, count=5)
    
    if "web" in stats_results:
        total_results = len(stats_results["web"].get("results", []))
        print(f"   ✅ 成功获取 {total_results} 个结果")
        
        # 显示混合结果类型
        if "mixed" in stats_results:
            mixed = stats_results["mixed"]
            print(f"   📱 混合结果: {len(mixed.get('results', []))} 个")
    
    print("\n🎉 演示完成!")


if __name__ == "__main__":
    main()