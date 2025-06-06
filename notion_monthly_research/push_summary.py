import os
import requests
from datetime import datetime

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
PAGE_ID = os.environ["NOTION_PAGE_ID"]

today = datetime.today().strftime("%Y年%m月")

content = f"""
## {today} 医学影像AI科研月报

### 📄 本月论文推荐
- [Example] Cross-Modality Ultrasound Image Synthesis via Diffusion

### 🧠 数据集更新
- TCIA：新冠肺炎CT影像数据更新
- Grand Challenge：超声图像器官分割挑战赛

### 🛠️ 工具动态
- MONAI v1.4：支持超声图像增强模块，适配3D分割任务

（此内容为示例，我可每月帮你自动填充）
"""

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
