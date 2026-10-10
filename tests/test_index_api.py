"""GitHub's UTF-8 JSON must survive a Windows legacy text encoding."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import router


class GitHubIndexEncodingTests(unittest.TestCase):
    def test_non_ascii_skill_paths_are_read_as_utf8(self):
        expected = {"tree": [{"path": "ā/SKILL.md", "type": "blob"}]}
        payload = json.dumps(expected, ensure_ascii=False).encode("utf-8")
        real_run = subprocess.run
        def github_fixture(arguments, **options):
            # Emulate the default Windows code page unless the client chose UTF-8.
            options.setdefault("encoding", "cp1252")
            return real_run([sys.executable, "-c", f"import sys; sys.stdout.buffer.write({payload!r})"], **options)
        with patch.object(router.subprocess, "run", side_effect=github_fixture):
            result = router.gh_api("repos/example/skills/git/trees/main?recursive=1")
        self.assertEqual(result, expected)
