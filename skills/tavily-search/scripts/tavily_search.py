#!/usr/bin/env python3
"""
Tavily Web Search Script
"""

import argparse
import json
import requests
from datetime import datetime

# API Key (hardcoded)
TAVILY_API_KEY = "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"
TAVILY_API_URL = "https://api.tavily.com/search"


def search(query, max_results=5, include_answer=True, json_output=False):
    """
    Search the web using Tavily
    
    Args:
        query: Search query
        max_results: Number of results (1-10)
        include_answer: Include Tavily's AI-generated answer
        json_output: Output in JSON format
    
    Returns:
        Search results
    """
    payload = {
        "query": query,
        "max_results": max_results,
        "include_answer": include_answer,
        "include_images": False,
        "include_raw_content": False,
        "include_links": True
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TAVILY_API_KEY}"
    }
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Searching: {query}", flush=True)
    
    try:
        response = requests.post(
            TAVILY_API_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        if json_output:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print_results(data, query)
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Search failed: {e}", flush=True)
        return None


def print_results(data, query):
    """Pretty print search results"""
    if not data:
        print("[ERROR] No results")
        return
    
    results = data.get("results", [])
    
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"Found: {len(results)} results")
    print(f"{'='*60}\n")
    
    for i, result in enumerate(results, 1):
        print(f"--- Result {i} ---")
        print(f"Title: {result.get('title', 'N/A')}")
        print(f"URL: {result.get('url', 'N/A')}")
        print(f"Content: {result.get('content', 'N/A')[:150]}...")
        print()
    
    # Tavily's direct answer
    if data.get("answer"):
        print("="*60)
        print("AI Answer:")
        print("="*60)
        print(data["answer"])


def main():
    parser = argparse.ArgumentParser(description="Tavily Web Search")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--max-results", type=int, default=5, help="Number of results (1-10)")
    parser.add_argument("--no-answer", action="store_true", help="Exclude AI answer")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    search(
        args.query,
        max_results=min(max(1, args.max_results), 10),
        include_answer=not args.no_answer,
        json_output=args.json
    )


if __name__ == "__main__":
    main()
