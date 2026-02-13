# Brave Search API Demo

一个使用Brave Search API的Python演示程序。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置API密钥

1. 访问 [Brave Search API](https://brave.com/search/api/) 获取API密钥
2. 设置环境变量：

```bash
export BRAVE_API_KEY="your_api_key_here"
```

或者在Windows上：

```cmd
set BRAVE_API_KEY=your_api_key_here
```

## 运行演示

```bash
python bravesearch_demo.py
```

## 功能特性

- 🔍 **网页搜索**: 执行标准网页搜索并显示结果
- 📰 **新闻搜索**: 搜索最新新闻
- 📊 **搜索统计**: 显示搜索结果统计信息
- 🎨 **美观输出**: 格式化显示搜索结果

## 使用示例

```python
from bravesearch_demo import BraveSearchAPI

# 初始化
brave = BraveSearchAPI("your_api_key")

# 网页搜索
results = brave.search("Python编程")

# 新闻搜索  
news = brave.get_news("人工智能")
```