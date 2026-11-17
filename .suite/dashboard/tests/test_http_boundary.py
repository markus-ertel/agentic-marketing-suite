"""Real HTTP parsing/dispatch through an in-memory transport (no listening socket)."""
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.app import Handler, local_host
from server.files import Files


class Connection:
    def __init__(self, data):
        self.input = io.BytesIO(data)
        self.output = io.BytesIO()
    def makefile(self, *args):return self.input
    def sendall(self, data):self.output.write(data)


class HTTPBoundaryTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);self.root=Path(folder.name)
        (self.root/"page.html").write_text("<h1>Preview</h1>")
        (self.root/"style.css").write_text("h1 {color: blue}")
        (self.root/".env").write_text("fictional-secret")

    def request(self, route, method='GET', headers=None, payload=None):
        server = SimpleNamespace(server_port=8765, token='start-token', preview_token='preview-token',
                                 config={'suite': {}, 'viewer': {}}, files=Files(self.root))
        data = json.dumps(payload).encode() if payload is not None else b''
        fields = {'Host': '127.0.0.1:8765', 'Connection': 'close', **(headers or {})}
        if data:fields['Content-Length'] = str(len(data))
        request = (method + ' ' + route + ' HTTP/1.1\r\n' + ''.join(k + ': ' + v + '\r\n' for k,v in fields.items()) + '\r\n').encode() + data
        connection = Connection(request)
        Handler(connection, ('127.0.0.1', 12345), server)
        return connection.output.getvalue().decode()

    def test_local_headers_do_not_authenticate_api_raw_preview_or_sse(self):
        for route in ('/api/config', '/api/raw?path=.env', '/view/file.html', '/api/events'):
            with self.subTest(route=route):self.assertIn('401 Unauthorized', self.request(route))
        self.assertIn('401 Unauthorized', self.request('/api/chat', 'POST', {'Origin': 'http://127.0.0.1:8765'}, {}))

    def test_bootstrap_cookie_and_bearer_authorize_without_query_secrets(self):
        origin = {'Origin': 'http://127.0.0.1:8765'}
        self.assertIn('401 Unauthorized', self.request('/api/auth','POST',origin,{'token':'wrong'}))
        response = self.request('/api/auth','POST',origin,{'token':'start-token'})
        self.assertIn('200 OK', response)
        self.assertIn('Set-Cookie: ams_dashboard=start-token; HttpOnly; SameSite=Strict; Path=/', response)
        for headers in ({'Cookie':'ams_dashboard=start-token'}, {'Authorization':'Bearer start-token'}):
            self.assertIn('200 OK', self.request('/api/config',headers=headers))
        self.assertIn('401 Unauthorized', self.request('/api/config',headers={'Cookie':'ams_dashboard=stale'}))

    def test_security_headers_and_origin_still_apply(self):
        response = self.request('/api/config',headers={'Authorization':'Bearer start-token'})
        self.assertIn('X-Frame-Options: DENY', response)
        self.assertIn("frame-ancestors 'none'", response)
        self.assertIn("img-src 'self'", response)
        self.assertIn('Referrer-Policy: no-referrer', response)
        self.assertIn('403 Forbidden', self.request('/api/auth','POST',{'Origin':'http://evil.invalid'},{'token':'start-token'}))

    def test_preview_capability_only_reads_and_keeps_sandbox_and_private_rules(self):
        base='/preview/preview-token/'
        response=self.request(base+'page.html')
        self.assertIn('200 OK',response)
        self.assertIn('sandbox;',response)
        self.assertNotIn('allow-same-origin',response)
        self.assertIn('Referrer-Policy: no-referrer',response)
        self.assertIn('200 OK',self.request(base+'style.css'))
        self.assertIn('403 Forbidden',self.request(base+'.env'))
        self.assertIn('401 Unauthorized',self.request('/api/config',headers={'X-Dashboard-Token':'preview-token'}))
        self.assertIn('401 Unauthorized',self.request(base+'page.html','POST',{'Origin':'http://127.0.0.1:8765'},{}))

    def test_static_login_shell_contains_no_private_file_content(self):
        self.assertIn('200 OK',self.request('/'))
        self.assertIn('401 Unauthorized',self.request('/?token=wrong'))

    def test_non_loopback_hosts_are_never_resolved_or_bound(self):
        for name in ('0.0.0.0','::','192.168.1.2','public.example'):
            with self.assertRaises(ValueError):local_host(name)
