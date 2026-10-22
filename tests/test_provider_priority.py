"""Offline regression coverage for provider priority evidence and validation."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from decision_providers import ProviderError
from provider_priority import provider_order


class ProviderPriorityTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "priority.json"
        self.models = {"jev": "jev-test", "perplexity": "pplx-test"}
        self.profile = {
            "schema_version": 1,
            "source": "Offline test measurements",
            "providers": {
                "jev": {"models": ["jev-test"], "accuracy": 0.96,
                        "cost_per_candidate_usd": 0.01},
                "perplexity": {"models": ["pplx-test"], "accuracy": 0.94,
                               "cost_per_candidate_usd": 0.001},
            },
        }

    def order(self):
        self.path.write_text(json.dumps(self.profile), encoding="utf-8")
        return provider_order(self.models, profile_path=self.path)

    def test_measured_basis_when_both_providers_have_matching_accuracy(self):
        result = self.order()
        self.assertEqual(result["basis"], "measured_accuracy_then_measured_cost")

    def test_incomplete_basis_when_only_one_provider_has_matching_accuracy(self):
        self.models["perplexity"] = "custom-model"
        result = self.order()
        self.assertEqual(result["basis"], "provisional_order_incomplete_quality_evidence")

    def test_unavailable_basis_when_neither_provider_has_accuracy(self):
        for record in self.profile["providers"].values():
            record["accuracy"] = None
        result = self.order()
        self.assertEqual(result["basis"], "provisional_order_quality_unavailable")

    def test_profile_size_limit_when_file_exceeds_64_kib(self):
        content = json.dumps(self.profile).encode("utf-8")
        self.path.write_bytes(content + b" " * (65536 - len(content)))
        self.assertEqual(self.path.stat().st_size, 65536)
        self.assertEqual(provider_order(self.models, profile_path=self.path)["order"],
                         ["jev", "perplexity"])
        with self.path.open("ab") as profile_file:
            profile_file.write(b" ")
        self.assertEqual(self.path.stat().st_size, 65537)
        with self.assertRaisesRegex(ProviderError, "exceeds 64 KiB"):
            provider_order(self.models, profile_path=self.path)

    def test_source_rejected_when_not_a_string(self):
        for source in (None, 42, True, [], {}):
            with self.subTest(source=source):
                self.profile["source"] = source
                with self.assertRaisesRegex(ProviderError, "Invalid priority profile source"):
                    self.order()

    def test_source_rejected_when_longer_than_500_characters(self):
        self.profile["source"] = "s" * 501
        with self.assertRaisesRegex(ProviderError, "Invalid priority profile source"):
            self.order()

    def test_source_accepted_when_exactly_500_characters(self):
        self.profile["source"] = "s" * 500
        self.assertEqual(self.order()["source"], "s" * 500)

    def test_missing_provider_metrics_when_profile_lists_only_jev(self):
        del self.profile["providers"]["perplexity"]
        result = self.order()
        self.assertEqual(result["order"], ["jev", "perplexity"])
        self.assertIsNone(result["metrics"]["perplexity"]["accuracy"])
        self.assertIs(result["metrics"]["perplexity"]["model_matches"], False)


if __name__ == "__main__":
    unittest.main()
