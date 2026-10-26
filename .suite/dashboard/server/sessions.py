"""Only observed external sessions and a bounded, in-memory SSE transport buffer."""
from collections import deque
from datetime import datetime, timezone
import shutil
import threading
import uuid

from .adapters import ADAPTERS


class Session:
    def __init__(self, profile, cwd):
        self.id = str(uuid.uuid4())
        self.profile = profile
        self.cwd = cwd
        self.status = 'unbekannt'
        self.external_id = None
        self.model = None
        self.session_file = None
        self.last_event = None
        self.busy = False
        self.disconnected = False
        self.adapter = None
        self.events = deque(maxlen=2000)
        self.sequence = 0
        self.condition = threading.Condition(threading.RLock())
        self.interactions = {}

    def emit(self, event):
        with self.condition:
            self.sequence += 1
            self.last_event = datetime.now(timezone.utc).isoformat()
            event = {**event, 'id': self.sequence, 'timestamp': self.last_event, 'session': self.id,
                     'adapter': self.profile['adapter'], 'source': event.get('source', 'external-protocol')}
            if event['type'] == 'agent.status':
                self.status = event['status']
                if self.status in ('abgeschlossen', 'Fehler', 'nicht verbunden', 'bereit'):
                    self.busy = False
                elif self.status in ('arbeitet', 'wartet auf Eingabe'):
                    self.busy = True
            elif event['type'] == 'agent.turn_end':
                self.busy = False
                self.interactions.clear()
            elif event['type'] == 'agent.session':
                self.external_id = event.get('external_id') or self.external_id
                self.model = event.get('model') or self.model
                self.session_file = event.get('session_file') or self.session_file
            elif event['type'] == 'agent.input_requested':
                self.interactions[event['request_id']] = event
            elif event['type'] == 'agent.input_resolved':
                self.interactions.pop(event['request_id'], None)
            self.events.append(event)
            self.condition.notify_all()

    def events_after(self, after, timeout=0):
        with self.condition:
            if self.sequence <= after:
                self.condition.wait(timeout)
            result = []
            if self.events and after < self.events[0]['id'] - 1:
                result.append({'type': 'stream.gap', 'id': self.events[0]['id'] - 1})
            result.extend(e for e in self.events if e['id'] > after)
            return result

    def snapshot(self):
        with self.condition:
            return {'id': self.id, 'profile': self.profile['id'], 'label': self.profile['label'],
                    'cwd': self.cwd, 'status': self.status, 'external_id': self.external_id,
                    'session_file': self.session_file, 'model': self.model, 'last_event': self.last_event,
                    'busy': self.busy, 'capabilities': self.adapter.capabilities if self.adapter else {}}


class Sessions:
    def __init__(self, config, files):
        self.config, self.files = config, files
        self.items = {}
        self.lock = threading.RLock()

    def profiles(self):
        result = []
        for profile in self.config.get('profiles', []):
            adapter = ADAPTERS.get(profile['adapter'])
            result.append({'id': profile['id'], 'label': profile['label'], 'adapter': profile['adapter'],
                           'available': bool(adapter and shutil.which(profile['command'][0])),
                           'capabilities': adapter.capabilities if adapter else {'streaming': False, 'resume': False, 'interactions': False},
                           'notice': adapter.notice if adapter else 'Unbekannter Adapter.'})
        return result

    def connect(self, profile_id, cwd, external_id=None):
        profile = next((p for p in self.config.get('profiles', []) if p['id'] == profile_id), None)
        if not profile or profile['adapter'] not in ADAPTERS:
            raise ValueError('Unbekanntes Agentenprofil oder Adapter.')
        if not shutil.which(profile['command'][0]):
            raise ValueError('Agentenprogramm nicht installiert: ' + profile['command'][0])
        directory = self.files.resolve(cwd)
        if not directory.is_dir():
            raise ValueError('Arbeitsverzeichnis nicht vorhanden.')
        adapter_class = ADAPTERS[profile['adapter']]
        if external_id and not adapter_class.capabilities['resume']:
            raise ValueError('Dieser Adapter unterstützt keine Wiederaufnahme.')
        session = Session(profile, '' if directory == self.files.root else directory.relative_to(self.files.root).as_posix())
        session.adapter = adapter_class(profile, directory, session.emit, external_id)
        with self.lock:
            self.items[session.id] = session
        try:
            session.adapter.connect()
        except Exception as exc:
            session.emit({'type': 'agent.error', 'message': str(exc)})
            session.adapter.close()
            session.emit({'type': 'agent.status', 'status': 'Fehler'})
            raise
        return session.snapshot()

    def get(self, session_id):
        with self.lock:
            if session_id not in self.items:
                raise ValueError('Sitzung nicht mehr beobachtbar. Bitte neu verbinden oder extern fortsetzen.')
            return self.items[session_id]

    def snapshot(self):
        with self.lock:
            return [session.snapshot() for session in self.items.values()]

    def send(self, session_id, message):
        if not isinstance(message, str) or not message.strip():
            raise ValueError('Die Nachricht darf nicht leer sein.')
        session = self.get(session_id)
        with session.condition:
            if session.disconnected:
                raise ValueError('Diese Verbindung wurde getrennt. Bitte eine neue Verbindung öffnen.')
            if session.busy:
                raise ValueError('Diese Sitzung arbeitet bereits oder wartet auf eine Eingabe.')
            session.busy = True
        session.emit({'type': 'agent.message.user', 'text': message, 'source': 'browser'})
        try:
            session.adapter.send(message)
        except Exception as exc:
            session.emit({'type': 'agent.error', 'message': str(exc)})
            session.emit({'type': 'agent.status', 'status': 'Fehler'})
            raise
        return {'accepted': True, 'session': session_id}

    def respond(self, session_id, request_id, response):
        session = self.get(session_id)
        request = session.interactions.get(str(request_id))
        if not request:
            raise ValueError('Die Rückfrage ist nicht mehr offen.')
        if not isinstance(response, dict):
            raise ValueError('Antwort muss ein JSON-Objekt sein.')
        session.adapter.respond(request.get('rpc_id', request_id), response)
        return {'accepted': True}

    def disconnect(self, session_id):
        session = self.get(session_id)
        session.disconnected = True
        session.adapter.close()
        return session.snapshot()

    def close(self):
        with self.lock:
            sessions = list(self.items.values())
        for session in sessions:
            session.adapter.close()
