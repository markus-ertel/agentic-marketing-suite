from .base import Adapter


class CodexAppServer(Adapter):
    capabilities = {'streaming': True, 'resume': True, 'interactions': True}
    notice = 'App Server; externe Rückfragen werden mit ihrem Originalinhalt durchgereicht.'

    MAX_DIFF = 200_000

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # File changes arrive as items before their approval request; keep them to show what is approved.
        self.file_changes = {}

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
            if method == 'item/fileChange/requestApproval':
                # Never ask for a blind approval: attach paths and diffs, or say they are unknown.
                data['changes'] = self.file_changes.get(params.get('itemId'))
                changes = data['changes']
                if not changes or any(not change['path'] or not change['diff'] or change.get('truncated') for change in changes):
                    data['decisions'] = ['decline', 'cancel']
            self.event('input_requested', **data)
        elif method == 'turn/started':
            self.file_changes.clear()
            self.status('arbeitet')
        elif method == 'item/agentMessage/delta':
            self.event('message.delta', text=params.get('delta', ''), item_id=params.get('itemId'))
        elif method in ('item/started', 'item/updated') and params.get('item', {}).get('type') == 'fileChange':
            item = params['item']
            changes = []
            for change in item.get('changes') or []:
                if isinstance(change, dict):
                    kind = change.get('kind')
                    changes.append({'path': str(change.get('path', '')),
                                    'kind': str(kind.get('type', '') if isinstance(kind, dict) else kind or ''),
                                    'diff': str(change.get('diff', ''))[:self.MAX_DIFF],
                                    'truncated': len(str(change.get('diff', ''))) > self.MAX_DIFF})
            if len(self.file_changes) < 100 or item.get('id') in self.file_changes:
                self.file_changes[item.get('id')] = changes
        elif method == 'item/completed':
            item = params.get('item', {})
            self.file_changes.pop(item.get('id'), None)
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
