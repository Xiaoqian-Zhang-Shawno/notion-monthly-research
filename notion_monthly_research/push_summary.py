import os
import sys
import time
import json
import requests
import feedparser
from datetime import datetime, timedelta
from urllib.parse import urlencode
from typing import List
from openai import OpenAI

# =========================
# 环境变量（请先在系统里配置）
# =========================
# DeepSeek
#   OPENAI_API_KEY=<你的 DeepSeek API Key>
#   OPENAI_BASE_URL=https://api.deepseek.com   （也可不设，用下面的默认）
# Notion
#   NOTION_TOKEN=<你的 Notion 集成密钥>
#   PAGE_ID=<要写入的页面或块的 block_id>
# arXiv 关键词（可选）
#   QUERY_KEYWORDS="medical imaging, segmentation, ultrasound, CT"

DEEPSEEK_API_KEY = os.environ.get("OPENAI_API_KEY")
DEEPSEEK_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
PAGE_ID = os.environ.get("PAGE_ID")
QUERY_KEYWORDS = os.environ.get("QUERY_KEYWORDS","Large model fine-tuning, multimodal decoupling, multimodal alignment, multimodal enhancement")

if not DEEPSEEK_API_KEY:
    print("ERROR: 请设置环境变量 OPENAI_API_KEY 为你的 DeepSeek API Key")
    sys.exit(1)
if not NOTION_TOKEN or not PAGE_ID:
    print("ERROR: 请设置环境变量 NOTION_TOKEN 与 PAGE_ID")
    sys.exit(1)

# 初始化 DeepSeek（OpenAI 兼容）客户端
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


# 时间
today = datetime.today()
today_fmt = today.strftime("%Y年%m月")
past_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")


# =========================
# 工具函数
# =========================
def chunk_text(text: str, chunk_size: int = 1800) -> List[str]:
    """将长文本切成多段，避免 Notion 单块过长"""
    lines = text.splitlines()
    chunks, cur, cur_len = [], [], 0
    for ln in lines:
        ln_len = len(ln) + 1
        if cur_len + ln_len > chunk_size and cur:
            chunks.append("\n".join(cur))
            cur, cur_len = [], 0
        cur.append(ln)
        cur_len += ln_len
    if cur:
        chunks.append("\n".join(cur))
    return chunks


def notion_append_paragraph_blocks(page_or_block_id: str, markdown_text: str):
    """将 Markdown 文本按段落块追加到 Notion 指定页面/块下"""
    url = f"https://api.notion.com/v1/blocks/{page_or_block_id}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    # 简单按段落拆分（\n\n 作为分段），并进一步分块控制每段长度
    paragraphs = markdown_text.split("\n\n")
    blocks = []
    for para in paragraphs:
        for piece in chunk_text(para, 1800):
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": piece}}]
                }
            })

    payload = {"children": blocks}
    # 轻量重试
    for attempt in range(3):
        res = requests.patch(url, headers=headers, json=payload, timeout=30)
        if res.status_code in (200, 201):
            print("Notion push OK.")
            return
        print(f"Notion push failed [{res.status_code}]: {res.text}")
        if res.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** attempt)
            continue
        break
    raise RuntimeError("Push to Notion failed.")


# =========================
# 业务逻辑
# =========================
def fetch_arxiv_papers(max_results=10) -> List[str]:
    """抓取 arXiv 最近论文（按提交时间倒序）。返回 Markdown 列表行。"""
    base_url = "http://export.arxiv.org/api/query"
    keywords = [kw.strip() for kw in QUERY_KEYWORDS.split(",") if kw.strip()]
    raw_query = " OR ".join(keywords) if keywords else "medical imaging"
    params = {
        "search_query": f"all:{raw_query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }
    feed_url = f"{base_url}?{urlencode(params)}"
    feed = feedparser.parse(feed_url)

    papers = []
    for entry in feed.entries:
        title = entry.title.strip().replace("\n", " ")
        date = entry.published.split("T")[0] if hasattr(entry, "published") else ""
        link = entry.link
        papers.append(f"- [{date}] {title} ({link})")
    return papers


def generate_summary_from_papers(papers: List[str]) -> str:
    """用 DeepSeek 生成 Markdown 总结（OpenAI 兼容 Chat Completions）"""
    papers_markdown = "\n".join(papers) if papers else "- （近30天未抓到相关论文）"
    prompt = f"""
以下是近 30 天内与“{QUERY_KEYWORDS}”相关的 arXiv 论文列表，请根据它们总结当前多模态解耦、融合、对比、增强研究以及大模型微调的关键趋势、热点方向和研究关注点。输出请使用 Markdown，并按以下格式：

## {today_fmt} 多模态 arXiv 热点论文总结

### 🔍 趋势概览
（由模型生成的简洁要点，避免空话套话，尽量引用论文中的可验证信号）

### 📄 论文列表
{papers_markdown}
""".strip()

    # 轻量重试
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model="deepseek-reasoner",  # 或 "deepseek-reasoner"
                messages=[
                    {"role": "system", "content": "你是一位专业的AI算法和大模型研究分析助手"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"DeepSeek API 调用失败（第 {attempt+1} 次）: {e}")
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("DeepSeek 生成失败，请检查网络/API Key/额度。")


def main():
    print(f"Keywords: {QUERY_KEYWORDS}")
    print("Fetching arXiv...")
    papers = fetch_arxiv_papers(max_results=12)

    print("Generating summary with DeepSeek...")
    summary_md = generate_summary_from_papers(papers)

    print("Pushing to Notion...")
    notion_append_paragraph_blocks(PAGE_ID, summary_md)

    print("Done.")


if __name__ == "__main__":
    main()
