# 一次真实检索的输出节选

[English](source-preview.en.md) | 简体中文

检索日期：2026-11-17。日期窗口：2026-10-18 至 2026-11-17。

下面三条选自本项目当日实际抓取并筛选的结果，用于展示标题、日期、命中主题和可点击来源。它们是**检索输出节选，不是模型总结或论文质量推荐**。为避免在公开示例中大段转载摘要，这里省略摘要原文。正常运行的报告还包括摘要摘录、模型样本观察和数据源状态。

| 论文 | 提交日期 | 命中主题 |
| --- | --- | --- |
| [Learning What Pairs Miss for Higher-Order Multimodal Alignment](https://arxiv.org/abs/2611.21372v1) | 2026-11-16 | multimodal alignment |
| [UniOMA: Unified Optimal-Transport Multi-Modal Structural Alignment for Robot Perception](https://arxiv.org/abs/2611.12351v1) | 2026-11-09 | multimodal alignment |
| [Flow-Guided Target-Space Alignment via Path Consistency](https://arxiv.org/abs/2611.09863v1) | 2026-11-06 | multimodal alignment |

这次 Semantic Scholar 查询没有返回通过主题和日期筛选的会场论文。它不证明该时间段没有相关论文。关键词采用短语匹配，不能保证结果都符合个人研究目标；日期、会场索引和返回数量也会影响覆盖率。

自己复现一次检索（结果会随日期和索引更新）：

```bash
QUERY_KEYWORDS="multimodal alignment" python push_summary.py --fetch-only --output papers.md
```

此命令只请求公开论文源，不调用模型，不写入 Notion，也不需要模型或 Notion 密钥。
