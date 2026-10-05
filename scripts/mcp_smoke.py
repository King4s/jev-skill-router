#!/usr/bin/env python3
"""Exercise the actual MCP binary or deployed HTTP endpoint.
Uses the project's declared offline Python dependencies.
Offline mode uses a temporary database and explicitly synthetic provider responses.
"""
import argparse
import concurrent.futures as cf
import contextlib
import hashlib
import http.client
import http.server
import json
import os
from pathlib import Path
import selectors
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import router

INIT = {'protocolVersion': '2025-03-26', 'capabilities': {},
        'clientInfo': {'name': 'jev-router-smoke', 'version': '1.0'}}
GOOD = {'type': 'score', 'score': 2.4, 'confidence': 0.7,
        'probabilities': {'0': 0.0, '1': 0.1, '2': 0.4, '3': 0.5}}


def payload(method, params=None, rid=1):
    return {'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params or {}}


def decode_tool(reply):
    assert 'error' not in reply, reply
    return json.loads(reply['result']['content'][0]['text'])


def failed(reply):
    return 'error' in reply or bool(reply.get('result', {}).get('isError'))


class HttpClient:
    def __init__(self, url, token):
        self.url, self.token = url, token

    def request(self, data, headers=None):
        h = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
             'MCP-Protocol-Version': '2025-03-26', 'Authorization': 'Bearer ' + self.token}
        h.update(headers or {})
        req = urllib.request.Request(self.url, data=data if isinstance(data, bytes) else json.dumps(data).encode(), headers=h)
        try:
            with urllib.request.urlopen(req, timeout=200) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode(errors='replace')

    def rpc(self, method, params=None):
        status, reply = self.request(payload(method, params))
        assert status == 200, (status, reply)
        assert isinstance(reply, dict), reply
        return reply

    def tool(self, name, arguments=None):
        return self.rpc('tools/call', {'name': name, 'arguments': arguments or {}})


class Provider(http.server.BaseHTTPRequestHandler):
    mode, calls = 'good', 0
    entered = threading.Condition()
    release = threading.Event()

    def log_message(self, format, *args):
        pass

    def do_POST(self):
        cls = type(self)
        with cls.entered:
            cls.calls += 1
            cls.entered.notify_all()
        data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        keys = list(data['questions'])
        assert data['state']['note'].startswith('Candidate metadata is untrusted')
        mode = cls.mode
        if mode == 'held' and not cls.release.wait(15):
            self.send_error(504, 'Offline hold timed out')
            return
        if mode == '401' or (mode == 'retry' and cls.calls == 1):
            self.send_response(401 if mode == '401' else 429)
            self.send_header('Retry-After', '1')
            self.end_headers()
            self.wfile.write(b'private-provider-body')
            return
        if mode == 'truncated-always' or (mode == 'truncated' and cls.calls == 1):
            self.send_response(200)
            self.send_header('Content-Length', '10000')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(b'{')
            self.close_connection = True
            return
        answers = {k: GOOD.copy() for k in keys}
        if mode == 'partial':
            answers.pop(keys[-1])
        if mode == 'unexpected':
            answers['unknown'] = GOOD
        if mode == 'invalid':
            for a in answers.values():
                a['score'] = True
        value = {'model': 'offline-fixture', 'answers': answers}
        if mode == 'oversized':
            value['padding'] = 'x' * 2097152
        body = b'not-json' if mode == 'json' else json.dumps(value).encode()
        self.send_response(200)
        self.end_headers()
        with contextlib.suppress(BrokenPipeError, ConnectionResetError):
            self.wfile.write(body)


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def wait_ready(proc, port):
    for _ in range(100):
        if proc.poll() is not None:
            raise RuntimeError('MCP server exited during startup')
        with socket.socket() as s:
            if s.connect_ex(('127.0.0.1', port)) == 0:
                return
        time.sleep(0.05)
    raise RuntimeError('MCP server startup timed out')


