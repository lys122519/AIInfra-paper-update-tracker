import sys
import unittest
import urllib.parse
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dblp_snapshot import load_snapshot_items_by_topic, title_matches_keyword  # noqa: E402


class DblpSnapshotTests(unittest.TestCase):
    def test_every_configured_query_has_a_key_prefix(self):
        config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
        dblp = config["dblp"]
        self.assertEqual(
            set(dblp["queries"]),
            set(dblp["snapshot"]["query_key_prefixes"]),
        )

    def test_truncated_keyword_tokens_match_title_words(self):
        self.assertTrue(title_matches_keyword("AI Infrastructure Scheduling", "AI schedul"))
        self.assertFalse(title_matches_keyword("Storage Infrastructure Scheduling", "AI schedul"))

    def test_streaming_parser_filters_year_venue_and_keyword(self):
        keywords = ["AI schedul", "RDMA", "Kubernetes"]
        queries = ["venue:MLSys:", "streamid:journals/tpds:"]
        results = load_snapshot_items_by_topic(
            snapshot_path=ROOT / "tests" / "fixtures" / "dblp_sample.xml",
            dtd_path=ROOT / "tests" / "fixtures" / "dblp.dtd",
            keywords=keywords,
            queries=queries,
            query_key_prefixes={
                "venue:MLSys:": "conf/mlsys",
                "streamid:journals/tpds:": "journals/tpds",
            },
            min_year=2025,
            max_year=2026,
        )

        gpu_topic = (
            f"{urllib.parse.quote('AI schedul', safe='')}%20"
            f"{urllib.parse.quote('venue:MLSys:', safe='')}"
        )
        rdma_topic = (
            f"{urllib.parse.quote('RDMA', safe='')}%20"
            f"{urllib.parse.quote('streamid:journals/tpds:', safe='')}"
        )
        self.assertEqual([item["key"] for item in results[gpu_topic]], ["conf/mlsys/Smith26"])
        self.assertIn("Müller", results[gpu_topic][0]["author"])
        self.assertEqual(results[gpu_topic][0]["doi"], "10.1000/gpu.2026")
        self.assertEqual([item["key"] for item in results[rdma_topic]], ["journals/tpds/Jones25"])
        self.assertTrue(all(not values for topic, values in results.items() if topic not in {gpu_topic, rdma_topic}))


if __name__ == "__main__":
    unittest.main()
