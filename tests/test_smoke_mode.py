import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import main  # noqa: E402
import utils  # noqa: E402


class SmokeModeTests(unittest.TestCase):
    def test_removed_api_source_is_rejected(self):
        config = {
            "cache_path": ROOT / "tests" / "_unused_cache",
            "dblp": {
                "source": "api",
                "keywords": ["AI infrastructure"],
                "queries": ["venue:MLSys:"],
                "mails": [],
            },
        }
        with patch.object(main, "init", return_value=config):
            with self.assertRaisesRegex(ValueError, "only `snapshot` is supported"):
                main.Scaffold().run(env="dev", dry_run=True, skip_enrichment=True)

    def test_configured_keywords_support_legacy_and_string_forms(self):
        self.assertEqual(
            utils.get_configured_keywords({"dblp": {"keywords": [" a ", "", None, "b"]}}),
            ["a", "b"],
        )
        self.assertEqual(utils.get_configured_keywords({"dblp": {"keywords": "solo"}}), ["solo"])
        self.assertEqual(utils.get_configured_keywords({"dblp": {"keyword": "legacy"}}), ["legacy"])
        self.assertEqual(utils.get_configured_keywords({"dblp": {}}), [])
        self.assertEqual(
            utils.get_configured_topics({"dblp": {"keyword": "AI infra", "queries": ["venue:MLSys:"]}}),
            {"AI%20infra%20venue%3AMLSys%3A"},
        )

    def test_get_msg_uses_escaped_newlines_for_github_env(self):
        items = [
            {"title": "Paper A", "ee": "https://doi.org/10.1/a", "related_code": "https://github.com/u/r"},
            {"title": "Paper B", "ee": ""},
        ]
        msg = utils.get_msg(items, "AI%20infrastructure%20venue%3AMLSys%3A")
        self.assertNotIn("\n", msg)
        self.assertTrue(msg.startswith("## [MLSys](https://dblp.org/search?q="))
        self.assertIn("[+2]", msg)
        self.assertIn("- Paper A. [[PUB](https://doi.org/10.1/a)] [[CODE](https://github.com/u/r)]\\n", msg)
        self.assertIn("- Paper B.\\n", msg)


if __name__ == "__main__":
    unittest.main()
