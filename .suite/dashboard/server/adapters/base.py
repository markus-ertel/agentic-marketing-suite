"""Line-delimited subprocess transport and correlated RPC calls."""
from collections import deque
import json
import subprocess
import threading
import uuid


class Adapter:
    capabilities = {'streaming': True, 'resume': False, 'interactions': False}
    notice = ''

    def __init__(self, profile, cwd, emit, external_id=None):
        self.profile, self.cwd, self.emit = profile, cwd, emit
        self.external_id = external_id
        self.process = None
        self.pending = {}
        self.write_lock = threading.Lock()
        self.pending_lock = threading.Lock()
        self.closed = False
        self.stderr = deque(maxlen=20)

    def event(self, kind, **data):
        self.emit({'type': 'agent.' + kind, **data})

    def status(self, value):
        self.event('status', status=value)

    def start(self, command=None):
        self.process = subprocess.Popen(command or self.profile['command'], cwd=self.cwd,
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        threading.Thread(target=self._errors, args=(self.process,), daemon=True).start()
        threading.Thread(target=self._read, args=(self.process,), daemon=True).start()

    def _errors(self, process):
        for line in process.stderr:
            self.stderr.append(line.decode('utf-8', errors='replace').strip()[:2000])

    def _read(self, process):
        try:
            for line in process.stdout:
                if len(line) > 16 * 1024 * 1024:
                    raise RuntimeError('Agentenereignis überschreitet 16 MB.')
                try:
                    record = json.loads(line)
                except ValueError:
                    self.event('error', message='Agent lieferte kein gültiges JSON-Ereignis.')
                    continue
                if not isinstance(record, dict):
                    continue
                key = str(record.get('id', ''))
                with self.pending_lock:
                    pending = self.pending.get(key)
                if pending and 'method' not in record:
                    pending['record'] = record
                    pending['ready'].set()
                else:
                    self.handle(record)
            code = process.wait()
            self.exited(code)
        except Exception as exc:
            if not self.closed:
                self.event('error', message=str(exc))
                self.status('Fehler')
        finally:
            with self.pending_lock:
                for pending in self.pending.values():
                    pending['ready'].set()
            for stream in (process.stdout, process.stderr):
                if stream:
                    stream.close()

    def exited(self, code):
        if not self.closed:
            self.event('error', message=f'Agentenprozess beendet (Code {code}). ' + '\n'.join(self.stderr))
            self.status('Fehler' if code else 'nicht verbunden')

    def write(self, record):
        with self.write_lock:
            if self.closed or not self.process or self.process.poll() is not None:
                raise RuntimeError('Agentenprozess ist nicht verbunden.')
            self.process.stdin.write((json.dumps(record, ensure_ascii=False) + '\n').encode())
            self.process.stdin.flush()

    def request(self, record, timeout=30):
        key = str(uuid.uuid4())
        record = {**record, 'id': key}
        pending = {'ready': threading.Event()}
        with self.pending_lock:
            self.pending[key] = pending
        try:
            self.write(record)
            if not pending['ready'].wait(timeout):
                raise TimeoutError('Agent antwortet nicht rechtzeitig auf die Protokollanfrage.')
            response = pending.get('record')
            if not response:
                raise RuntimeError('Agentenverbindung während der Anfrage beendet. ' + '\n'.join(self.stderr))
            if response.get('error') or response.get('success') is False:
                raise RuntimeError(str(response.get('error', 'Agentenanfrage fehlgeschlagen.')))
            return response.get('result', response.get('data', {}))
        finally:
            with self.pending_lock:
                self.pending.pop(key, None)

    def close(self):
        self.closed = True
        process = self.process
        if process:
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
        self.status('nicht verbunden')

    def respond(self, request_id, response):
        raise ValueError('Dieser Adapter unterstützt keine interaktiven Antworten.')
