import importlib.util
import os
from pathlib import Path
import tempfile
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
        response = Mock(status_code=200, content=('<feed xmlns="http://www.w3.org/2005/Atom">' + "".join(entries) + '</feed>').encode())
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

    def test_arxiv_rate_limit_respects_retry_after(self):
        limited = Mock(status_code=429, headers={"Retry-After": "7"})
        ok = Mock(status_code=200, content=b'<feed xmlns="http://www.w3.org/2005/Atom"></feed>')
        with patch.object(summary.requests, "get", side_effect=[limited, ok]), patch.object(summary.time, "sleep") as sleep:
            self.assertEqual(summary.fetch_arxiv_papers(), [])
        sleep.assert_called_once_with(7)

    def test_no_summary_when_both_sources_lack_records(self):
        with patch.object(summary, "fetch_arxiv_papers", side_effect=summary.requests.Timeout), patch.object(summary, "fetch_arxiv_search_papers", side_effect=summary.requests.Timeout), patch.object(summary, "fetch_ccf_a_papers", return_value=["- unavailable"]), patch.object(summary, "generate_summary_from_papers") as generate:
            with self.assertRaises(RuntimeError):
                summary.main([])
        generate.assert_not_called()

    def test_rate_limit_is_preserved_in_report(self):
        response = Mock(status_code=429)
        response.raise_for_status.side_effect = summary.requests.HTTPError(response=response)
        with patch.object(summary.requests, "get", return_value=response):
            warning = summary.fetch_ccf_a_papers()
        model = Mock()
        model.chat.completions.create.return_value.choices = [Mock(message=Mock(status_code=200, content="- 观察"))]
        paper = "- [2026-11-16] Multimodal alignment (https://arxiv.org/abs/1234.5678)"
        with patch.object(summary, "client", model):
            report = summary.generate_summary_from_papers([paper], warning)
        self.assertIn(paper, report)
        self.assertIn(warning[0], report)
        self.assertIn("检索不完整", report)

    def test_search_page_preserves_full_abstract_and_filters_dates(self):
        html = """<li class="arxiv-result">
        <p class="list-title"><a href="https://arxiv.org/abs/2611.12345">arXiv</a></p>
        <p class="title">Testing <span>multimodal</span> alignment</p>
        <span class="abstract-full">Full abstract evidence.<a>Less</a></span>
        <p>Submitted 16 November, 2026;</p></li>"""
        papers = summary.parse_arxiv_search(html, 12)
        self.assertEqual(len(papers), 1)
        self.assertIn("Full abstract evidence.", papers[0])
        self.assertNotIn("Less", papers[0])
        self.assertEqual(summary.parse_arxiv_search(html.replace("2026;", "2020;"), 12), [])
        with self.assertRaises(RuntimeError):
            summary.parse_arxiv_search("<html>Access denied</html>", 12)

    def test_fetch_only_needs_no_keys_and_never_calls_model_or_notion(self):
        paper = "### [Multimodal alignment](https://arxiv.org/abs/2611.12345)"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "papers.md"
            with patch.multiple(summary, DEEPSEEK_API_KEY=None, NOTION_TOKEN=None, PAGE_ID=None), patch.object(summary, "fetch_arxiv_papers", return_value=[paper]), patch.object(summary, "fetch_ccf_a_papers", return_value=[]), patch.object(summary, "generate_summary_from_papers") as generate, patch.object(summary, "notion_append_blocks") as publish:
                summary.main(["--fetch-only", "--output", str(output)])
            self.assertIn(paper, output.read_text())
            generate.assert_not_called()
            publish.assert_not_called()

    def test_dry_run_generates_without_notion_credentials_or_writes(self):
        with patch.multiple(summary, NOTION_TOKEN=None, PAGE_ID=None), patch.object(summary, "fetch_arxiv_papers", return_value=["https://arxiv.org/abs/2611.12345"]), patch.object(summary, "fetch_ccf_a_papers", return_value=[]), patch.object(summary, "generate_summary_from_papers", return_value="# report") as generate, patch.object(summary, "notion_append_blocks") as publish:
            summary.main(["--dry-run"])
        generate.assert_called_once()
        publish.assert_not_called()

    def test_notion_links_formatting_and_long_lines(self):
        blocks = summary.markdown_to_notion_blocks("### [A paper](https://arxiv.org/abs/2611.12345)\n\n**Evidence** and " + chr(96) + "code" + chr(96))
        self.assertEqual(blocks[0]["heading_3"]["rich_text"][0]["text"]["link"]["url"], "https://arxiv.org/abs/2611.12345")
        self.assertTrue(blocks[1]["paragraph"]["rich_text"][0]["annotations"]["bold"])
        long_blocks = summary.build_text_blocks("paragraph", "x" * 5000)
        self.assertEqual(sum(len(item["text"]["content"]) for b in long_blocks for item in b["paragraph"]["rich_text"]), 5000)
        self.assertTrue(all(len(item["text"]["content"]) <= 1800 for b in long_blocks for item in b["paragraph"]["rich_text"]))

    def test_notion_batches_and_ambiguous_failure(self):
        ok = Mock(status_code=200)
        with patch.object(summary.requests, "patch", return_value=ok) as request:
            summary.notion_append_blocks("test", [{"type": "paragraph"}] * 101)
        self.assertEqual([len(call.kwargs["json"]["children"]) for call in request.call_args_list], [100, 1])
        with patch.object(summary.requests, "patch", return_value=Mock(status_code=500)) as request:
            with self.assertRaises(RuntimeError):
                summary.notion_append_blocks("test", [{"type": "paragraph"}])
        self.assertEqual(request.call_count, 1)


if __name__ == "__main__":
    unittest.main()
