#!/usr/bin/env python3
"""Stdlib compiled-stdio exclusion regression; owned synthetic corpus/provider only."""
import argparse
import contextlib
import hashlib
import http.server
import json
import os
from pathlib import Path
import selectors
import sqlite3
import subprocess
import tempfile
import threading


@contextlib.contextmanager
def native(binary, cwd, env):
    proc = subprocess.Popen([binary], cwd=cwd, env=env, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
    stdin, stdout, stderr = proc.stdin, proc.stdout, proc.stderr
    assert stdin is not None and stdout is not None and stderr is not None
    request_id = 0
    try:
        def rpc(method, params):
            nonlocal request_id
            request_id += 1
            stdin.write(json.dumps({'jsonrpc': '2.0', 'id': request_id,
                                        'method': method, 'params': params}).encode() + b'\n')
            stdin.flush()
            with selectors.DefaultSelector() as selector:
                selector.register(stdout, selectors.EVENT_READ)
                assert selector.select(5), 'compiled stdio response timeout'
                reply = json.loads(stdout.readline())
            assert reply['id'] == request_id, reply
            return reply
        initialized = rpc('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {},
                          'clientInfo': {'name': 'exclusions-smoke', 'version': '1'}})
        assert 'result' in initialized, initialized
        stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        stdin.flush()
        yield lambda name, args=None: rpc('tools/call', {'name': name, 'arguments': args or {}})
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        for stream in (stdin, stdout, stderr):
            stream.close()


def failed(reply):
    return 'error' in reply or bool(reply.get('result', {}).get('isError'))


def decode(reply):
    assert not failed(reply), reply
    return json.loads(reply['result']['content'][0]['text'])


def seed(path):
    with contextlib.closing(sqlite3.connect(path)) as db, db:
        db.executescript("""
            CREATE TABLE skills(id INTEGER PRIMARY KEY,name TEXT,desc TEXT,repo TEXT,
                                path TEXT,url TEXT,tier TEXT,dup_of INTEGER,revision TEXT);
            CREATE TABLE sources(repo TEXT);
            CREATE VIRTUAL TABLE skills_fts USING fts5(name,desc);
            INSERT INTO skills VALUES
              (1,'malicious','PDF PDF PDF','owner/repo','bad/SKILL.md','url','vendor',NULL,'old'),
              (2,'safe','PDF','owner/repo','safe/SKILL.md','url','vendor',NULL,'new'),
              (3,'other','PDF','other/repo','bad/SKILL.md','url','vendor',NULL,'new'),
              (4,'alias-old','PDF','alias/repo','alias/SKILL.md','url','vendor',1,'old'),
              (5,'alias-new','PDF','alias/repo','alias/SKILL.md','url','vendor',3,'new'),
              (6,'malicious-new','PDF PDF PDF','owner/repo','bad/SKILL.md','url','vendor',1,'new');
            INSERT INTO skills_fts(rowid,name,desc) SELECT id,name,desc FROM skills;
        """)


def publish(path, repo, skill):
    # Atomic replacement is the production publication contract; no process restart.
    next_path = path.with_suffix('.next')
    next_path.write_text(json.dumps({'version': 1, 'entries': [{'repo': repo, 'path': skill,
                        'revision': 'a' * 40, 'evidence_id': 'b' * 64, 'reason': 'TEST-ONLY'}]}))
    next_path.replace(path)


@contextlib.contextmanager
def provider(records):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            records.append((self.path, self.headers.get('Authorization'), body))
            good = {'type': 'score', 'score': 2.4, 'confidence': 0.7,
                    'probabilities': {'0': 0.0, '1': 0.1, '2': 0.4, '3': 0.5}}
            data = json.dumps({'model': 'test-resolved',
                               'answers': {key: good for key in body['questions']}}).encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/test-decisions'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not thread.is_alive(), 'owned provider did not stop'


