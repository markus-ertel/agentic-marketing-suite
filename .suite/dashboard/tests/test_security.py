"""Local-only security regressions using fictional files and a recording transport."""
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.app import DashboardServer, load_config
from server.files import Files


class RecordingSessions:
    """Records calls without ever starting an agent or executing a command."""
    def __init__(self):
        self.calls = []

    def connect(self, *args):
        self.calls.append(('connect', args))
        return {'connected': True}

    def send(self, *args):
        self.calls.append(('send', args))
        return {'accepted': True}

    def respond(self, *args):
        self.calls.append(('respond', args))
        return {'accepted': True}

    def disconnect(self, *args):
        self.calls.append(('disconnect', args))
        return {'disconnected': True}

    def close(self):
        pass


class SecurityHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('public.txt', '.suite/STATE.md', '.git/config', '.env',
                     'noCRM/.env.local', 'marketing/.marketing/STATE.md'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('FICTIONAL_TEST_CONTENT', encoding='utf-8')
        self.config = {'server': {'host': '127.0.0.1', 'port': 0},
                       'suite': {'root': str(self.root), 'show_internal_files': False},
                       'viewer': {'max_inline_file_mb': 1}}
        self.server = DashboardServer(self.config)
        self.server.sessions = RecordingSessions()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.authority = '127.0.0.1:' + str(self.server.server_port)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, host=None, origin=None, payload=None, extra_headers=(), token=True):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            connection.putrequest(method, path, skip_host=True)
            if host is not None:
                connection.putheader('Host', host)
            if origin is not None:
                connection.putheader('Origin', origin)
            if token:
                connection.putheader('X-Dashboard-Token', self.server.token)
            for key, value in extra_headers:
                connection.putheader(key, value)
            data = json.dumps(payload).encode() if payload is not None else b''
            if data:
                connection.putheader('Content-Type', 'application/json')
                connection.putheader('Content-Length', str(len(data)))
            connection.endheaders(data)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_untrusted_hosts_are_rejected_on_all_routes_and_methods(self):
        for host in ('attacker.invalid:' + str(self.server.server_port), None,
                     '127.0.0.1:1', 'localhost', '127.0.0.1.evil.invalid:' + str(self.server.server_port),
                     'user@' + self.authority, self.authority + '.evil.invalid'):
            for route in ('/', '/api/config', '/api/raw?path=.suite/STATE.md',
                          '/api/file?path=public.txt&meta=true', '/view/public.txt', '/api/events'):
                with self.subTest(host=host, route=route):
                    self.assertEqual(self.request('GET', route, host)[0], 403)
            with self.subTest(host=host, method='POST'):
                self.assertEqual(self.request('POST', '/api/sessions', host,
                                             'http://' + (host or 'attacker.invalid'),
                                             {'profile': 'fake', 'cwd': ''})[0], 403)
        for method in ('HEAD', 'OPTIONS', 'PUT'):
            with self.subTest(method=method):
                self.assertEqual(self.request(method, '/', 'attacker.invalid:8765')[0], 403)
        self.assertEqual(self.server.sessions.calls, [])

    def test_loopback_authorities_use_actual_bound_port(self):
        self.assertNotEqual(self.server.server_port, self.config['server']['port'])
        for name in ('127.0.0.1', 'localhost', '[::1]'):
            host = name + ':' + str(self.server.server_port)
            with self.subTest(host=host):
                self.assertEqual(self.request('GET', '/api/raw?path=public.txt', host)[0], 200)
                self.assertEqual(self.request('POST', '/api/sessions', host, 'http://' + host,
                                             {'profile': 'fake', 'cwd': ''})[0], 200)
        self.assertEqual(len(self.server.sessions.calls), 3)

    def test_every_post_requires_exact_local_origin_before_dispatch(self):
        for origin in (None, 'null', 'http://attacker.invalid', 'https://' + self.authority,
                       'http://' + self.authority + '/path', 'http://user@' + self.authority,
                       'http://localhost:' + str(self.server.server_port),
                       'http://' + self.authority + '.evil.invalid', 'http://127.0.0.1:1'):
            for route in ('/api/sessions', '/api/chat', '/api/interaction', '/api/disconnect'):
                with self.subTest(origin=origin, route=route):
                    self.assertEqual(self.request('POST', route, self.authority, origin, {})[0], 403)
        self.assertEqual(self.server.sessions.calls, [])
        for route, payload in (('/api/chat', {'session': 'fake', 'message': 'hello'}),
                               ('/api/interaction', {'session': 'fake', 'request_id': '1', 'response': {}}),
                               ('/api/disconnect', {'session': 'fake'})):
            with self.subTest(valid_route=route):
                self.assertEqual(self.request('POST', route, self.authority,
                                             'http://' + self.authority, payload)[0], 200)

    def test_duplicate_host_and_origin_are_rejected(self):
        self.assertEqual(self.request('GET', '/', self.authority,
                                     extra_headers=(('Host', self.authority),))[0], 403)
        self.assertEqual(self.request('POST', '/api/sessions', self.authority,
                                     'http://' + self.authority, {'profile': 'fake'},
                                     (('Origin', 'http://' + self.authority),))[0], 403)
        self.assertEqual(self.server.sessions.calls, [])

    def test_secret_and_disabled_internal_paths_on_every_file_route(self):
        for path in ('.git/config', '.env', 'noCRM/.env.local', 'marketing/.marketing/STATE.md'):
            encoded = quote(path, safe='')
            for route in ('/api/raw?path=' + encoded, '/api/raw?download=true&path=' + encoded,
                          '/api/file?path=' + encoded, '/api/file?meta=true&path=' + encoded,
                          '/view/' + encoded):
                with self.subTest(path=path, route=route):
                    self.assertEqual(self.request('GET', route, self.authority)[0], 403)
        status, body = self.request('GET', '/api/tree?hidden=true&q=STATE', self.authority)
        self.assertEqual(status, 200)
        self.assertEqual([entry['path'] for entry in json.loads(body)], ['.suite/STATE.md'])
        self.assertEqual(self.request('GET', '/api/tree?hidden=true&path=marketing/.marketing',
                                     self.authority)[0], 403)

    def test_internal_opt_in_does_not_enable_secrets(self):
        self.server.files = Files(self.root, show_internal_files=True)
        self.assertEqual(self.request('GET', '/api/raw?path=marketing/.marketing/STATE.md',
                                     self.authority)[0], 200)
        self.assertEqual(self.request('GET', '/api/raw?path=.git/config', self.authority)[0], 403)
        self.assertEqual(self.request('GET', '/api/raw?path=noCRM/.env.local', self.authority)[0], 403)


    def test_requests_without_the_start_token_are_rejected(self):
        # Host and Origin are strings any local process can set; only the printed token authorizes.
        origin = 'http://' + self.authority
        for method, route in (('GET', '/'), ('GET', '/app.js'), ('GET', '/api/raw?path=public.txt'),
                              ('GET', '/api/sessions'), ('POST', '/api/sessions'), ('POST', '/api/chat')):
            with self.subTest(route=route):
                status, _ = self.request(method, route, self.authority, origin if method == 'POST' else None,
                                         {'profile': 'fake'} if method == 'POST' else None, token=False)
                self.assertEqual(status, 401)
        status, _ = self.request('GET', '/api/raw?path=public.txt', self.authority, token=False,
                                 extra_headers=[('X-Dashboard-Token', 'wrong')])
        self.assertEqual(status, 401)
        self.assertEqual(self.request('GET', '/?token=wrong', self.authority, token=False)[0], 401)

    def test_token_url_sets_http_only_cookie_and_cookie_authorizes(self):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            connection.request('GET', '/?token=' + self.server.token, headers={'Host': self.authority})
            response = connection.getresponse(); response.read()
            self.assertEqual(response.status, 303)
            self.assertEqual(response.getheader('Location'), '/')
            cookie = response.getheader('Set-Cookie')
            self.assertIn('HttpOnly', cookie); self.assertIn('SameSite=Strict', cookie)
        finally:
            connection.close()
        status, _ = self.request('GET', '/api/raw?path=public.txt', self.authority, token=False,
                                 extra_headers=[('Cookie', cookie.split(';')[0])])
        self.assertEqual(status, 200)

    def test_dashboard_pages_cannot_be_framed(self):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            connection.request('GET', '/', headers={'Host': self.authority, 'X-Dashboard-Token': self.server.token})
            response = connection.getresponse(); response.read()
            self.assertEqual(response.getheader('X-Frame-Options'), 'DENY')
            self.assertIn("frame-ancestors 'none'", response.getheader('Content-Security-Policy'))
        finally:
            connection.close()


class SecurityFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, relative):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('FICTIONAL_SECRET', encoding='utf-8')
        return path

    def test_secret_patterns_are_always_denied_and_absent_from_search(self):
        paths = ('.git/config', 'nested/.git/config', '.env', '.env.production',
                 '.ENV.local', '.aws/credentials', '.ssh/config', '.codex/auth.json',
                 '.npmrc', '.pypirc', '.netrc', 'private.pem', 'private.key',
                 'client.p12', 'client.pfx', 'store.jks', 'id_rsa', 'id_ed25519',
                 'nested/secrets.json', 'credentials.json')
        for name in paths:
            self.write(name)
        for enabled in (False, True):
            files = Files(self.root, show_internal_files=enabled)
            for name in paths:
                with self.subTest(enabled=enabled, name=name):
                    with self.assertRaises(PermissionError):
                        files.resolve(name)
            visible = {entry['path'] for entry in files.tree(hidden=True, query='.')}
            self.assertFalse(visible.intersection(paths))

    def test_symlink_aliases_cannot_bypass_lexical_or_target_policy(self):
        self.write('public.txt')
        self.write('marketing/.marketing/internal.md')
        self.write('.git/config')
        (self.root / 'secret-alias.txt').symlink_to(self.root / '.git/config')
        (self.root / 'internal-alias.md').symlink_to(self.root / 'marketing/.marketing/internal.md')
        (self.root / '.env.alias').symlink_to(self.root / 'public.txt')
        (self.root / 'git-alias').symlink_to(self.root / '.git', target_is_directory=True)
        (self.root / 'outside-alias').symlink_to(self.root.parent, target_is_directory=True)
        for enabled in (False, True):
            files = Files(self.root, show_internal_files=enabled)
            for name in ('secret-alias.txt', '.env.alias', 'git-alias/config', 'outside-alias'):
                with self.subTest(enabled=enabled, name=name):
                    with self.assertRaises(PermissionError):
                        files.resolve(name)
        with self.assertRaises(PermissionError):
            Files(self.root).resolve('internal-alias.md')
        self.assertTrue(Files(self.root, show_internal_files=True).resolve('internal-alias.md').is_file())

    def test_non_loopback_host_requires_explicit_opt_in(self):
        config = self.root / 'config.json'
        for host in ('0.0.0.0', '192.168.1.10', 'example.org'):
            config.write_text(json.dumps({'server': {'host': host}, 'suite': {'root': '.'}}))
            with self.subTest(host=host), self.assertRaises(ValueError):
                load_config(config)
        config.write_text(json.dumps({'server': {'host': '0.0.0.0', 'allow_non_loopback': True}, 'suite': {'root': '.'}}))
        self.assertEqual(load_config(config)['server']['host'], '0.0.0.0')
        for host in ('127.0.0.1', 'localhost', '::1'):
            config.write_text(json.dumps({'server': {'host': host}, 'suite': {'root': '.'}}))
            self.assertEqual(load_config(config)['server']['host'], host)

    def test_agents_do_not_inherit_adapter_credentials(self):
        from server.adapters.base import agent_environment
        env = agent_environment({'PATH': '/bin', 'OPENAI_API_KEY': 'agent-own', 'MAIL_PASSWORD': 'x',
                                 'SITE_KEY_FILE': 'x', 'SITE_KNOWN_HOSTS_FILE': 'x', 'GOOGLE_OAUTH_ACCESS_TOKEN': 'x'})
        self.assertEqual(env, {'PATH': '/bin', 'OPENAI_API_KEY': 'agent-own'})

    def test_config_toggle_is_boolean_and_defaults_to_disabled(self):
        config = self.root / 'config.json'
        for value in ('false', 1, None, []):
            config.write_text(json.dumps({'suite': {'root': '.', 'show_internal_files': value}}))
            with self.subTest(value=value), self.assertRaises(ValueError):
                load_config(config)
        config.write_text(json.dumps({'suite': {'root': '.'}}))
        self.assertIs(load_config(config)['suite']['show_internal_files'], False)
