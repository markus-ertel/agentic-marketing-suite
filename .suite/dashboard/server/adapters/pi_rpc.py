from .base import Adapter


class PiRPC(Adapter):
    capabilities = {'streaming': True, 'resume': True, 'interactions': True}
    notice = 'Wiederaufnahme über Pi-Sessiondatei; Abschluss erst bei agent_settled.'

    def connect(self):
        command = list(self.profile['command'])
        if self.external_id:
            command += ['--session', self.external_id]
        self.failed = False
        self.start(command)
        info = self.request({'type': 'get_state'})
        self.external_id = info.get('sessionId')
        model = info.get('model') or {}
        self.event('session', external_id=self.external_id, model=model.get('id'), session_file=info.get('sessionFile'))
        self.status('arbeitet' if info.get('isStreaming') or info.get('isCompacting') else 'bereit')

    def send(self, message):
        self.failed = False
        result = self.request({'type': 'prompt', 'message': message})
        # Prompt acceptance is not completion or proof that model work started.
        if result.get('disposition') == 'handled':
            self.event('turn_end', outcome='handled')
            self.status('bereit')

    def handle(self, record):
        kind = record.get('type')
        if kind == 'agent_start':
            self.status('arbeitet')
        elif kind == 'message_update':
            update = record.get('assistantMessageEvent', {})
            if update.get('type') == 'text_delta':
                self.event('message.delta', text=update.get('delta', ''))
        elif kind == 'message_end':
            message = record.get('message', {})
            if message.get('role') == 'assistant' and message.get('stopReason') in ('error', 'aborted'):
                self.failed = True
                self.event('error', message=message.get('errorMessage') or 'Pi-Turn fehlgeschlagen oder abgebrochen.')
        elif kind == 'agent_settled':
            self.event('turn_end', outcome='failed' if self.failed else 'completed')
            self.status('Fehler' if self.failed else 'abgeschlossen')
        elif kind == 'extension_ui_request':
            if record.get('method') in ('select', 'confirm', 'input', 'editor'):
                self.status('wartet auf Eingabe')
                self.event('input_requested', request_id=record['id'], request=record)
        elif kind == 'response' and record.get('success') is False:
            self.event('error', message=str(record.get('error')))
            self.status('Fehler')

    def respond(self, request_id, response):
        self.write({**response, 'id': request_id, 'type': 'extension_ui_response'})
        self.event('input_resolved', request_id=request_id)
        self.status('unbekannt')
