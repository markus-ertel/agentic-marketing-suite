from .base import Adapter


class CodexAppServer(Adapter):
    capabilities = {'streaming': True, 'resume': True, 'interactions': True}
    notice = 'App Server; externe Rückfragen werden mit ihrem Originalinhalt durchgereicht.'

    def connect(self):
        self.start()
        self.request({'method': 'initialize', 'params': {'clientInfo': {'name': 'agentic_marketing_dashboard', 'title': 'Agentic Marketing Dashboard', 'version': '0.1.0'}}})
        self.write({'method': 'initialized', 'params': {}})
        params = {'cwd': str(self.cwd)}
        method = 'thread/start'
        if self.external_id:
            method = 'thread/resume'
            params['threadId'] = self.external_id
        result = self.request({'method': method, 'params': params}, timeout=60)
        self.external_id = result['thread']['id']
        self.event('session', external_id=self.external_id, model=result.get('model'))
        thread_status = result['thread'].get('status', {}).get('type', 'idle')
        self.status('arbeitet' if thread_status == 'active' else 'bereit' if thread_status == 'idle' else 'unbekannt')

    def send(self, message):
        self.request({'method': 'turn/start', 'params': {'threadId': self.external_id, 'input': [{'type': 'text', 'text': message}]}})

    def handle(self, record):
        method, params = record.get('method'), record.get('params', {})
        if 'id' in record and method:
            self.status('wartet auf Eingabe')
            data = {'request_id': str(record['id']), 'rpc_id': record['id'], 'request': {'method': method, 'params': params}}
            if method in ('item/commandExecution/requestApproval', 'item/fileChange/requestApproval'):
                data['decisions'] = ['accept', 'decline', 'cancel']
            self.event('input_requested', **data)
        elif method == 'turn/started':
            self.status('arbeitet')
        elif method == 'item/agentMessage/delta':
            self.event('message.delta', text=params.get('delta', ''), item_id=params.get('itemId'))
        elif method == 'item/completed':
            item = params.get('item', {})
            if item.get('type') == 'agentMessage':
                self.event('message.final', text=item.get('text', ''), item_id=item.get('id'))
        elif method == 'turn/completed':
            turn = params.get('turn', {})
            outcome = turn.get('status')
            self.event('turn_end', outcome=outcome)
            if outcome == 'failed':
                self.event('error', message=str(turn.get('error') or 'Codex-Turn fehlgeschlagen.'))
            self.status('abgeschlossen' if outcome == 'completed' else 'Fehler' if outcome == 'failed' else 'unbekannt')
        elif method == 'error':
            self.event('error', message=str(params.get('error', params)))
            if not params.get('willRetry'):
                self.status('Fehler')
        elif method == 'serverRequest/resolved':
            self.event('input_resolved', request_id=str(params.get('requestId')))
        elif method == 'thread/status/changed':
            kind = params.get('status', {}).get('type')
            if kind == 'active':
                self.status('arbeitet')

    def respond(self, request_id, response):
        # Preserve JSON-RPC ID type, tracked by Sessions from the original request.
        self.write({'id': request_id, 'result': response})
        self.event('input_resolved', request_id=str(request_id))
        self.status('unbekannt')
