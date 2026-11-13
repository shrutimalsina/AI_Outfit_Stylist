import unittest

from backend.app.evaluation.metrics import summarize
from pipeline.run_evaluation import evaluate
import test_ranking


class EvaluationTest(unittest.TestCase):
    def test_metrics(self):
        self.assertEqual(summarize([1, 2, None]), {
            "recall_at_1": 1 / 3, "recall_at_3": 2 / 3, "mrr_at_3": 0.5,
        })
        self.assertIsNone(summarize([])["recall_at_3"])

    def test_shared_engine_and_seeded_baseline(self):
        fixture = test_ranking.RankingTest()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        manifest = {"outfits": [
            {"id": "held-out", "split": "test", "item_ids": ["query", "b", "shoe", "missing"]},
            {"id": "development", "split": "valid", "item_ids": ["query", "a"]},
        ]}
        report = evaluate(fixture.catalog, manifest, "test")
        self.assertEqual(report, evaluate(fixture.catalog, manifest, "test"))
        self.assertEqual(report["eligible_cases"], 6)
        self.assertEqual(report["excluded_cases"], 6)
        self.assertEqual(report["clip"]["recall_at_3"], 5 / 6)
        self.assertEqual(len(report["random"]["recall_at_3_by_seed"]), 100)
        self.assertEqual(report["evaluated_outfits"], 1)
