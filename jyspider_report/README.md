# 股票 + 交易计划 - 合并表设计

**时间**: 2026-02-04

---

## 合并后的单表结构 (JSON)

```json
{
  "stock": {
    "name": "海鸥住工",
    "heat": 70
  },
  "author": {
    "name": "醉酒小麻雀",
    "id": "dc6011e9b521455798f03aff075636d1"
  },
  "content": {
    "view": "看好",
    "time": "2026-02-04 11:41:43",
    "logic": "房地产松绑，多地政府收房，用作保障房..."
  },
  "stats": {
    "likes": 0,
    "forwards": 2,
    "comments": 1
  },
  "meta": {
    "url": "/plan?pageType=search&stock_name=海鸥住工",
    "is_strong": false,
    "crawl_time": "2026-02-04 14:50:00"
  }
}
```

---

## 字段总览 (扁平化)

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `stock_name` | string | 股票名称 | 海鸥住工 |
| `stock_heat` | int | 热度 | 70 |
| `author_name` | string | 作者昵称 | 醉酒小麻雀 |
| `author_id` | string | 作者ID | dc6011e9b521... |
| `view` | string | 观点 | 看好/谨慎/说不清 |
| `publish_time` | string | 发布时间 | 2026-02-04 11:41:43 |
| `core_logic` | string | 核心逻辑内容 | 房地产松绑... |
| `likes` | int | 点赞数 | 0 |
| `forwards` | int | 转发数 | 2 |
| `comments` | int | 评论数 | 1 |
| `url` | string | 详情URL | /plan?pageType=search&... |
| `is_strong_logic` | bool | 是否强逻辑 | false |
| `crawl_time` | string | 抓取时间 | 2026-02-04 14:50:00 |

---

## JSON 示例 (单行)

```json
{
  "stock_name": "海鸥住工",
  "stock_heat": 70,
  "author_name": "醉酒小麻雀",
  "author_id": "dc6011e9b521455798f03aff075636d1",
  "view": "看好",
  "publish_time": "2026-02-04 11:41:43",
  "core_logic": "房地产松绑，多地政府收房，用作保障房。利好精装修...",
  "likes": 0,
  "forwards": 2,
  "comments": 1,
  "url": "/plan?pageType=search&stock_name=海鸥住工",
  "is_strong_logic": false,
  "crawl_time": "2026-02-04 14:50:00"
}
```

---

## SQLite 表结构

```sql
CREATE TABLE stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 股票
    stock_name TEXT NOT NULL,
    stock_heat INTEGER DEFAULT 0,
    
    -- 作者
    author_name TEXT,
    author_id TEXT,
    
    -- 内容
    view TEXT,
    publish_time TEXT,
    core_logic TEXT,
    
    -- 互动
    likes INTEGER DEFAULT 0,
    forwards INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    
    -- 元数据
    url TEXT,
    is_strong_logic INTEGER DEFAULT 0,
    crawl_time TEXT,
    
    UNIQUE(stock_name, author_name, publish_time)
);

CREATE INDEX idx_stock ON stocks(stock_name);
CREATE INDEX idx_time ON stocks(publish_time DESC);
CREATE INDEX idx_heat ON stocks(stock_heat DESC);
```

---

## 合并原因

| 之前 | 之后 |
|------|------|
| stocks + authors + plans (3张表) | stocks (1张表) |
| 外键关联 | 扁平化 |
| 复杂查询 | 直接查询 |
| 需要 JOIN | 单表搞定 |

---

## 爬虫代码 (合并版)

```python
import asyncio, re, sqlite3, json
from datetime import datetime

DB = "stocks.db"

def init_db():
    with sqlite3.connect(DB) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY,
            stock_name, stock_heat, author_name, author_id,
            view, publish_time, core_logic,
            likes, forwards, comments,
            url, is_strong_logic, crawl_time,
            UNIQUE(stock_name, author_name, publish_time)
        )""")

async def crawl(pages=10):
    from browser import AgentBrowser
    browser = AgentBrowser()
    
    for p in range(1, pages+1):
        url = f"https://www.jiuyangongshe.com/plan?page={p}"
        await browser.open(url)
        snapshot = await browser.snapshot()
        
        for row in parse(snapshot):
            save(row)
        print(f"Page {p}: OK")
        await asyncio.sleep(2)

def parse(text):
    lines, results, cur = text.split('\n'), [], {}
    for l in lines:
        if 'listitem:' in l:
            if cur: results.append(cur)
            cur = {"crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        elif cur:
            if m := re.search(r'text: "(\d+)"', l): pass  # 序号忽略
            if 'link "' in l and '/u/' not in l and m := re.search(r'link "([^"]+)"', l):
                cur["stock_name"] = m.group(1)
            if m := re.search(r'🔥(\d+)', l): cur["stock_heat"] = int(m.group(1))
            if '/u/' in l:
                if m := re.search(r'link "([^"]+)"', l): cur["author_name"] = m.group(1)
                if m := re.search(r'/u/([^"\s]+)', l): cur["author_id"] = m.group(1)
            if any(x in l for x in ['2025-', '2026-']):
                if m := re.search(r'(2025-\d{2}-\d{2}|2026-\d{2}-\d{2})', l):
                    cur["publish_time"] = m.group(1)
                cur["view"] = "看好" if ' 看好' in l else "谨慎" if ' 谨慎' in l else "说不清"
                cur["core_logic"] = (l.split(' 看好')[-1] or l.split(' 谨慎')[-1] or "")[:500]
    return results + [cur] if cur else results

def save(row):
    with sqlite3.connect(DB) as c:
        c.execute("""INSERT OR REPLACE INTO stocks VALUES (
            NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )""", (
            row.get("stock_name"), row.get("stock_heat"),
            row.get("author_name"), row.get("author_id"),
            row.get("view"), row.get("publish_time"), (row.get("core_logic") or "")[:1000],
            0, 0, 0, "", 0, row.get("crawl_time")
        ))

def export(f="stocks.json"):
    with sqlite3.connect(DB) as c:
        json.dump([dict(r) for r in c.execute("SELECT * FROM stocks ORDER BY publish_time DESC")], 
                  open(f, 'w', encoding='utf-8'))

if __name__ == "__main__":
    init_db()
    asyncio.run(crawl(10))
    export()
```

---

## 结论

✅ **一张表搞定所有数据**
- 股票 + 作者 + 交易计划
- 扁平化设计
- 简单查询
- 易于导出