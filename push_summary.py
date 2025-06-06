import os
import openai
from datetime import datetime
import requests

# 从环境变量获取必要信息
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
PAGE_ID = os.environ["NOTION_PAGE_ID"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
QUERY_KEYWORDS = os.environ.get("QUERY_KEYWORDS", "医学影像, 超声, segmentation")

# 初始化 OpenAI
openai.api_key = OPENAI_API_KEY

today = datetime.today().strftime("%Y年%m月")

# 生成 prompt
prompt = f"""
请生成一份关于{today}的医学影像AI月报，包括但不限于以下关键词：{QUERY_KEYWORDS}。
内容结构参考以下格式：
1. 📄 最新论文推荐（列出2~3项，带简单描述）
2. 🧠 数据集进展（列出新发布/更新的公共数据集）
3. 🛠️ 工具或框架更新（如 MONAI、nnUNet 等的版本或功能变化）
请用 Markdown 格式返回。
"""

# 调用 ChatGPT API
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "你是一位智能科研月报助手，擅长总结医学影像领域最新进展。"},
        {"role": "user", "content": prompt}
    ]
)
content = f"## {today} 医学影像AI科研月报\n\n" + response["choices"][0]["message"]["content"]

# 推送到 Notion
def update_notion():
    url = f"https://api.notion.com/v1/blocks/{PAGE_ID}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    data = {
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
    response = requests.patch(url, headers=headers, json=data)
    print("Push result:", response.status_code, response.text)

if __name__ == "__main__":
    update_notion()
