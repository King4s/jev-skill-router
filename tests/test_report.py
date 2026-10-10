"""Routing output stays usable by the existing HTML report on Windows."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPORT = Path(__file__).resolve().parents[1] / "scripts" / "rapport.py"


class ReportCompatibilityTests(unittest.TestCase):
    def test_priority_success_labels_the_preferred_provider_without_claiming_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = {"provider": "both", "status": "complete", "aggregation": "priority_failover",
                    "priority": {"order": ["perplexity", "jev"], "basis": "test", "metrics": {}},
                    "used_providers": ["perplexity"], "providers": {
                        "perplexity": {"status": "complete"}, "jev": {"status": "not_used"}},
                    "ranked": [{"name": "minecraft-modding", "repo": "example/skills", "tier": "community",
                                "score": 2.4, "confidence": 0.8, "aggregation": "single",
                                "confidence_kind": "provider_reported", "used_providers": ["perplexity"]}],
                    "rejected": []}
            (root / "minecraft.json").write_text(json.dumps(data), encoding="utf-8")
            completed = subprocess.run([sys.executable, str(REPORT), "--dir", str(root)],
                                       capture_output=True, encoding="utf-8",
                                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(completed.returncode, 0, completed.stderr)
            rendered = (root / "rapport.html").read_text(encoding="utf-8")
            self.assertIn("Decision maker: perplexity", rendered)
            self.assertNotIn("fallback used", rendered)
            self.assertNotIn("minimum provider confidence", rendered)
            self.assertRegex(rendered.lower(), r"provider.?reported confidence")

    def test_rejected_candidate_does_not_claim_a_fallback_was_used(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = {"provider": "both", "status": "degraded", "used_providers": ["jev", "perplexity"],
                    "ranked": [{"name": "minecraft-modding", "repo": "example/skills", "tier": "community",
                                "score": 2.4, "confidence": 0.8, "aggregation": "equal_mean"}],
                    "rejected": [{"name": "missing", "error": "Neither answer valid"}]}
            (root / "minecraft.json").write_text(json.dumps(data), encoding="utf-8")
            completed = subprocess.run([sys.executable, str(REPORT), "--dir", str(root)],
                                       capture_output=True, encoding="utf-8",
                                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(completed.returncode, 0, completed.stderr)
            rendered = (root / "rapport.html").read_text(encoding="utf-8")
            self.assertNotIn("fallback used", rendered)
            self.assertIn("incomplete provider coverage", rendered)

    def test_degraded_both_ranking_labels_the_actual_provider_and_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = {"project": "Build a dashboard", "provider": "both", "status": "degraded",
                    "used_providers": ["jev"], "providers": {
                        "jev": {"status": "complete"},
                        "perplexity": {"status": "error", "error": "Provider unavailable"}},
                    "ranked": [{"name": "minecraft-modding", "repo": "example/skills", "tier": "community",
                                "score": 2.4, "confidence": 0.8, "confidence_kind": "provider_reported",
                                "used_providers": ["jev"], "aggregation": "single", "score_disagreement": None}],
                    "rejected": []}
            (root / "minecraft.json").write_text(json.dumps(data), encoding="utf-8")
            completed = subprocess.run([sys.executable, str(REPORT), "--dir", str(root)],
                                       capture_output=True, encoding="utf-8",
                                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(completed.returncode, 0, completed.stderr)
            rendered = (root / "rapport.html").read_text(encoding="utf-8")
            self.assertIn("Decision maker: jev", rendered)
            self.assertIn("fallback", rendered.lower())
            self.assertRegex(rendered.lower(), r"provider.?reported confidence")
            self.assertNotIn("confidence is minimum provider confidence", rendered)

    def test_unavailable_both_ranking_does_not_claim_either_provider_was_used(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = {"project": "Build a dashboard", "provider": "both", "status": "unavailable",
                    "used_providers": [], "ranked": [],
                    "providers": {"jev": {"status": "error"}, "perplexity": {"status": "unavailable"}},
                    "rejected": [{"name": "minecraft-modding", "error": "No valid provider answer"}]}
            (root / "minecraft.json").write_text(json.dumps(data), encoding="utf-8")
            completed = subprocess.run([sys.executable, str(REPORT), "--dir", str(root)],
                                       capture_output=True, encoding="utf-8",
                                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(completed.returncode, 0, completed.stderr)
            rendered = (root / "rapport.html").read_text(encoding="utf-8")
            self.assertIn("unavailable", rendered.lower())
            self.assertNotIn("Decision maker: both", rendered)
            self.assertNotIn("confidence is minimum provider confidence", rendered)

    def test_utf8_combined_ranking_keeps_unicode_and_labels_its_provider(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = {"project": "Build a “dashboard”", "provider": "both", "ranked": [
                {"name": "minecraft-modding “guide”", "repo": "example/skills", "tier": "community",
                 "score": 1.5, "confidence": 1.0, "confidence_kind": "minimum_provider_confidence"}],
                "rejected": []}
            (root / "minecraft.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            completed = subprocess.run([sys.executable, "-X", "utf8=0", str(REPORT), "--dir", str(root)],
                                       capture_output=True, encoding="utf-8",
                                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(completed.returncode, 0, completed.stderr)
            html = (root / "rapport.html").read_text(encoding="utf-8")
            self.assertIn("“guide”", html)
            self.assertIn("Decision maker: both", html)
            self.assertIn("minimum provider confidence", html)

    def test_legacy_windows_ranking_is_still_readable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = {"project": "Merge café documents", "ranked": [
                {"name": "café", "repo": "example/skills", "tier": "community", "score": 2.4, "confidence": 0.8}],
                "rejected": []}
            (root / "minecraft.json").write_text(json.dumps(data, ensure_ascii=False), encoding="cp1252")
            completed = subprocess.run([sys.executable, "-X", "utf8=0", str(REPORT), "--dir", str(root)],
                                       capture_output=True, encoding="utf-8",
                                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("café", (root / "rapport.html").read_text(encoding="utf-8"))
