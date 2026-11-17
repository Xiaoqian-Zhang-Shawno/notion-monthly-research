import importlib.util
import os
from pathlib import Path
import unittest
from datetime import datetime
from unittest.mock import Mock, patch
from xml.sax.saxutils import escape

os.environ.setdefault("OPENAI_API_KEY", "unused-test-key")
os.environ.setdefault("NOTION_TOKEN", "unused-test-token")
os.environ.setdefault("PAGE_ID", "unused-test-page")
spec = importlib.util.spec_from_file_location("summary", Path(__file__).parents[1] / "push_summary.py")
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.topic = patch.object(summary, "QUERY_KEYWORDS", "multimodal alignment, CT")
        dates = patch.multiple(summary, today=datetime(2026, 11, 17), past_date="2026-10-18", today_fmt="2026年11月")
        dates.start()
        self.addCleanup(dates.stop)
        self.topic.start()
        self.addCleanup(self.topic.stop)

    def test_word_boundaries_and_hyphens(self):
        self.assertEqual(summary.matched_keywords("Activity in quantum dots", ""), [])
        self.assertEqual(summary.matched_keywords("CT reconstruction", ""), ["ct"])
        self.assertEqual(summary.matched_keywords("Alignment", "multimodal-alignment methods"), ["multimodal alignment"])

    def test_arxiv_filters_unrelated_old_future_and_duplicate_records(self):
        entries = []
        rows = [
            ("1v1", "Activity in quantum dots", "", "2026-11-16"),
            ("2v1", "Multimodal alignment", "multimodal alignment evidence", "2026-11-16"),
            ("2v2", "Multimodal alignment", "", "2026-11-16"),
            ("3v1", "CT reconstruction", "", "2020-01-01"),
            ("4v1", "CT reconstruction", "", "2099-01-01"),
        ]
        for identifier, title, abstract, date in rows:
            entries.append(f'<entry><id>https://arxiv.org/abs/{identifier}</id><title>{escape(title)}</title><summary>{escape(abstract)}</summary><published>{date}T00:00:00Z</published><link href="https://arxiv.org/abs/{identifier}"/></entry>')
        response = Mock(content=('<feed xmlns="http://www.w3.org/2005/Atom">' + "".join(entries) + '</feed>').encode())
        with patch.object(summary.requests, "get", return_value=response) as get:
            papers = summary.fetch_arxiv_papers(10)
        self.assertEqual(len(papers), 1)
        self.assertIn("evidence", papers[0])
        query = get.call_args.kwargs["params"]["search_query"]
        self.assertIn('(ti:"multimodal alignment" OR abs:"multimodal alignment")', query)
        self.assertIn('(ti:"ct" OR abs:"ct")', query)
        self.assertIn("AND submittedDate:[", query)

    def test_semantic_scholar_uses_topic_venue_date_filters_and_one_request(self):
        response = Mock()
        response.json.return_value = {"data": [
            {"paperId": "1", "title": "Unrelated physics", "abstract": "", "venue": "NeurIPS", "publicationDate": "2026-11-16", "url": "https://example.org/1"},
            {"paperId": "2", "title": "Multimodal alignment", "abstract": "Evidence", "venue": "NeurIPS", "publicationDate": "2026-11-16", "url": "https://example.org/2"},
            {"paperId": "3", "title": "Multimodal alignment", "abstract": "", "venue": "NeurIPS", "publicationDate": None, "url": "https://example.org/3"},
        ], "token": "next"}
        with patch.object(summary.requests, "get", return_value=response) as get:
            papers = summary.fetch_ccf_a_papers(max_total=1)
        self.assertEqual(get.call_count, 1)
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["query"], '"multimodal alignment" | "ct"')
        self.assertIn("venue", params)
        self.assertIn("publicationDateOrYear", params)
        self.assertIn("example.org/2", papers[0])
        self.assertIn("首批", papers[-1])

    def test_rate_limit_is_preserved_in_report(self):
        response = Mock(status_code=429)
        response.raise_for_status.side_effect = summary.requests.HTTPError(response=response)
        with patch.object(summary.requests, "get", return_value=response):
            warning = summary.fetch_ccf_a_papers()
        model = Mock()
        model.chat.completions.create.return_value.choices = [Mock(message=Mock(content="- 观察"))]
        paper = "- [2026-11-16] Multimodal alignment (https://arxiv.org/abs/1234.5678)"
        with patch.object(summary, "client", model):
            report = summary.generate_summary_from_papers([paper], warning)
        self.assertIn(paper, report)
        self.assertIn(warning[0], report)
        self.assertIn("检索不完整", report)


if __name__ == "__main__":
    unittest.main()
