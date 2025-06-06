import os
import openai
import requests
from datetime import datetime, timedelta
import feedparser
from urllib.parse import urlencode

# 获取环境变量
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
PAGE_ID = os.environ["PAGE_ID"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
QUERY_KEYWORDS = os.environ.get("QUERY_KEYWORDS", "medical imaging, segmentation, ultrasound, CT")

# 初始化 GPT
openai.api_key = OPENAI_API_KEY
today = datetime.today()
today_fmt = today.strftime("%Y年%m月")
past_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")

# -------- STEP 1: 抓取 arXiv 论文 --------
def fetch_arxiv_papers(max_results=10):
    base_url = "http://export.arxiv.org/api/query"
    keywords = [kw.strip() for kw in QUERY_KEYWORDS.split(",")]
    raw_query = " OR ".join(keywords)
    query_params = {
        "search_query": f"all:{raw_query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }
    query_string = urlencode(query_params)
    feed_url = f"{base_url}?{query_string}"
    feed = feedparser.parse(feed_url)
    papers = []
    for entry in feed.entries:
        title = entry.title.strip().replace("\n", " ")
        date = entry.published.split("T")[0]
        link = entry.link
        papers.append(f"- [{date}] {title} ({link})")
    return papers

# -------- STEP 2: 构造 ChatGPT Prompt 并获取摘要 --------
def generate_summary_from_papers(papers):
    papers_markdown = "\n".join(papers)
    prompt = f"""
以下是近 30 天内与“{QUERY_KEYWORDS}”相关的 arXiv 论文列表，请根据它们总结当前医学影像研究的关键趋势、热点方向和研究关注点。输出请使用 Markdown，并按以下格式：

## {today_fmt} 医学影像 arXiv 热点论文总结

### 🔍 趋势概览
（由 GPT 生成的总结）

### 📄 论文列表
{papers_markdown}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "你是一位专业的医学影像研究分析助手"},
            {"role": "user", "content": prompt}
        ]
    )
    return response["choices"][0]["message"]["content"]

# -------- STEP 3: 推送到 Notion --------
def push_to_notion(content):
    url = f"https://api.notion.com/v1/blocks/{PAGE_ID}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    payload = {
        "children": [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": content}
                }]
            }
        }]
    }
    res = requests.patch(url, headers=headers, json=payload)
    print("Push result:", res.status_code, res.text)

# -------- 主流程 --------
if __name__ == "__main__":
    papers = fetch_arxiv_papers()
    summary = generate_summary_from_papers(papers)
    push_to_notion(summary)
