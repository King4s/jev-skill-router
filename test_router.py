#!/usr/bin/env python3
"""Offline regression checks for the review findings; all HTTP inputs are synthetic."""
import contextlib
from email.message import Message
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import router


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, router.ROOT / 'scripts' / (name + '.py'))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GOOD = {'type': 'score', 'score': 2.4, 'confidence': 0.7,
        'probabilities': {'0': 0.0, '1': 0.1, '2': 0.4, '3': 0.5}}


class ReviewChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'skills.db'
        self.sources = self.root / 'sources.txt'
        self.sources.write_text('example/repo\n')
        self.index_args = SimpleNamespace(db=str(self.path), sources=str(self.sources), workers=1)
        with sqlite3.connect(self.path) as db:
            db.executescript(router.SCHEMA)
            for i in (1, 2):
                db.execute('INSERT INTO skills(id,name,desc,tags,tier,repo,path,url,fp) VALUES(?,?,?,?,?,?,?,?,?)',
                           (i, 'skill'+str(i), 'Read PDF files', '', 'vendor', 'example/repo',
                            'skills/'+str(i)+'/SKILL.md', 'https://example.invalid/skill', 'fp'+str(i)))
                db.execute('INSERT INTO skills_fts(rowid,name,desc,tags) VALUES(?,?,?,?)',
                           (i, 'skill'+str(i), 'Read PDF files', ''))
            db.execute("INSERT INTO fm(repo,path,sha,name,desc,tags) VALUES('example/repo','SKILL.md','old-sha','cached','Read PDF files','')")
        self.output = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.output)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)

    def snapshot(self):
        with sqlite3.connect(self.path) as db:
            return {table: db.execute('SELECT * FROM '+table).fetchall()
                    for table in ('skills', 'skills_fts', 'fm', 'sources')}

    def route(self, response, top=40):
        out = self.root / 'route.json'
        args = SimpleNamespace(db=str(self.path), project='Read PDF files', top=top,
                               show=25, out=str(out), rule='plain')
        with patch.object(router, 'jev_call', return_value=response) as call:
            result = router.cmd_route(args)
        return result, json.loads(out.read_text()) if out.exists() else None, call

    def test_discovery_failure_preserves_all_published_rows(self):
        before = self.snapshot()
        with patch.object(router, 'gh_api', return_value=None):
            try:
                result = router.cmd_index(self.index_args)
            except (RuntimeError, ValueError):
                result = 1
        self.assertNotEqual(result, 0)
        self.assertEqual(self.snapshot(), before)

    def test_changed_blob_fetch_failure_preserves_index_and_cache(self):
        before = self.snapshot()
        with patch.object(router, 'list_skill_paths', return_value=('main', [('SKILL.md', 'new-sha')], 1)), \
             patch.object(router, 'fetch_head', return_value=None):
            try:
                result = router.cmd_index(self.index_args)
            except (RuntimeError, ValueError):
                result = 1
        self.assertNotEqual(result, 0)
        self.assertEqual(self.snapshot(), before)

    def test_truncated_tree_is_not_complete_discovery(self):
        with patch.object(router, 'gh_api', side_effect=[
                {'default_branch': 'main', 'stargazers_count': 1},
                {'sha': 'pinned-commit'},
                {'truncated': True, 'tree': []}]):
            with self.assertRaises((RuntimeError, ValueError)):
                router.list_skill_paths('example/repo')

    def test_successful_refresh_removes_confirmed_deletions(self):
        with patch.object(router, 'list_skill_paths', return_value=('main', [('SKILL.md', 'new-sha')], 1)), \
             patch.object(router, 'fetch_head', return_value='---\nname: new\ndescription: Read PDFs\n---\n'):
            self.assertEqual(router.cmd_index(self.index_args), 0)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT name FROM skills').fetchall(), [('new',)])
            self.assertEqual(db.execute('SELECT name FROM skills_fts').fetchall(), [('new',)])
            self.assertEqual(db.execute('SELECT sha FROM fm').fetchall(), [('new-sha',)])

    def test_publish_error_rolls_back_all_derived_rows(self):
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TRIGGER fail_publish BEFORE INSERT ON skills WHEN NEW.name='new' BEGIN SELECT RAISE(ABORT,'offline publication failure'); END")
        before = self.snapshot()
        with patch.object(router, 'list_skill_paths', return_value=('main', [('SKILL.md', 'new-sha')], 1)), \
             patch.object(router, 'fetch_head', return_value='---\nname: new\ndescription: Read PDFs\n---\n'):
            with self.assertRaises(sqlite3.DatabaseError):
                router.cmd_index(self.index_args)
        self.assertEqual(self.snapshot(), before)

    def test_parse_failure_preserves_published_rows(self):
        before = self.snapshot()
        with patch.object(router, 'list_skill_paths', return_value=('main', [('SKILL.md', 'new-sha')], 1)), \
             patch.object(router, 'fetch_head', return_value='---\nname: new\ndescription: [unsupported, structure]\n---\n'):
            self.assertEqual(router.cmd_index(self.index_args), 1)
        self.assertEqual(self.snapshot(), before)

    def test_missing_metadata_is_explicitly_accounted(self):
        with patch.object(router, 'list_skill_paths', return_value=('main', [('SKILL.md', 'new-sha')], 1)), \
             patch.object(router, 'fetch_head', return_value='---\nname: missing-description\n---\n'):
            self.assertEqual(router.cmd_index(self.index_args), 0)
        with sqlite3.connect(self.path) as db:
            coverage = json.loads(db.execute("SELECT value FROM index_meta WHERE key='coverage'").fetchone()[0])
            self.assertEqual(coverage['discovered'], 1)
            self.assertEqual(coverage['missing_metadata'], 1)
            self.assertEqual(coverage['fetch_failed'], 0)
            self.assertEqual(coverage['parse_failed'], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM skills').fetchone()[0], 0)

    def test_validator_rejects_malformed_shapes_and_values_without_exception(self):
        self.assertIsNone(router.validate_score(GOOD, 4))
        bad = [None, [], 'not an object', {},
               {**GOOD, 'score': True}, {**GOOD, 'confidence': False},
               {**GOOD, 'score': 0}, {**GOOD, 'score': '2.4'},
               {**GOOD, 'probabilities': ['0', '1', '2', '3']},
               {**GOOD, 'probabilities': {'0': 'bad', '1': 0.1, '2': 0.4, '3': 0.5}},
               {**GOOD, 'probabilities': {'0': False, '1': 0.1, '2': 0.4, '3': 0.5}},
               {**GOOD, 'probabilities': {'0': float('nan'), '1': 0.1, '2': 0.4, '3': 0.5}}]
        for value in bad:
            with self.subTest(value=value):
                self.assertIsNotNone(router.validate_score(value, 4))

    def test_no_valid_answers_returns_failure_and_artifact(self):
        for response in ({'answers': {}}, {'answers': None}, [], None):
            with self.subTest(response=response):
                result, data, _ = self.route(response)
                self.assertNotEqual(result, 0)
                assert data is not None
                self.assertEqual(len(data['rejected']), 2)
                self.assertEqual(data['ranked'], [])

    def test_partial_artifact_preserves_candidate_and_run_provenance(self):
        result, data, _ = self.route({'model': 'offline-model', 'answers': {'skill_000': GOOD}})
        self.assertEqual(result, 0)
        assert data is not None
        self.assertTrue(data['degraded'])
        self.assertEqual(len(data['candidates']), 2)
        self.assertEqual(len(data['ranked']) + len(data['rejected']), len(data['candidates']))
        self.assertEqual(data['meta']['top'], 40)
        self.assertEqual(data['meta']['rule'], 'plain')
        self.assertEqual(data['meta']['model'], 'offline-model')
        self.assertEqual(data['meta']['corpus']['unique'], 2)
        self.assertGreaterEqual(data['meta']['latency_s'], 0)
        self.assertTrue(data['meta']['corpus']['identity'])

    def test_eval_gate_checks_active_default_not_best_experiment(self):
        ev = load_script('eval_shortlist')
        with patch.object(sys, 'argv', ['eval', '--db', str(self.path), '--require', '13']), \
             patch.object(ev, 'run', side_effect=lambda db, rule, top, show: 13 if rule == 'pool' else 11):
            self.assertEqual(ev.main(), 1)

    def test_zero_frequency_rules_do_not_divide_by_zero(self):
        for populated in (False, True):
            db = sqlite3.connect(self.path if populated else ':memory:')
            self.addCleanup(db.close)
            if not populated:
                db.executescript(router.SCHEMA)
            for rule in ('plain', 'bm25', 'pool', 'hybrid', 'idf'):
                with self.subTest(populated=populated, rule=rule):
                    self.assertEqual(router.shortlist(db, 'zzzznonexistenttoken', 40, rule), [])

    def test_invalid_top_is_rejected_before_inference(self):
        for top in (-1, 0, 1000000):
            with patch.object(router, 'jev_call') as call:
                with self.subTest(top=top):
                    args = SimpleNamespace(db=str(self.path), project='PDF', top=top, show=25, out=None, rule='plain')
                    try:
                        result = router.cmd_route(args)
                    except (ValueError, SystemExit):
                        result = 1
                    self.assertNotEqual(result, 0)
                    call.assert_not_called()

    def test_http_permanent_failure_attempted_once(self):
        for code in (401, 422):
            with self.subTest(code=code), patch.object(router, 'jev_key', return_value='offline-key'), \
                 patch.object(router.urllib.request, 'urlopen', side_effect=HTTPError(router.JEV_API, code, 'offline', Message(), io.BytesIO(b'{}'))) as call:
                with self.assertRaises(RuntimeError):
                    router.jev_call({}, {}, retries=3)
                self.assertEqual(call.call_count, 1)

    def test_http_overload_retries_with_backoff(self):
        for code in (429, 529):
            response = contextlib.nullcontext(io.BytesIO(b'{"answers":{}}'))
            headers = Message()
            headers['Retry-After'] = '1'
            with self.subTest(code=code), patch.object(router, 'jev_key', return_value='offline-key'), \
                 patch.object(router.urllib.request, 'urlopen', side_effect=[HTTPError(router.JEV_API, code, 'offline', headers, io.BytesIO(b'{}')), response]) as call, \
                 patch('time.sleep') as sleep:
                self.assertEqual(router.jev_call({}, {}), {'answers': {}})
                self.assertEqual(call.call_count, 2)
                sleep.assert_called_once()
                self.assertGreaterEqual(sleep.call_args.args[0], 1)

    def test_fingerprint_preserves_unicode_and_language_punctuation(self):
        self.assertNotEqual(router.fingerprint('数学', '计算与证明'), router.fingerprint('音乐', '演奏与作曲'))
        self.assertNotEqual(router.fingerprint('C', 'Development'), router.fingerprint('C++', 'Development'))
        self.assertEqual(router.fingerprint('PDF', 'Read PDFs.'), router.fingerprint('pdf', 'read  pdfs'))

    def test_quoted_yaml_markers_are_literals_not_structure(self):
        for value in ('[experimental] files', '!important files', '&anchor', '*alias', '{mapping}', '>', '|'):
            for quoted in (json.dumps(value), "'" + value + "'"):
                with self.subTest(quoted=quoted):
                    data = router.parse_frontmatter('---\nname: sample\ndescription: '+quoted+'\n---\n')
                    self.assertEqual(data['description'], value)
        for raw in ('[array]', '!tag value', '&anchor value', '*alias', '{key: value}'):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    router.parse_frontmatter('---\nname: sample\ndescription: '+raw+'\n---\n')

    def test_scalar_and_block_yaml_inline_comments(self):
        for desc in ('"A useful skill" # comment', '> # comment\n  A useful skill'):
            data = router.parse_frontmatter('---\nname: sample # comment\ndescription: '+desc+'\n---\n')
            self.assertEqual(data['name'], 'sample')
            self.assertEqual(data['description'], 'A useful skill')

    def test_fetch_reads_complete_frontmatter_beyond_four_kib(self):
        text = '---\nname: sample\ndescription: '+('a'*5000)+'\n---\n# Body'
        with patch.object(router.urllib.request, 'urlopen', return_value=contextlib.nullcontext(io.BytesIO(text.encode()))):
            result = router.fetch_head('example/repo', 'revision', 'space dir/SKILL.md')
        assert result is not None
        self.assertEqual(router.parse_frontmatter(result)['name'], 'sample')
        self.assertEqual(len(router.parse_frontmatter(result)['description']), 5000)

    def test_report_separates_retrieval_from_validation_and_uses_metadata(self):
        report = load_script('rapport')
        fixture = {'project': 'offline', 'candidates': [{'name': 'wanted'}], 'ranked': [],
                   'rejected': [{'name': 'wanted', 'error': 'offline malformed answer'}],
                   'meta': {'top': 7, 'rule': 'plain', 'model': 'offline-model', 'latency_s': 1.23,
                            'corpus': {'unique': 2, 'sources': 1, 'identity': 'offline-snapshot'}}}
        (self.root / 'sample.json').write_text(json.dumps(fixture))
        with patch.object(report, 'FACIT', {'sample': (['wanted'], 'Offline fixture')}), \
             patch.object(sys, 'argv', ['rapport', '--dir', str(self.root)]):
            self.assertEqual(report.main(), 0)
        html = (self.root / 'rapport.html').read_text()
        self.assertIn('1/1', html)
        self.assertIn('7', html)
        self.assertIn('1.23', html)
        self.assertNotIn('top 40', html)
        self.assertNotIn('10,656', html)
        self.assertNotIn('0.5 s', html)

    def test_legacy_report_marks_provenance_unknown(self):
        report = load_script('rapport')
        (self.root / 'sample.json').write_text(json.dumps({'ranked': [], 'rejected': []}))
        with patch.object(report, 'FACIT', {'sample': (['wanted'], 'Legacy fixture')}), \
             patch.object(sys, 'argv', ['rapport', '--dir', str(self.root)]):
            self.assertEqual(report.main(), 0)
        html = (self.root / 'rapport.html').read_text().lower()
        self.assertIn('unknown', html)
        self.assertNotIn('10,656', html)
        self.assertNotIn('0.5 s', html)


if __name__ == '__main__':
    unittest.main()
