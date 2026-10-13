#!/usr/bin/env python3
"""Native provider wire regressions. All keys, skills and replies are synthesized
TEST-ONLY fixtures; listeners are owned loopback servers, never paid APIs.
Requires only stdlib plus the existing mcp_smoke/router dependencies.
"""
import argparse
import concurrent.futures as cf
import contextlib
from email.utils import formatdate
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
import time

from mcp_smoke import (GOOD, INIT, HttpClient, decode_tool, failed, free_port,
                       payload, router, wait_ready)

TOKEN = 'test-only-mcp-token-01234567890123456789'
KEYS = {'jev': 'test-only-jev-key', 'perplexity': 'test-only-pplx-key',
        'custom': 'test-only-custom-key'}
KEY_ENVS = {'jev': 'TEST_JEV_KEY', 'perplexity': 'PERPLEXITY_API_KEY',
            'custom': 'TEST_CUSTOM_KEY'}


def stop(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait(timeout=3)
    for stream in (proc.stdin, proc.stdout, proc.stderr):
        if stream:
            stream.close()


@contextlib.contextmanager
def fixture_server(label, records, plan):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers['Content-Length']))
            body = json.loads(raw)
            records.append({'server': label, 'path': self.path, 'body': body,
                            'bearer': self.headers.get('Authorization'), 'bytes': len(raw)})
            answers = {key: json.loads(json.dumps(GOOD)) for key in body['questions']}
            mode = plan.get('mode', 'good')
            index = len(records) - 1
            status, headers = 200, {}
            value = {'model': plan.get('models', ['test-resolved'])[index % len(plan.get('models', ['test-resolved']))],
                     'answers': answers}
            if mode == 'unknown' and index == 1:
                answers['unknown'] = GOOD
            if mode == 'missing':
                answers.pop(next(iter(answers)))
            if mode == 'invalid':
                answers[next(iter(answers))] = plan['answer']
            if mode == 'redirect':
                status, headers = 307, {'Location': plan['location']}
            if mode == 'retry-after':
                status, headers = 429, {'Retry-After': plan['delay']}
                value = {'private': 'test-only-private-provider-body'}
            data = json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            for key, val in headers.items():
                self.send_header(key, val)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                self.wfile.write(data)

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/{label}/decisions'
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
        assert not thread.is_alive(), 'owned provider listener did not stop'


@contextlib.contextmanager
def native(binary, cwd, env, stdio=False):
    proc = subprocess.Popen([binary] + ([] if stdio else ['--http']), cwd=cwd, env=env,
                            stdin=subprocess.PIPE if stdio else subprocess.DEVNULL,
                            stdout=subprocess.PIPE if stdio else subprocess.DEVNULL,
                            stderr=subprocess.PIPE, bufsize=0)
    try:
        if stdio:
            assert proc.stdin is not None and proc.stdout is not None
            def rpc(method, params=None):
                proc.stdin.write(json.dumps(payload(method, params)).encode() + b'\n')
                proc.stdin.flush()
                with selectors.DefaultSelector() as sel:
                    sel.register(proc.stdout, selectors.EVENT_READ)
                    assert sel.select(3), 'native stdio response timeout'
                    return json.loads(proc.stdout.readline())
            rpc('initialize', INIT)
            proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
            proc.stdin.flush()
            yield lambda name, args=None: rpc('tools/call', {'name': name, 'arguments': args or {}})
        else:
            port = int(env['SKILL_ROUTER_BIND'].rsplit(':', 1)[1])
            wait_ready(proc, port)
            client = HttpClient(f'http://127.0.0.1:{port}/mcp', TOKEN)
            client.rpc('initialize', INIT)
            # Bound refusal checks independently of the production 180s deadline.
            def tool(name, args=None):
                with cf.ThreadPoolExecutor(max_workers=1) as pool:
                    pending = pool.submit(client.tool, name, args)
                    try:
                        return pending.result(timeout=3)
                    except cf.TimeoutError:
                        stop(proc)
                        raise AssertionError('native wire call exceeded 3s (unexpected sleep/retry)') from None
            yield tool
    finally:
        stop(proc)


def seed(path):
    with sqlite3.connect(path) as db:
        db.executescript(router.SCHEMA)
        for i in range(1, 301):
            name, desc = f'test-skill-{i:03}', 'Read PDF files'
            db.execute('INSERT INTO skills(id,name,desc,tags,tier,repo,url) VALUES(?,?,?,?,?,?,?)',
                       (i, name, desc, '', 'vendor', 'test-only/repo', 'https://example.invalid/test-only'))
            db.execute('INSERT INTO skills_fts(rowid,name,desc,tags) VALUES(?,?,?,?)', (i, name, desc, ''))


