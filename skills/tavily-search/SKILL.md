---
name: tavily-search
description: "Web search using Tavily API. Use when you need to search the internet for current information, news, facts, or any topic that requires real-time data. Perfect for: looking up current events and news, finding technical documentation or tutorials, researching companies products or technologies, getting answers to factual questions, searching for code examples or solutions."
---

# Tavily Search Skill

## Quick Start

Use the `tavily_search.py` script to search the web:

```bash
python scripts/tavily_search.py "Python machine learning tutorial"
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `query` | Search query string | Required |
| `--max-results` | Number of results (1-10) | 5 |
| `--include-answer` | Include Tavily AI answer | true |
| `--json` | Output in JSON format | false |

## Examples

```bash
# Basic search
python scripts/tavily_search.py "OpenAI GPT-4 features"

# Limit results
python scripts/tavily_search.py "Python tutorials" --max-results 3

# JSON output
python scripts/tavily_search.py "AI trends 2024" --json

# Without AI answer
python scripts/tavily_search.py "OpenAI" --no-answer
```

## API Configuration

The script uses a hardcoded Tavily API key. To update the key, edit:
- `scripts/tavily_search.py` - Update `TAVILY_API_KEY` variable