def run(binary):
    binary = str(Path(binary).resolve(strict=True))
    print('ARTIFACT', binary, hashlib.sha256(Path(binary).read_bytes()).hexdigest(), flush=True)
    records = []
    with tempfile.TemporaryDirectory(prefix='jev-exclusions-smoke-') as tmp, provider(records) as endpoint:
        cwd = Path(tmp)
        db, gate, profiles = cwd / 'skills.db', cwd / 'exclusions.json', cwd / 'providers.json'
        seed(db)
        model = '@test/model+revision=2'
        profiles.write_text(json.dumps({'default': 'synthetic', 'profiles': {'synthetic': {
            'endpoint': endpoint, 'model': model, 'key_env': 'TEST_EXCLUSION_KEY'}}}))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('SKILL_ROUTER_', 'JEV_'))}
        env.update(SKILL_ROUTER_DB=str(db), SKILL_ROUTER_EXCLUSIONS=str(gate),
                   SKILL_ROUTER_PROVIDERS_FILE=str(profiles), TEST_EXCLUSION_KEY='test-only-key',
                   TYPESAFE_API_KEY='test-wrong-legacy-key')
        publish(gate, 'owner/repo', 'bad/SKILL.md')
        with native(binary, cwd, env) as tool:
            def search(top=2):
                return decode(tool('skills_search', {'query': 'PDF', 'top': top}))

            def ids(value):
                return [row['id'] for row in value['candidates']]

            filtered = search()
            assert ids(filtered) == [2, 3], ('exact path guard/refill failed', ids(filtered))
            assert ids(search(1)) == [2], 'exclusion must precede top truncation'
            assert filtered['meta']['exclusions']['matched_source_count'] == 2
            assert filtered['meta']['exclusions']['canonical_count'] == 1
            print('PASS exact repo/path across revisions; same-repo safe and other-repo skill retained; top refill', flush=True)
            routed = decode(tool('skills_route', {'project': 'PDF', 'top': 2}))
            assert ids(routed) == [2, 3] and [r['id'] for r in routed['ranked']] == [2, 3]
            assert len(records) == 1, records
            path, bearer, body = records[0]
            assert path == '/test-decisions' and bearer == 'Bearer test-only-key'
            assert body['model'] == model and routed['meta']['provider'] == 'synthetic'
            candidates = [q['instructions']['candidate_skill'] for q in body['questions'].values()]
            assert candidates == [{'name': r['name'], 'description': r['desc'], 'source_repo': r['repo']}
                                  for r in filtered['candidates']], candidates
            print('PASS synthetic native provider receives only permitted candidates; literal model/selected key', flush=True)
            publish(gate, 'alias/repo', 'alias/SKILL.md')
            aliases = search()
            assert ids(aliases) == [2] and aliases['meta']['exclusions']['canonical_count'] == 2
            publish(gate, 'owner/repo', 'safe/SKILL.md')
            assert ids(search(1)) == [1], 'same-process atomic policy replacement not reloaded'
            print('PASS duplicate aliases map to both canonical IDs; atomic per-request reload without restart', flush=True)
            for state in ('corrupt', 'missing'):
                if state == 'corrupt':
                    gate.write_text('{')
                else:
                    gate.unlink()
                # Empty queries must not bypass required policy loading either.
                for query in ('PDF', ''):
                    assert failed(tool('skills_search', {'query': query})), state
                    assert failed(tool('skills_route', {'project': query})), state
                assert decode(tool('skills_stats'))['rows'] == 6
                # Fresh initialization also stays available under a broken required policy.
                with native(binary, cwd, env) as fresh:
                    assert decode(fresh('skills_stats'))['rows'] == 6
                    assert failed(fresh('skills_search', {'query': 'PDF'})), state
                    assert failed(fresh('skills_route', {'project': 'PDF'})), state
                assert len(records) == 1, 'refused route contacted provider'
                print(f'PASS {state} configured policy fails search+route closed; init/stats available; no provider request', flush=True)
            publish(gate, 'owner/repo', 'bad/SKILL.md')
            assert ids(search()) == [2, 3], 'valid atomic policy must recover next request'
    print('PASS all compiled stdio exclusion regressions; owned resources cleaned up', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', help='compiled jev-skill-router executable')
    run(parser.parse_args().binary)