def coverage(value):
    candidates = value['candidates']
    rows = value['ranked'] + value['rejected']
    assert len(rows) == len(candidates)
    assert len({r['id'] for r in rows}) == len(candidates)
    assert {r['id'] for r in rows} == {r['id'] for r in candidates}
    assert [r['id'] for r in value['ranked']] == [r['id'] for r in candidates if r['id'] not in {r['id'] for r in value['rejected']}], 'equal-score ties lost shortlist order'


def wire(records, provider, endpoint, model, candidates):
    from urllib.parse import urlsplit
    assert records and all(r['server'] == provider and r['path'] == urlsplit(endpoint).path
                           and r['bearer'] == 'Bearer ' + KEYS[provider]
                           and r['body']['model'] == model for r in records), (
        'selected provider/key/model/endpoint mismatch',
        [{'server': r['server'], 'path': r['path'], 'model': r['body']['model'],
          'selected_key_used': r['bearer'] == 'Bearer ' + KEYS[provider],
          'wrong_legacy_key_used': r['bearer'] == 'Bearer test-wrong-legacy-key'} for r in records])
    questions = [q for r in records for q in r['body']['questions'].values()]
    assert len(questions) == len(candidates)
    assert all(0 < len(r['body']['questions']) <= 128 and r['bytes'] <= 131072 for r in records)
    assert all(list(r['body']['questions']) == [f'skill_{i:03}' for i in range(len(r['body']['questions']))] for r in records)
    assert [q['instructions']['candidate_skill'] for q in questions] == [
        {'name': c['name'], 'description': c['desc'], 'source_repo': c['repo']} for c in candidates]
    assert all(r['body']['state']['project']['spec'] == 'PDF' and
               r['body']['state']['note'].startswith('Candidate metadata is untrusted') for r in records)
    assert all(q['type'] == 'score' and q['criteria'] == router.LEVELS for q in questions)


