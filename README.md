# notion-monthly-research
#本项目旨在实现一个 自动化的学术论文月度总结工作流。系统通过 GitHub Actions 定时触发，调用 DeepSeek API 从 arXiv 获取近一个月的相关研究论文，并利用大模型自动生成趋势分析与总结。随后，结果会被推送到指定的 Notion 页面，形成可视化的月度研究动态归档。整个过程无需人工干预，能够帮助研究人员高效追踪领域前沿进展，并保持学术资料的持续积累与同步。<br>
shawno的每月AI影像热点周报，任务更新日志<br>

2025.06.06<br>
_notion上成功更新了，这是伟大的开始_<br>
我尝试接入gpt，更多期刊尝试更新抓取中，可以给我更多的推荐！！！<br>
2025.09.22<br>
md,gpt太贵了我更新了接口，可以使用所有大模型，我现在换成了deepseek<br>

---

# 使用方法

## 1. 前置准备

1. **Fork / Clone 本仓库**
   将项目代码拉到本地或直接 fork 到你的 GitHub。

2. **获取 DeepSeek API Key**

   * 前往 [DeepSeek 控制台](https://platform.deepseek.com/)，生成一个 `sk-...` 的 API Key。

3. **创建 Notion 集成**

   * 打开 [Notion My Integrations](https://www.notion.com/my-integrations)。
   * 创建新集成，获得一个 `secret_...` 的 token（记为 `NOTION_TOKEN`）。
   * 打开你想存放结果的页面，在右上角 **··· → 添加连接 (Add connections)**，授权给这个集成。
   * 复制页面 URL 末尾的 32 位 UUID（记为 `NOTION_PAGE_ID`）。

---

## 2. 配置 GitHub Secrets

进入你的 GitHub 仓库 → **Settings → Secrets and variables → Actions**，新增以下 Secrets：

* `DEEPSEEK_API_KEY` = 你的 DeepSeek API Key (`sk-...`)
* `NOTION_TOKEN` = 你的 Notion 集成 token (`secret_...`)
* `NOTION_PAGE_ID` = Notion 页面 ID (`xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
* （可选）`QUERY_KEYWORDS` = 你想监控的关键词（默认值是 `"medical imaging, segmentation, ultrasound, CT"`）

---

## 3. 修改/确认 Workflow

仓库里已有 `.github/workflows/main.yml`，内容大致如下：

```yaml
on:
  schedule:
    - cron: '0 0 1 * *'   # 每月1号 UTC 零点运行
  workflow_dispatch:       # 允许手动触发
```

这会在每月 1 日自动执行，或者你也可以在 **GitHub Actions → Run workflow** 手动运行。

---

## 4. 工作流运行效果

1. Workflow 会执行 `push_summary.py`：

   * 抓取近 30 天的 arXiv 论文（按关键词）。
   * 使用 DeepSeek 模型自动总结研究趋势。
   * 推送总结结果到你的 Notion 页面。

2. 运行完成后，打开 Notion 页面即可看到新内容。

---

## 5. 本地调试（可选）

如果想先在本地确认 API 和 Notion 是否可用，可以运行：

```bash
export OPENAI_BASE_URL="https://api.deepseek.com"
export OPENAI_API_KEY="sk-..."
export NOTION_TOKEN="secret_..."
export PAGE_ID="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

python push_summary.py
```

运行成功后，你的 Notion 页面会新增一条总结。

---




