"""Temporary local files and fictional people only; no real approval or execution."""
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from approval_audit import (CheckError, action_approval, parse_json, read_events, record_decision,
                            record_request, replay, summarize)
from validate_records import check

SUITE = Path(__file__).resolve().parents[1]
T = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


class ApprovalAuditTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from approval_key import use_test_key
        self.key = use_test_key(self)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / 'approvals.jsonl'
        self.artifact = self.root / 'website' / 'home.html'
        self.artifact.parent.mkdir()
        self.artifact.write_text('<h1>Fiktive Homepage</h1>', encoding='utf-8')
        bundle = json.loads((SUITE / 'beispiele/demo-freigabe-bundle.json').read_text())
        art = bundle['artifacts'][0]
        art.update(path='website/home.html', version=2, status='review',
                   sha256=hashlib.sha256(self.artifact.read_bytes()).hexdigest())
        for review in bundle['reviews']:
            review['artifact_version'] = 2
        self.request = dict(id='req-demo-home-v2', title='Website-Startseite',
                            summary='Fiktive Veröffentlichung der geprüften Startseite.',
                            requested_by='Website-Spezialist', requested_at=T.isoformat(),
                            artifact=art, action='publish', target='website:production',
                            reviews=bundle['reviews'])

    def start(self, request=None):
        return record_request(self.log, request or self.request, self.root, now=T)

    def decide(self, prior, decision='approved', **changes):
        args = dict(log=self.log, request_id=self.request['id'], decision=decision,
                    actor='Erika Beispiel', actor_role='Geschäftsführung',
                    occurred_at=(T + timedelta(minutes=1)).isoformat(),
                    evidence_ref='trusted-harness:fictional-human-response-1',
                    reason='Fiktive menschliche Entscheidung für den Test.',
                    previous_event_id=prior['id'], root=self.root, now=T + timedelta(minutes=2))
        args.update(changes)
        return record_decision(**args)

    def test_request_records_exact_file_and_remains_pending(self):
        event = self.start()
        check('approval-event', event)
        self.assertEqual(event['artifact_version'], 2)
        self.assertEqual(event['request']['artifact']['sha256'], hashlib.sha256(self.artifact.read_bytes()).hexdigest())
        row = summarize(self.log, now=T)[0]
        self.assertEqual(row['status'], 'pending')
        self.assertNotIn('action_approval_candidate', row)
        self.assertFalse(self.log.with_name('approvals.jsonl.lock').exists())

    def test_approval_uses_existing_contract_and_never_claims_execution(self):
        event = self.decide(self.start())
        candidate = action_approval(self.request, event)
        check('action-approval', candidate)
        self.assertEqual(candidate['authorizer'], 'Erika Beispiel')
        self.assertEqual(candidate['artifact_version'], 2)
        self.assertEqual(candidate['execution_status'], 'not_attempted')
        row = summarize(self.log, now=T + timedelta(minutes=3))[0]
        self.assertEqual(row['status'], 'approved')
        self.assertEqual(row['actor_role'], 'Geschäftsführung')
        self.assertEqual(row['recorded_at'], event['recorded_at'])

    def test_denial_and_changes_requested_are_distinct_terminal_decisions(self):
        for decision in ('denied', 'changes_requested'):
            with self.subTest(decision=decision):
                self.log = self.root / (decision + '.jsonl')
                first = self.start()
                self.decide(first, decision)
                self.assertEqual(summarize(self.log, now=T)[0]['status'], decision)
                prefix = self.log.read_bytes()
                with self.assertRaises(CheckError):
                    self.decide(first)
                self.assertEqual(self.log.read_bytes(), prefix)

    def test_revocation_appends_without_rewriting_prior_records(self):
        first = self.start()
        requested_bytes = self.log.read_bytes()
        approved = self.decide(first)
        approved_bytes = self.log.read_bytes()
        self.assertTrue(approved_bytes.startswith(requested_bytes))
        self.decide(approved, 'revoked', occurred_at=(T + timedelta(minutes=3)).isoformat(),
                    now=T + timedelta(minutes=4))
        self.assertTrue(self.log.read_bytes().startswith(approved_bytes))
        row = summarize(self.log, now=T + timedelta(minutes=5))[0]
        self.assertEqual(row['status'], 'revoked')
        self.assertNotIn('action_approval_candidate', row)
        self.assertEqual([e['type'] for e in read_events(self.log)], ['requested', 'approved', 'revoked'])

    def test_changed_file_missing_file_and_symlink_escape_cannot_be_approved(self):
        first = self.start()
        prefix = self.log.read_bytes()
        self.artifact.write_text('changed')
        with self.assertRaises(CheckError):
            self.decide(first)
        self.artifact.unlink()
        with self.assertRaises(FileNotFoundError):
            self.decide(first)
        self.artifact.symlink_to(self.root.parent)
        with self.assertRaises(CheckError):
            self.decide(first)
        self.assertEqual(self.log.read_bytes(), prefix)
        # Denial remains possible even after a file was changed or removed.
        self.decide(first, 'denied')

    def test_request_already_requires_real_file_hash(self):
        self.request['artifact']['sha256'] = '0' * 64
        with self.assertRaises(CheckError):
            self.start()
        self.assertFalse(self.log.exists())

    def test_approval_requires_g2_g3_and_no_blocking_review(self):
        for defect in ('no-g2', 'no-g3', 'blocked', 'pending-rights', 'not-checked'):
            with self.subTest(defect=defect):
                self.log = self.root / (defect + '.jsonl')
                request = copy.deepcopy(self.request)
                if defect == 'no-g2':
                    request['reviews'] = [r for r in request['reviews'] if r['dimension'] == 'legal']
                elif defect == 'no-g3':
                    request['reviews'] = [r for r in request['reviews'] if r['dimension'] != 'legal']
                elif defect == 'blocked':
                    request['reviews'][0].update(status='blocked', findings=[{'severity': 'major', 'message': 'Fiktive Sperre'}])
                elif defect == 'not-checked':
                    request['reviews'][0]['status'] = 'not_checked'
                else:
                    request['artifact']['rights_status'] = 'pending'
                first = self.start(request)
                prefix = self.log.read_bytes()
                with self.assertRaises(CheckError):
                    self.decide(first)
                self.assertEqual(self.log.read_bytes(), prefix)

    def test_budget_is_bound_to_request_and_preserved_in_decisions(self):
        self.request.update(action='spend', budget_limit=500, currency='EUR')
        first = self.start()
        approval = self.decide(first)
        self.assertEqual(approval['budget_limit'], 500)
        self.assertEqual(approval['currency'], 'EUR')
        changed = copy.deepcopy(read_events(self.log))
        changed[-1]['budget_limit'] = 501
        with self.assertRaises(CheckError):
            replay(changed)

    def test_spend_without_budget_and_invalid_currency_are_rejected(self):
        for fields in ({'action': 'spend'}, {'budget_limit': 500}, {'currency': 'EUR'},
                       {'budget_limit': float('nan'), 'currency': 'EUR'},
                       {'budget_limit': -1, 'currency': 'EUR'}, {'budget_limit': 500, 'currency': 'eur'}):
            with self.subTest(fields=fields), self.assertRaises(CheckError):
                self.start(dict(self.request, **fields))

    def test_human_identity_evidence_and_timezone_are_required(self):
        first = self.start()
        for changed in ({'actor': 'KI-Assistent'}, {'actor': '  '}, {'evidence_ref': ''},
                        {'occurred_at': '2026-10-27T09:01:00'}, {'reason': ''}):
            with self.subTest(changed=changed), self.assertRaises(CheckError):
                self.decide(first, **changed)
        self.assertEqual(len(read_events(self.log)), 1)

    def test_expiration_and_post_expiry_revocation(self):
        self.request['expires_at'] = (T + timedelta(minutes=5)).isoformat()
        first = self.start()
        approved = self.decide(first)
        row = summarize(self.log, now=T + timedelta(minutes=6))[0]
        self.assertEqual(row['status'], 'expired')
        self.assertNotIn('action_approval_candidate', row)
        self.decide(approved, 'revoked', occurred_at=(T + timedelta(minutes=7)).isoformat(),
                    now=T + timedelta(minutes=8))
        self.assertEqual(summarize(self.log, now=T + timedelta(minutes=9))[0]['status'], 'revoked')

    def test_expired_pending_request_cannot_be_approved(self):
        self.request['expires_at'] = (T + timedelta(minutes=1)).isoformat()
        first = self.start()
        with self.assertRaises(CheckError):
            self.decide(first)

    def test_duplicate_request_and_stale_confirmation_are_rejected(self):
        first = self.start()
        with self.assertRaises(CheckError):
            self.start()
        with self.assertRaises(CheckError):
            self.decide(first, previous_event_id='evt-not-the-one-presented')
        with self.assertRaises(CheckError):
            self.decide(first, 'revoked')

    def test_replay_rejects_subject_action_version_timestamp_or_chain_changes(self):
        first = self.start()
        self.decide(first)
        for fields in ({'artifact_version': 3}, {'artifact_sha256': 'b' * 64},
                       {'action': 'delete'}, {'target': 'other'}, {'previous_event_id': 'bad-chain'},
                       {'occurred_at': (T - timedelta(minutes=1)).isoformat()},
                       {'recorded_at': (T - timedelta(minutes=1)).isoformat()}):
            events = copy.deepcopy(read_events(self.log))
            events[-1].update(fields)
            with self.subTest(fields=fields), self.assertRaises(CheckError):
                replay(events)
        events = read_events(self.log)
        with self.assertRaises(CheckError):
            replay(events + [events[-1]])

    def test_corrupt_or_partial_log_is_not_silently_repaired(self):
        self.start()
        for tail in (b'{', b'\n', b'{"id":"duplicate","id":"keys"}\n'):
            log = self.root / ('bad-' + str(len(tail)) + '.jsonl')
            data = self.log.read_bytes() + tail
            log.write_bytes(data)
            with self.subTest(tail=tail), self.assertRaises((CheckError, ValueError)):
                record_request(log, dict(self.request, id='new-request'), self.root, now=T)
            self.assertEqual(log.read_bytes(), data)

    def test_existing_lock_and_concurrent_decisions_fail_closed(self):
        first = self.start()
        lock = self.log.with_name('approvals.jsonl.lock')
        lock.touch()
        with self.assertRaises(CheckError):
            self.decide(first)
        self.assertTrue(lock.exists())
        lock.unlink()
        def attempt(decision):
            try:
                self.decide(first, decision)
                return True
            except CheckError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, ('approved', 'denied')))
        self.assertEqual(sum(results), 1)
        self.assertEqual(len(read_events(self.log)), 2)

    def test_new_version_uses_new_request_and_earlier_decision_is_retained(self):
        first = self.start()
        self.decide(first, 'changes_requested')
        self.artifact.write_text('Version 3')
        next_request = copy.deepcopy(self.request)
        next_request.update(id='req-demo-home-v3')
        next_request['artifact'].update(version=3, sha256=hashlib.sha256(self.artifact.read_bytes()).hexdigest())
        next_request['reviews'] = []
        next_request["requested_at"] = (T + timedelta(minutes=3)).isoformat()
        record_request(self.log, next_request, self.root, now=T + timedelta(minutes=3))
        self.assertEqual([row['status'] for row in summarize(self.log, now=T)], ['changes_requested', 'pending'])

    def test_cli_roundtrip_and_read_only_status(self):
        request_file = self.root / 'request.json'
        request_file.write_text(json.dumps(self.request))
        command = [sys.executable, str(SUITE / 'tools/approval_audit.py')]
        # Fixed test clock is in the future on some developer machines, so use a historical instant.
        request = copy.deepcopy(self.request)
        request['requested_at'] = '2026-10-24T14:00:00+02:00'
        request_file.write_text(json.dumps(request))
        result = subprocess.run(command + ['request', '--request', str(request_file), '--root', str(self.root),
                                '--log', str(self.log)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        first = json.loads(result.stdout)
        decision_file = self.root / 'decision.json'
        decision_file.write_text(json.dumps(dict(request_id=request['id'], decision='approved',
            actor='Erika Beispiel', actor_role='Geschäftsführung', occurred_at='2026-10-24T14:01:00+02:00',
            evidence_ref='trusted-harness:fictional-response', reason='Fiktiv bestätigt', previous_event_id=first['id'])))
        result = subprocess.run(command + ['decide', '--decision', str(decision_file), '--root', str(self.root),
                                '--log', str(self.log)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('signature', json.loads(result.stdout))
        before = self.log.read_bytes()
        result = subprocess.run(command + ['status', '--log', str(self.log)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]['status'], 'approved')
        self.assertEqual(self.log.read_bytes(), before)
        result = subprocess.run(command + ['check', '--log', str(self.log)], capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout)['events'], 2)
        head = json.loads(subprocess.run(command + ['checkpoint', '--log', str(self.log)], capture_output=True, text=True).stdout)
        result = subprocess.run(command + ['check', '--log', str(self.log), '--expect', '%d:%s' % (head['events'], head['head'])],
                                capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout)['checkpoint'], 'pass')
        key_out = Path(tempfile.mkdtemp()) / 'new.key'
        self.addCleanup(lambda: key_out.unlink(missing_ok=True))
        created = json.loads(subprocess.run(command + ['keygen', '--out', str(key_out)], capture_output=True, text=True).stdout)
        self.assertEqual(oct(key_out.stat().st_mode & 0o777), '0o600'); self.assertEqual(len(created['key_id']), 16)
        self.assertNotEqual(subprocess.run(command + ['keygen', '--out', str(key_out)], capture_output=True, text=True).returncode, 0)

    def test_hash_chain_detects_edits_and_checkpoint_detects_truncation(self):
        from approval_audit import chain_head, verify_checkpoint
        request = copy.deepcopy(self.request)
        first = record_request(self.log, request, self.root)
        checkpoint = chain_head(self.log)
        record_decision(self.log, request['id'], 'denied', 'Erika Beispiel', request['requested_at'],
                        'trusted-harness:fictional', 'Fiktiv abgelehnt', first['id'], self.root, key=self.key)
        self.assertEqual(len(read_events(self.log)), 2)
        self.assertEqual(verify_checkpoint(self.log, checkpoint['events'], checkpoint['head'])['checkpoint'], 'pass')
        original = self.log.read_bytes()
        lines = original.split(b'\n')
        # Changing an earlier record breaks the link of the next one.
        self.log.write_bytes(lines[0].replace(b'"reason":"', b'"reason":"X') + b'\n' + b'\n'.join(lines[1:]))
        with self.assertRaises(CheckError):
            read_events(self.log)
        # Dropping the last record keeps a valid chain, but an external checkpoint notices.
        self.log.write_bytes(original)
        later = chain_head(self.log)
        self.log.write_bytes(lines[0] + b'\n')
        read_events(self.log)
        with self.assertRaises(CheckError):
            verify_checkpoint(self.log, later['events'], later['head'])

    def test_legacy_unchained_records_still_read_but_chain_cannot_be_dropped(self):
        request = copy.deepcopy(self.request)
        event = record_request(self.log, request, self.root)
        legacy = dict(event); legacy.pop('prev_hash')
        self.log.write_text(json.dumps(legacy, ensure_ascii=False, separators=(',', ':')) + '\n')
        record_decision(self.log, request['id'], 'denied', 'Erika Beispiel', request['requested_at'],
                        'trusted-harness:fictional', 'Fiktiv', event['id'], self.root, key=self.key)
        self.assertEqual(len(read_events(self.log)), 2)
        data = self.log.read_bytes().split(b'\n')
        second = json.loads(data[1]); second.pop('prev_hash')
        third = dict(second, id='evt-' + 'f' * 8)
        with self.assertRaises(CheckError):
            self.log.write_bytes(data[0] + b'\n' + data[1] + b'\n' + json.dumps(third).encode() + b'\n')
            read_events(self.log)

    def test_strict_json_and_symlink_log(self):
        for text in ('{"x":1,"x":2}', '{"x":NaN}'):
            with self.assertRaises(CheckError):
                parse_json(text)
        self.log.symlink_to(self.root / 'other.jsonl')
        with self.assertRaises(CheckError):
            self.start()

    def test_unicode_line_separators_remain_one_jsonl_record(self):
        self.request['summary'] = 'Fiktiv\u2028weiter\u2029Ende'
        self.start()
        self.assertEqual(len(read_events(self.log)), 1)
        self.assertEqual(read_events(self.log)[0]['reason'], self.request['summary'])

    def test_same_artifact_version_cannot_be_reassigned_to_changed_bytes(self):
        self.start()
        self.artifact.write_text('Andere Datei unter derselben Versionsnummer')
        request = copy.deepcopy(self.request)
        request.update(id='new-request-same-version')
        request['artifact']['sha256'] = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        with self.assertRaises(CheckError):
            self.start(request)
        self.assertEqual(len(read_events(self.log)), 1)

    def test_nested_contracts_and_future_reviews_are_checked(self):
        for defect in ('unknown-artifact-field', 'missing-hash', 'wrong-review-version',
                       'future-review', 'duplicate-review-id'):
            request = copy.deepcopy(self.request)
            if defect == 'unknown-artifact-field':
                request['artifact']['unknown'] = True
            elif defect == 'missing-hash':
                del request['artifact']['sha256']
            elif defect == 'wrong-review-version':
                request['reviews'][0]['artifact_version'] = 3
            elif defect == 'future-review':
                request['reviews'][0]['reviewed_at'] = (T + timedelta(hours=1)).isoformat()
            else:
                request['reviews'].append(copy.deepcopy(request['reviews'][0]))
            with self.subTest(defect=defect), self.assertRaises(CheckError):
                self.start(request)

    def test_committed_examples_have_expected_states_and_append_only_revocation(self):
        folder = SUITE / 'beispiele/approval-demo'
        original, revoked = folder / 'approvals-demo.jsonl', folder / 'approvals-revoked-demo.jsonl'
        self.assertTrue(revoked.read_bytes().startswith(original.read_bytes()))
        now = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
        self.assertEqual([row['status'] for row in summarize(original, now=now)], ['pending', 'approved', 'denied'])
        self.assertEqual([row['status'] for row in summarize(revoked, now=now)], ['pending', 'revoked', 'denied'])
        for row in summarize(original, now=now):
            if row['status'] == 'approved':
                check('action-approval', row['action_approval_candidate'])