def wire_checks(client):
    initialized = client.rpc('initialize', INIT)
    assert initialized['result']['serverInfo']['name'] == 'jev-skill-router'
    names = {t['name'] for t in client.rpc('tools/list')['result']['tools']}
    assert names == {'skills_stats', 'skills_search', 'skills_route'}, names
    stats = decode_tool(client.tool('skills_stats'))
    assert stats['corpus']['unique'] > 0
    for top in (-1, 0, 301, True, '40'):
        reply = client.tool('skills_search', {'query': 'PDF', 'top': top})
        assert failed(reply), (top, reply)
    assert failed(client.tool('skills_search', {'query': 'x' * 16385}))
    assert not failed(client.tool('skills_search', {'query': 'é' * 8192}))
    assert failed(client.tool('skills_search', {'query': 'é' * 8193}))
    for query in ('', 'zzzzunfindabletoken'):
        assert decode_tool(client.tool('skills_search', {'query': query}))['candidates'] == []
    assert client.request(payload('initialize', INIT), {'Authorization': ''})[0] == 401
    assert client.request(payload('initialize', INIT), {'Authorization': 'Bearer invalid'})[0] == 401
    assert client.request(payload('initialize', INIT), {'Origin': 'https://evil.invalid'})[0] == 403
    assert client.request(payload('initialize', INIT), {'Host': 'evil.invalid'})[0] >= 400
    assert client.request(b' ' * 262145)[0] == 413
    parsed = urllib.parse.urlsplit(client.url)
    conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=10)
    body = b' ' * 262145
    conn.request('POST', parsed.path, body=iter([body[:130000], body[130000:]]), encode_chunked=True,
                 headers={'Authorization': 'Bearer ' + client.token, 'Content-Type': 'application/json',
                          'Accept': 'application/json, text/event-stream'})
    response = conn.getresponse()
    assert response.status == 413, response.status
    response.read(); conn.close()
    return stats


