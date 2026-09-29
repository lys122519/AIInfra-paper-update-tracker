import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import main  # noqa: E402
import utils  # noqa: E402


class SmokeModeTests(unittest.TestCase):
    def test_html_verification_page_fails_without_retrying(self):
        response = Mock(
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            text="<!doctype html><title>Making sure you're not a bot!</title>",
        )
        response.raise_for_status.return_value = None

        with patch.object(utils.requests, "get", return_value=response) as get, patch.object(
            utils.time, "sleep"
        ):
            self.assertIsNone(utils.request_data("https://example.invalid", retry=10))

        get.assert_called_once()

    def test_strict_smoke_mode_raises_on_request_failure(self):
        config = {
            "cache_path": ROOT / "tests" / "_unused_cache",
            "dblp": {
                "url": "https://dblp.org/search/publ/api?q={}&format=json&h=1000",
                "keywords": ["GPU cluster"],
                "queries": ["venue:MLSys:"],
                "mails": [],
            },
        }
        with patch.object(main, "init", return_value=config), patch.object(
            main, "request_data", return_value=None
        ):
            with self.assertRaisesRegex(RuntimeError, "DBLP request failed"):
                main.Scaffold().run(
                    env="dev",
                    keyword_limit=1,
                    query_limit=1,
                    max_results=10,
                    dry_run=True,
                    skip_enrichment=True,
                    fail_on_request_error=True,
                )


if __name__ == "__main__":
    unittest.main()
