"""Local HTTP/SSE server. Run: python3 .suite/dashboard/server/app.py."""
import argparse
import json
import mimetypes
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit, unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.files import Files

DASHBOARD = Path(__file__).resolve().parents[1]


def load_config(path):
    path = Path(path).resolve()
    config = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(config, dict):
        raise ValueError('Die Konfiguration muss ein JSON-Objekt sein.')
    for section in ('server', 'suite', 'viewer', 'agents'):
        if section in config and not isinstance(config[section], dict):
            raise ValueError(section + ' muss ein JSON-Objekt sein.')
    server = config.setdefault('server', {})
    port = server.setdefault('port', 8765)
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError('server.port muss zwischen 0 und 65535 liegen.')
    server.setdefault('host', '127.0.0.1')
    if not isinstance(server['host'], str) or not server['host']:
        raise ValueError('server.host muss ein Hostname oder eine IP-Adresse sein.')
    suite = config.setdefault('suite', {})
    if not isinstance(suite.get('root', '../..'), str):
        raise ValueError('suite.root muss ein Verzeichnispfad sein.')
    suite['root'] = str((path.parent / suite.get('root', '../..')).resolve(strict=True))
    interval = suite.setdefault('refresh_interval_ms', 2000)
    if isinstance(interval, bool) or not isinstance(interval, (int, float)) or interval < 500:
        raise ValueError('refresh_interval_ms muss mindestens 500 betragen.')
    viewer = config.setdefault('viewer', {})
    limit = viewer.setdefault('max_inline_file_mb', 25)
    if isinstance(limit, bool) or not isinstance(limit, (int, float)) or limit <= 0:
        raise ValueError('max_inline_file_mb muss positiv sein.')
    if viewer.get('default_mode', 'preview') not in ('preview', 'source'):
        raise ValueError('viewer.default_mode muss preview oder source sein.')
    profiles = config.get('agents', {}).get('profiles', [])
    if not isinstance(profiles, list):
        raise ValueError('agents.profiles muss eine Liste sein.')
    ids = set()
    for profile in profiles:
        if not isinstance(profile, dict) or not all(isinstance(profile.get(key), str) and profile[key] for key in ('id', 'label', 'adapter')):
            raise ValueError('Jedes Agentenprofil benötigt id, label und adapter.')
        if profile['id'] in ids:
            raise ValueError('Agentenprofil-IDs müssen eindeutig sein.')
        ids.add(profile['id'])
        command = profile.get('command')
        if not isinstance(command, list) or not command or not all(isinstance(s, str) and s for s in command):
            raise ValueError('Agentencommand muss eine nicht leere Liste von Argumenten sein.')
    return config


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, config):
        self.config = config
        self.files = Files(config['suite']['root'], config['viewer']['max_inline_file_mb'])
        self.sessions = None
        super().__init__((config['server']['host'], config['server']['port']), Handler)

    def server_close(self):
        if self.sessions:
            self.sessions.close()
        super().server_close()


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        # Do not log prompts, query paths, or file contents.
        if args and str(args[1] if len(args) > 1 else '').startswith('5'):
            super().log_message(fmt, *args)

    def reply(self, value, status=200, mime='application/json; charset=utf-8'):
        data = json.dumps(value, ensure_ascii=False).encode() if mime.startswith('application/json') else value
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        try:
            self.get()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except (FileNotFoundError, IsADirectoryError) as exc:
            self.reply({'error': str(exc)}, 404)
        except PermissionError as exc:
            self.reply({'error': str(exc)}, 403)
        except (ValueError, KeyError) as exc:
            self.reply({'error': str(exc)}, 400)
        except OSError as exc:
            self.reply({'error': str(exc)}, 503)

    def get(self):
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        arg = lambda key, default='': query.get(key, [default])[0]
        files = self.server.files
        if url.path == '/api/config':
            config = self.server.config
            return self.reply({'suite': {k: v for k, v in config['suite'].items() if k != 'root'},
                               'viewer': config['viewer'], 'default_profile': config.get('agents', {}).get('default_profile')})
        if url.path == '/api/modules':
            return self.reply(files.modules())
        if url.path == '/api/tree':
            return self.reply(files.tree(arg('path'), arg('hidden') == 'true', arg('q')))
        if url.path == '/api/file':
            return self.reply(files.metadata(arg('path')) if arg('meta') == 'true' else files.preview(arg('path')))
        if url.path == '/api/raw':
            return self.raw(arg('path'), arg('download') == 'true')
        if url.path.startswith('/view/'):
            return self.raw(unquote(url.path[len('/view/'):]))
        if url.path == '/api/agents':
            return self.reply(self.server.sessions.profiles() if self.server.sessions else [])
        if url.path == '/api/sessions':
            return self.reply(self.server.sessions.snapshot() if self.server.sessions else [])
        if url.path == '/api/events' and self.server.sessions:
            return self.events(arg('session'), int(arg('after', self.headers.get('Last-Event-ID', '0'))))
        static = {'/': 'index.html', '/app.js': 'app.js', '/styles.css': 'styles.css'}.get(url.path)
        if static:
            return self.reply((DASHBOARD / 'web' / static).read_bytes(), mime=(mimetypes.guess_type(static)[0] or 'text/plain') + '; charset=utf-8')
        self.reply({'error': 'Endpunkt nicht vorhanden.'}, 404)

    def raw(self, relative, download=False):
        files = self.server.files
        meta = files.metadata(relative)
        path = files.resolve(relative)
        size = meta['size']
        start, end, status = 0, size - 1, 200
        range_header = self.headers.get('Range')
        if range_header:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', range_header)
            if not match or not any(match.groups()):
                return self.reply({'error': 'Ungültiger Bytebereich.'}, 416)
            first, last = match.groups()
            start = int(first) if first else max(0, size - int(last))
            end = min(int(last), size - 1) if first and last else size - 1
            if start >= size or start > end:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            status = 206
        # Open before sending headers to preserve useful missing-file errors.
        with path.open('rb') as stream:
            self.send_response(status)
            self.send_header('Content-Type', meta['mime'])
            self.send_header('Content-Length', str(max(0, end - start + 1)))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "sandbox; default-src 'none'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; media-src 'self'; font-src 'self'")
            if download:
                from urllib.parse import quote
                self.send_header('Content-Disposition', "attachment; filename*=UTF-8''" + quote(meta['name']))
            if status == 206:
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            self.end_headers()
            stream.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                block = stream.read(min(65536, remaining))
                if not block:
                    break
                self.wfile.write(block)
                remaining -= len(block)

    def do_POST(self):
        try:
            # A local transport, not an authentication platform. Reject cross-origin browser writes.
            origin = self.headers.get('Origin')
            if origin and urlsplit(origin).netloc != self.headers.get('Host'):
                raise PermissionError('Anfrage von einer fremden Browserseite abgelehnt.')
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= 1024 * 1024:
                raise ValueError('Leere oder zu große Nachricht.')
            payload = json.loads(self.rfile.read(length))
            manager = self.server.sessions
            if not manager:
                raise ValueError('Agententransport nicht gestartet.')
            route = urlsplit(self.path).path
            if route == '/api/sessions':
                result = manager.connect(payload['profile'], payload.get('cwd', ''), payload.get('external_id'))
            elif route == '/api/chat':
                result = manager.send(payload['session'], payload['message'])
            elif route == '/api/interaction':
                result = manager.respond(payload['session'], payload['request_id'], payload['response'])
            elif route == '/api/disconnect':
                result = manager.disconnect(payload['session'])
            else:
                return self.reply({'error': 'Endpunkt nicht vorhanden.'}, 404)
            self.reply(result)
        except PermissionError as exc:
            self.reply({'error': str(exc)}, 403)
        except (ValueError, KeyError, TypeError) as exc:
            self.reply({'error': str(exc)}, 400)
        except (OSError, RuntimeError, TimeoutError) as exc:
            self.reply({'error': str(exc)}, 503)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def events(self, session_id, after):
        session = self.server.sessions.get(session_id)
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            events = session.events_after(after, timeout=5)
            for event in events:
                self.wfile.write(('id: ' + str(event['id']) + '\ndata: ' + json.dumps(event, ensure_ascii=False) + '\n\n').encode())
                after = event['id']
            self.wfile.write(b': heartbeat\n\n')
            self.wfile.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=DASHBOARD / 'config.json')
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        with DashboardServer(config) as server:
            from server.sessions import Sessions
            server.sessions = Sessions(config.get('agents', {}), server.files)
            host, port = server.server_address[:2]
            print(f'Dashboard: http://{host}:{port}  (Stoppen: Strg+C)', flush=True)
            server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f'Dashboard konnte nicht starten: {exc}\n')


if __name__ == '__main__':
    main()