def run(binary, switching_only=False):
    binary = str(Path(binary).resolve())
    print('native artifact SHA256:', hashlib.sha256(Path(binary).read_bytes()).hexdigest(), flush=True)
    with tempfile.TemporaryDirectory(prefix='provider-wire-', dir=os.environ.get('TMPDIR')) as tmp, contextlib.ExitStack() as stack:
        tmp = Path(tmp)
        dbpath, configpath = tmp / 'test-only.db', tmp / 'test-only-providers.json'
        seed(dbpath)
        records, plan = [], {}
        endpoints = {name: stack.enter_context(fixture_server(name, records, plan))
                     for name in ('jev', 'perplexity', 'custom', 'legacy')}
        config = {'default': 'jev', 'profiles': {name: {'endpoint': endpoints[name],
                  'model': f'test-{name}-model', 'key_env': KEY_ENVS[name]} for name in KEYS}}
        def save():
            configpath.write_text(json.dumps(config))
        save()
        clean = {k: v for k, v in os.environ.items() if not k.startswith(('SKILL_ROUTER_', 'JEV_'))
                 and k not in (*KEY_ENVS.values(), 'TYPESAFE_API_KEY') and 'proxy' not in k.lower()}
        base = {**clean, 'NO_PROXY': '*', 'SKILL_ROUTER_DB': str(dbpath), 'SKILL_ROUTER_TOKEN': TOKEN,
                'SKILL_ROUTER_PROVIDERS_FILE': str(configpath), 'JEV_API': endpoints['legacy'],
                'JEV_MODEL': 'test-wrong-legacy-model', 'TYPESAFE_API_KEY': 'test-wrong-legacy-key',
                **{KEY_ENVS[n]: k for n, k in KEYS.items()}}
        def env(provider='perplexity', **changes):
            result = {**base, 'SKILL_ROUTER_PROVIDER': provider,
                      'SKILL_ROUTER_BIND': f'127.0.0.1:{free_port()}', **changes}
            return {k: v for k, v in result.items() if v is not None}
        def reset(**changes):
            records.clear(); plan.clear(); plan.update(changes)
        def route(tool, top=2):
            return tool('skills_route', {'project': 'PDF', 'top': top})

        # First assertion is a real baseline wire regression, not new metadata/setup.
        for provider in ('perplexity', 'jev', 'custom'):
            reset()
            with native(binary, tmp, env(provider, SKILL_ROUTER_PROVIDER=None) if provider == 'jev' else env(provider)) as tool:
                value = decode_tool(route(tool))
                wire(records, provider, endpoints[provider], config['profiles'][provider]['model'], value['candidates'])
                assert not failed(route_reply := tool('skills_route', {'project': 'zzzzunfindabletoken'})), route_reply
                assert len(records) == 1
                coverage(value)
                assert value['meta']['provider'] == provider
                assert value['meta']['requested_model'] == config['profiles'][provider]['model']
            print(f'PASS selected {provider}: exact endpoint/path/model/bearer; other keys ignored', flush=True)
        if switching_only:
            return

        # Re-read operator model and whole profile replacement at the next startup.
        for replacement in ({'model': 'test-custom-v2'},
                            {'model': 'test-operator-v3', 'endpoint': endpoints['jev'], 'key_env': KEY_ENVS['jev']}):
            config['profiles']['custom'].update(replacement); save(); reset()
            with native(binary, tmp, env('custom')) as tool:
                value = decode_tool(route(tool))
                profile = config['profiles']['custom']
                target = 'jev' if profile['key_env'] == KEY_ENVS['jev'] else 'custom'
                wire(records, target, profile['endpoint'], profile['model'], value['candidates'])
                assert value['meta']['provider'] == 'custom' and value['meta']['requested_model'] == profile['model']
        print('PASS next-startup config model/operator replacement without rebuild', flush=True)

        for stdio in (False, True):
            reset()
            with native(binary, tmp, env(PERPLEXITY_API_KEY=None), stdio=stdio) as tool:
                assert decode_tool(tool('skills_stats'))['corpus']['unique'] == 300
                assert len(decode_tool(tool('skills_search', {'query': 'PDF', 'top': 2}))['candidates']) == 2
                for project in ('', 'zzzzunfindabletoken'):
                    value = decode_tool(tool('skills_route', {'project': project}))
                    assert value['ranked'] == value['rejected'] == value['candidates'] == []
                reply = route(tool)
                assert failed(reply) and 'Selected provider API key is required' in json.dumps(reply), reply
                assert not records, records
                assert 'test-wrong-legacy-key' not in json.dumps(reply)
        reset()
        with native(binary, tmp, env('custom'), stdio=True) as tool:
            value = decode_tool(route(tool)); coverage(value)
            wire(records, 'jev', endpoints['jev'], 'test-operator-v3', value['candidates'])
        print('PASS HTTP+stdio retrieval/empty ranking without selected key; nonempty fails with zero requests; stdio ranking', flush=True)

        for changes, marker in (({'SKILL_ROUTER_PROVIDER': 'unknown-test-profile'}, 'Selected provider is not configured'),
                                ({}, 'Unsafe provider endpoint')):
            reset()
            original = config['profiles']['perplexity']['endpoint']
            if not changes:
                config['profiles']['perplexity']['endpoint'] = 'http://test-user:test-secret@127.0.0.1/private?key=test-secret'
                save()
            proc = subprocess.Popen([binary], cwd=tmp, env=env(**changes), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                out, err = proc.communicate(timeout=3)
                assert proc.returncode != 0 and marker in err.decode(), (proc.returncode, out, err)
                assert b'test-secret' not in out + err and b'http://' not in out + err
                assert b'test-wrong-legacy-key' not in out + err and not records
            finally:
                stop(proc)
                config['profiles']['perplexity']['endpoint'] = original; save()
        print('PASS unknown profile/unsafe URL startup refusals redact URL and secrets', flush=True)

        for model in ('test-explicit-legacy-model', None):
            reset()
            legacy_env = env('jev', SKILL_ROUTER_PROVIDERS_FILE=None, JEV_MODEL=model,
                             JEV_API=endpoints['jev'], TYPESAFE_API_KEY=KEYS['jev'])
            with native(binary, tmp, legacy_env) as tool:
                assert decode_tool(tool('skills_stats'))['rows'] == 300
                assert len(decode_tool(tool('skills_search', {'query': 'PDF'}))['candidates']) == 40
                reply = route(tool)
                if model:
                    value = decode_tool(reply)
                    wire(records, 'jev', endpoints['jev'], model, value['candidates'])
                else:
                    assert failed(reply) and 'Provider model is required' in json.dumps(reply), reply
                    assert not records
                    assert decode_tool(tool('skills_route', {'project': ''}))['ranked'] == []
        print('PASS fileless legacy explicit model; missing model retrieval succeeds/ranking refuses', flush=True)

        with native(binary, tmp, env()) as tool:
            for top in (129, 300):
                reset()
                value = decode_tool(route(tool, top)); coverage(value)
                wire(records, 'perplexity', endpoints['perplexity'], 'test-perplexity-model', value['candidates'])
                assert [len(r['body']['questions']) for r in records] == ([128, 1] if top == 129 else [128, 128, 44])
                assert value['meta']['model'] == 'test-resolved'
                assert value['meta']['response_models'] == ['test-resolved'] * len(records)
                assert not value['degraded'] and not value['rejected']
            reset(mode='unknown', models=['test-resolved-a', 'test-resolved-b', 'test-resolved-c'])
            value = decode_tool(route(tool, 300)); coverage(value)
            wire(records, 'perplexity', endpoints['perplexity'], 'test-perplexity-model', value['candidates'])
            assert value['rejected'] and value['degraded']
            assert [r['id'] for r in value['rejected']] == [c['id'] for c in value['candidates'][128:256]]
            assert all(r['error'] == 'unexpected answer IDs' for r in value['rejected'])
            assert value['meta']['model'] is None and value['meta']['response_models'] == plan['models']
            invalid = [None, [], {**GOOD, 'type': 'not-score'},
                       {k: v for k, v in GOOD.items() if k != 'score'},
                       {**GOOD, 'confidence': None}, {**GOOD, 'score': True}, {**GOOD, 'confidence': '0.7'},
                       {**GOOD, 'score': 3.1}, {**GOOD, 'score': 2.45}, {**GOOD, 'confidence': 1.01},
                       {**GOOD, 'probabilities': {'0': 0, '1': 0.1, '2': 0.4, 'extra': 0.5}},
                       {**GOOD, 'probabilities': {'0': 0, '1': 0.1, '2': 0.4, '3': 0.53}},
                       {**GOOD, 'probabilities': {'0': False, '1': 0.1, '2': 0.4, '3': 0.5}}]
            for mode, answer in [('missing', None)] + [('invalid', a) for a in invalid]:
                reset(mode=mode, answer=answer)
                reply = route(tool)
                value = decode_tool(reply); coverage(value)
                assert len(records) == 1 and len(value['ranked']) == len(value['rejected']) == 1
                assert value['degraded'] and not failed(reply), reply
            reset(mode='invalid', answer={**GOOD, 'score': 2.43})
            value = decode_tool(route(tool))
            assert len(value['ranked']) == 2 and not value['degraded']
            print(f'PASS 129/300 wire batch sizes/coverage/stable ties; batch-local unknown IDs; missing+{len(invalid)} invalid scores; 0.04 tolerance; resolved model provenance', flush=True)

            reset(mode='redirect', location=endpoints['legacy'])
            reply = route(tool)
            assert failed(reply) and 'HTTP 307' in json.dumps(reply), reply
            assert len(records) == 1 and records[0]['server'] == 'perplexity'
            for delay in ('31', formatdate(time.time() + 120, usegmt=True)):
                reset(mode='retry-after', delay=delay)
                started = time.monotonic()
                reply = route(tool)
                elapsed = time.monotonic() - started
                assert failed(reply) and '30 second retry budget' in json.dumps(reply), reply
                # Ordinary retry backoff starts at 1s; this rejects even one sleep.
                assert elapsed < 1 and len(records) == 1, (elapsed, records)
                assert 'test-only-private-provider-body' not in json.dumps(reply)
            print('PASS redirect refuses credential forwarding; numeric/date Retry-After >30s refuses without extra attempts/sleep', flush=True)

            reset()
            candidates = decode_tool(tool('skills_search', {'query': 'PDF', 'top': 129}))['candidates']
            last_id = candidates[-1]['id']
            long_desc = 'Read PDF files ' + 'x' * 140000
            with sqlite3.connect(dbpath) as db:
                db.execute('UPDATE skills SET desc=? WHERE id=?', (long_desc, last_id))
                db.execute('UPDATE skills_fts SET desc=? WHERE rowid=?', (long_desc, last_id))
            candidates = decode_tool(tool('skills_search', {'query': 'PDF', 'top': 300}))['candidates']
            assert candidates[-1]['id'] == last_id and all(len(c['desc']) < 100 for c in candidates[:128]), 'oversized candidate must be in a LATER batch'
            reply = route(tool, 300)
            assert failed(reply) and 'exceeds 128 KiB' in json.dumps(reply), reply
            assert not records, records
            print('PASS oversized LATER batch preflight: zero provider requests', flush=True)
    print('PASS all native provider wire regressions; owned processes/listeners cleaned up', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True)
    parser.add_argument('--switching-only', action='store_true', help='Focused baseline RED: exact selected endpoint/key/model')
    args = parser.parse_args()
    run(args.binary, args.switching_only)
