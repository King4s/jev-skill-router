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
