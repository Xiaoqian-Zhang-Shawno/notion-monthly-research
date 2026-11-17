# Excerpt from a real retrieval run

English | [简体中文](source-preview.md)

Retrieved on **2026-11-17**, with a date window of **2026-10-18 through 2026-11-17**.

These three entries were selected from records actually retrieved and filtered by the project on that date. This is a **retrieval excerpt**, not a model-generated summary or an endorsement of paper quality. Abstract text is omitted from this public example. A normal report additionally includes abstract excerpts, Chinese model observations, and source-status notes.

| Paper | Submission date | Matched topic |
| --- | --- | --- |
| [Learning What Pairs Miss for Higher-Order Multimodal Alignment](https://arxiv.org/abs/2611.21372v1) | 2026-11-16 | multimodal alignment |
| [UniOMA: Unified Optimal-Transport Multi-Modal Structural Alignment for Robot Perception](https://arxiv.org/abs/2611.12351v1) | 2026-11-09 | multimodal alignment |
| [Flow-Guided Target-Space Alignment via Path Consistency](https://arxiv.org/abs/2611.09863v1) | 2026-11-06 | multimodal alignment |

The Semantic Scholar query in the retrieval run used for this excerpt returned no venue records that passed the topic and date filters. This does not establish that no relevant papers existed. Phrase matching, index coverage, dates, and result limits all affect retrieval.

Try a fresh retrieval (results change with the date and index):

```bash
QUERY_KEYWORDS="multimodal alignment" python push_summary.py --fetch-only --output papers.md
```

This contacts public paper sources only. It does not call a model or write to Notion, and needs neither model nor Notion credentials.
