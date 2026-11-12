"""Read-only approval display tests; fictional audit logs, no real human decisions or agents."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard_auth import authenticate
from server.app import DashboardServer, load_config
from server.approvals import ApprovalView

DEMO = Path(__file__).resolve().parents[3] / '.suite/beispiele/approval-demo'
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)


class ApprovalViewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / 'approvals.jsonl'
        self.log.write_bytes((DEMO / 'approvals-demo.jsonl').read_bytes())
        self.source = {'id': 'demo', 'label': 'Fiktive Beispiele', 'path': str(self.log)}
        self.view = ApprovalView([self.source])

    def test_only_display_fields_are_exposed_and_no_files_are_written(self):
        before = {path.name: path.read_bytes() for path in self.root.iterdir()}
        data = self.view.snapshot()
        self.assertEqual([row['status'] for row in data['items']], ['pending', 'approved', 'denied'])
        self.assertEqual(data['sources'], [{'id': 'demo', 'label': 'Fiktive Beispiele', 'status': 'ok'}])
        self.assertEqual(data['items'][0]['event_type'], 'requested')
        self.assertEqual(data['items'][1]['actor_role'], 'Geschäftsführung')
        self.assertEqual(data['items'][2]['budget_limit'], 500)
        self.assertEqual(data['items'][2]['currency'], 'EUR')
        for row in data['items']:
            self.assertNotIn('action_approval_candidate', row)
            self.assertNotIn('evidence_ref', row)
            self.assertNotIn('artifact_sha256', row)
        self.assertNotIn(str(self.log), json.dumps(data))
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.root.iterdir()})

    def test_revocation_is_reflected_on_the_next_read(self):
        self.assertEqual(self.view.snapshot()['items'][1]['status'], 'approved')
        self.log.write_bytes((DEMO / 'approvals-revoked-demo.jsonl').read_bytes())
        self.assertEqual(self.view.snapshot()['items'][1]['status'], 'revoked')

    def test_missing_corrupt_and_locked_sources_never_keep_old_positive_status(self):
        self.assertEqual(len(self.view.snapshot()['items']), 3)
        self.log.unlink()
        data = self.view.snapshot()
        self.assertEqual(data['items'], [])
        self.assertEqual(data['sources'][0]['status'], 'unavailable')
        self.assertFalse(self.log.exists())
        self.log.write_text('{"partial":')
        self.assertEqual(self.view.snapshot()['items'], [])
        self.assertEqual(self.view.snapshot()['sources'][0]['status'], 'invalid')
        self.log.write_bytes((DEMO / 'approvals-demo.jsonl').read_bytes())
        lock = self.log.with_name(self.log.name + '.lock')
        lock.touch()
        self.assertEqual(self.view.snapshot()['items'], [])
        self.assertEqual(self.view.snapshot()['sources'][0]['status'], 'updating')
        self.assertTrue(lock.exists())

    def test_empty_unconfigured_and_independent_sources(self):
        self.assertEqual(ApprovalView([]).snapshot(), {'configured': False, 'sources': [], 'items': []})
        self.log.write_text('')
        data = self.view.snapshot()
        self.assertTrue(data['configured'])
        self.assertEqual(data['items'], [])
        self.assertEqual(data['sources'][0]['status'], 'ok')
        self.log.write_bytes((DEMO / 'approvals-demo.jsonl').read_bytes())
        sources = [self.source, {'id': 'missing', 'label': 'Anderer Vorgang', 'path': str(self.root / 'missing.jsonl')}]
        data = ApprovalView(sources).snapshot()
        self.assertEqual(len(data['items']), 3)
        self.assertEqual(data['sources'][1]['status'], 'unavailable')
        self.assertTrue(all(row['source_id'] == 'demo' for row in data['items']))

    def test_symlink_large_log_and_read_error_are_not_exposed(self):
        self.log.unlink()
        self.log.symlink_to(DEMO / 'approvals-demo.jsonl')
        self.assertEqual(self.view.snapshot()['sources'][0]['status'], 'invalid')
        self.log.unlink()
        self.log.write_bytes((DEMO / 'approvals-demo.jsonl').read_bytes())
        with patch('server.approvals.MAX_LOG_BYTES', 20):
            self.assertEqual(self.view.snapshot()['sources'][0]['status'], 'invalid')
        with patch('server.approvals.summarize', side_effect=PermissionError('/private/secret/path')):
            data = self.view.snapshot()
            self.assertEqual(data['items'], [])
            self.assertNotIn('/private/secret/path', json.dumps(data))

    def test_configuration_is_explicit_local_and_resolves_relative_to_config(self):
        path = self.root / 'config.json'
        value = {'suite': {'root': '.'}, 'approvals': {'logs': [dict(self.source, path='approvals.jsonl')]}}
        path.write_text(json.dumps(value))
        config = load_config(path)
        self.assertEqual(Path(config['approvals']['logs'][0]['path']).resolve(), self.log.resolve())
        path.write_text(json.dumps({'suite': {'root': '.'}}))
        self.assertEqual(load_config(path)['approvals']['logs'], [])
        for invalid in ([], {'logs': 'bad'}, {'logs': ['file.jsonl']},
                        {'logs': [dict(self.source, path='https://example.invalid/approvals.jsonl')]},
                        {'logs': [dict(self.source, path='.env')]},
                        {'logs': [dict(self.source, id='../private')]},
                        {'logs': [self.source, self.source]},
                        {'logs': [self.source, dict(self.source, id='another')]},
                        {'logs': [dict(self.source, label=' ')]}):
            value['approvals'] = invalid
            path.write_text(json.dumps(value))
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                load_config(path)


    def test_expiry_and_changes_requested_are_display_states(self):
        from approval_audit import summarize
        events = [json.loads(line) for line in self.log.read_text().splitlines()]
        events[1]['request']['expires_at'] = '2026-10-27T10:00:00+01:00'
        events[-1]['type'] = 'changes_requested'
        self.log.write_text(''.join(json.dumps(event) + '\n' for event in events))
        with patch('server.approvals.summarize', side_effect=lambda path, max_bytes: summarize(path, now=NOW, max_bytes=max_bytes)):
            self.assertEqual([row['status'] for row in self.view.snapshot()['items']], ['pending', 'expired', 'changes_requested'])



class ApprovalHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.log = cls.root / 'approvals.jsonl'
        cls.log.write_bytes((DEMO / 'approvals-demo.jsonl').read_bytes())
        cls.config = {'server': {'host': '127.0.0.1', 'port': 0},
                      'suite': {'root': str(cls.root)}, 'viewer': {'max_inline_file_mb': 1},
                      'approvals': {'logs': [{'id': 'demo', 'label': 'Fiktive Beispiele', 'path': str(cls.log)}]}}
        cls.server = DashboardServer(cls.config)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:' + str(cls.server.server_port)
        authenticate(cls.server)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def test_endpoint_is_read_only_and_does_not_accept_browser_chosen_paths(self):
        before = self.log.read_bytes()
        with urlopen(self.base + '/api/approvals') as response:
            data = json.load(response)
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual([row['status'] for row in data['items']], ['pending', 'approved', 'denied'])
        with urlopen(self.base + '/api/approvals?path=.git/config') as response:
            self.assertEqual(json.load(response), data)
        with urlopen(self.base + '/api/config') as response:
            self.assertNotIn('approvals', json.load(response))
        for route in ('/api/approvals', '/api/approvals/approve', '/api/approvals/revoke'):
            request = Request(self.base + route, data=b'{}', headers={'Content-Type': 'application/json', 'Origin': self.base})
            with self.subTest(route=route), self.assertRaises(HTTPError) as error:
                urlopen(request)
            self.assertEqual(error.exception.code, 405)
        self.assertEqual(self.log.read_bytes(), before)
        self.assertFalse(self.log.with_name('approvals.jsonl.lock').exists())

    def test_host_guard_applies_to_approval_display(self):
        request = Request(self.base + '/api/approvals', headers={'Host': 'attacker.invalid:8765'})
        with self.assertRaises(HTTPError) as error:
            urlopen(request)
        self.assertEqual(error.exception.code, 403)