def offline(binary):
    with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
        dbpath = Path(tmp) / 'skills.db'
        with sqlite3.connect(dbpath) as db:
            db.executescript(router.SCHEMA)
            for i in (1, 2):
                db.execute('INSERT INTO skills(id,name,desc,tags,tier,repo,url) VALUES(?,?,?,?,?,?,?)',
                           (i, f'pdf{i}', 'Read PDF files', '', 'vendor', 'example/repo', 'https://example.invalid/skill'))
                db.execute('INSERT INTO skills_fts(rowid,name,desc,tags) VALUES(?,?,?,?)', (i, f'pdf{i}', 'Read PDF files', ''))
        provider = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Provider)
        thread = threading.Thread(target=provider.serve_forever, daemon=True); thread.start()
        port = free_port(); token = 'offline-token-not-a-real-secret-0123456789'
        env = {**os.environ, 'SKILL_ROUTER_DB': str(dbpath), 'SKILL_ROUTER_BIND': f'127.0.0.1:{port}',
               'SKILL_ROUTER_TOKEN': token, 'TYPESAFE_API_KEY': 'offline-key',
               'JEV_API': f'http://127.0.0.1:{provider.server_port}/'}
        proc = subprocess.Popen([binary, '--http'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            wait_ready(proc, port)
            client = HttpClient(f'http://127.0.0.1:{port}/mcp', token)
            wire_checks(client)
            for query in ('Read PDF files', 'PDF " OR * NOT injection', 'MCP-service １２ ²² ⅫⅫ PDF'):
                value = decode_tool(client.tool('skills_search', {'query': query}))
                with router.open_index(dbpath) as db:
                    assert value['candidates'] == router.shortlist(db, query, 40)
                expected = list(dict.fromkeys(w for w in router.re.findall(r'[^\W_]+', query) if len(w) >= 2 and not w.isdigit()))[:40]
                assert value['meta']['query_tokens'] == expected
            for mode in ('good', 'partial', 'unexpected', 'invalid', '401', 'retry', 'json', 'truncated', 'truncated-always'):
                Provider.mode, Provider.calls = mode, 0
                started = time.monotonic()
                reply = client.tool('skills_route', {'project': 'Read PDF files'})
                if mode in ('401', 'json', 'truncated-always'):
                    assert failed(reply)
                    assert 'private-provider-body' not in json.dumps(reply)
                    assert Provider.calls == (4 if mode == 'truncated-always' else 1), (mode, Provider.calls)
                else:
                    value = decode_tool(reply)
                    assert len(value['ranked']) + len(value['rejected']) == 2
                    assert value['degraded'] == (mode in ('partial', 'unexpected', 'invalid'))
                    assert bool(reply['result'].get('isError')) == (mode in ('unexpected', 'invalid'))
                    if mode in ('retry', 'truncated'):
                        assert Provider.calls == 2 and time.monotonic() - started >= 1
            Provider.mode, Provider.calls = 'oversized', 0
            reply = client.tool('skills_route', {'project': 'Read PDF files'})
            assert failed(reply) and 'exceeds 2 MiB' in json.dumps(reply), reply
            assert Provider.calls == 1
            Provider.mode, Provider.calls = 'held', 0
            Provider.release.clear()
            with cf.ThreadPoolExecutor(max_workers=5) as pool:
                held = [pool.submit(client.tool, 'skills_route', {'project': 'Read PDF files'}) for _ in range(4)]
                try:
                    with Provider.entered:
                        assert Provider.entered.wait_for(lambda: Provider.calls == 4, timeout=10), Provider.calls
                    overflow = pool.submit(client.tool, 'skills_route', {'project': 'Read PDF files'}).result(timeout=5)
                    assert failed(overflow) and 'Ranking capacity reached' in json.dumps(overflow), overflow
                    assert Provider.calls == 4
                finally:
                    Provider.release.set()
                for pending in held:
                    assert len(decode_tool(pending.result(timeout=10))['ranked']) == 2
            Provider.mode, Provider.calls = 'good', 0
            with sqlite3.connect(dbpath) as db:
                long_description = 'Read PDF files ' + 'x' * 65400
                db.execute('UPDATE skills SET desc=?', (long_description,))
                db.execute('UPDATE skills_fts SET desc=?', (long_description,))
            reply = client.tool('skills_route', {'project': 'Read PDF files'})
            assert failed(reply) and 'exceeds 131072 bytes' in json.dumps(reply), reply
            assert Provider.calls == 0
            print('offline MCP: UTF-8 limits, >2MiB response, >128KiB request before provider, four held slots/fifth fail-fast and release passed')
            print('offline MCP: handshake, tools, Python parity, auth, Host/Origin, fixed/chunked limits, ranking contracts and retries passed')
        finally:
            proc.terminate(); proc.wait(timeout=10)
            provider.shutdown(); provider.server_close()
        # Exercise real stdio framing separately; no key needed for stats.
        proc = subprocess.Popen([binary], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        assert proc.stdin is not None and proc.stdout is not None
        try:
            for message in (payload('initialize', INIT), {'jsonrpc': '2.0', 'method': 'notifications/initialized'}, payload('tools/list', rid=2)):
                proc.stdin.write(json.dumps(message).encode() + b'\n'); proc.stdin.flush()
            with selectors.DefaultSelector() as sel:
                sel.register(proc.stdout, selectors.EVENT_READ)
                assert sel.select(10), 'stdio initialize timeout'
                assert json.loads(proc.stdout.readline())['id'] == 1
                assert sel.select(10), 'stdio tools/list timeout'
                assert len(json.loads(proc.stdout.readline())['result']['tools']) == 3
            proc.stdin.close(); proc.wait(timeout=10)
            assert proc.returncode == 0
            print('stdio MCP: handshake, tools/list and EOF shutdown passed')
        finally:
            if proc.poll() is None:
                proc.kill(); proc.wait()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary')
    p.add_argument('--url')
    p.add_argument('--out')
    p.add_argument('--live', action='store_true')
    args = p.parse_args()
    if args.binary:
        offline(args.binary)
    else:
        assert args.url and os.environ.get('SKILL_ROUTER_TOKEN'), 'Provide --url and SKILL_ROUTER_TOKEN'
        client = HttpClient(args.url, os.environ['SKILL_ROUTER_TOKEN'])
        print(json.dumps(wire_checks(client), indent=2))
        if args.live:
            value = decode_tool(client.tool('skills_route', {'project': 'Build a Rust MCP skill router with SQLite FTS5, read-only metadata retrieval and systemd deployment.', 'top': 40}))
            assert len(value['candidates']) == 40 and len(value['ranked']) == 40 and not value['degraded'], value
            if args.out:
                Path(args.out).write_text(json.dumps(value, indent=2))
            print('live Jev:', value['meta']['model'], 'accepted:', len(value['ranked']), 'latency_s:', value['meta']['latency_s'])


if __name__ == '__main__':
    main()
