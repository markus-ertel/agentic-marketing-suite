"""Regression cases for approval reuse, budget scope and OS authority boundaries."""
import copy
import json
import os
from pathlib import Path
import stat
import hashlib
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_capability_runtime import approve
from runtime import CapabilityError, require_approval, run_once, snapshot_json
from test_export_platform import ADS
from export_platform import check_google_ads
import execution_authority as authority


class HardeningTests(unittest.TestCase):
    def setUp(self):
        from approval_key import use_test_key
        use_test_key(self)

    def test_operator_key_binding_rejects_an_agent_selected_signing_key(self):
        from approval_audit import CheckError, sign
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as keys:
            root=Path(folder);trusted=os.environ['SUITE_APPROVAL_KEY_FILE']
            log,plan,request,event=approve(root,{},'send','mail:test')
            attacker=Path(keys)/'attacker.key';attacker.write_bytes(b'fictional-attacker-key-'+b'x'*40);attacker.chmod(0o600)
            lines=log.read_text().splitlines();forged=json.loads(lines[-1])
            forged['signature']=sign(forged,attacker.read_bytes())
            log.write_text('\n'.join(lines[:-1]+[json.dumps(forged,separators=(',',':'))])+'\n')
            with patch.dict(os.environ,{'SUITE_APPROVAL_KEY_FILE':str(attacker)}), self.assertRaises(CheckError):
                require_approval(log,request['id'],root,plan,'send','mail:test',snapshot_json(plan)[1],key_path=trusted)

    def test_invalid_checkpoints_are_rejected(self):
        from approval_audit import CheckError, verify_checkpoint
        for count,head in ((-1,'0'*64),(0,'1'*64),(1,'not-a-hash')):
            with self.subTest(count=count),self.assertRaises(CheckError):verify_checkpoint('/nonexistent',count,head)

    def test_approval_cannot_be_reused_by_changing_key_or_journal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            log, plan, request, event = approve(root, {'fixture': True}, 'send', 'mail:test')
            approval = require_approval(log, request['id'], root, plan, 'send', 'mail:test', snapshot_json(plan)[1])
            journal = root / 'executions.jsonl'
            calls = []
            run_once(journal, 'first', 'mail.send', approval, lambda: calls.append(1) or {'status': 'accepted'})
            with self.assertRaisesRegex(CapabilityError, 'already used'):
                run_once(journal, 'second', 'mail.send', approval, lambda: calls.append(2))
            with self.assertRaisesRegex(CapabilityError, 'Execution log'):
                run_once(root / 'different.jsonl', 'third', 'mail.send', approval, lambda: calls.append(3))
            self.assertEqual(calls, [1])

    def test_started_failed_and_uncertain_approvals_require_new_approval(self):
        from runtime import append_execution
        for status in ('started', 'failed', 'uncertain'):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                log, plan, request, event = approve(root, {}, 'send', 'mail:test')
                approval = require_approval(log, request['id'], root, plan, 'send', 'mail:test', snapshot_json(plan)[1])
                journal = root / 'executions.jsonl'
                append_execution(journal, {'key': 'first', 'capability': 'mail.send',
                                          **{k: v for k, v in approval.items() if k != 'approval_log'}, 'status': status})
                with self.assertRaises(CapabilityError):
                    run_once(journal, 'second', 'mail.send', approval, lambda: self.fail('duplicate'))

    def test_ads_budget_counts_inclusive_days_and_leap_day(self):
        manifest = copy.deepcopy(ADS)
        manifest['budget']['daily_max'] = '300'
        self.assertTrue(check_google_ads(manifest))
        manifest['budget'].update(period_start='2028-02-28', period_end='2028-03-01', daily_max='100')
        self.assertEqual(check_google_ads(manifest), [])
        manifest['budget']['daily_max'] = '100.01'
        self.assertTrue(check_google_ads(manifest))
        manifest['budget'].update(period_start='2028-02-29', period_end='2028-02-29', daily_max='300')
        self.assertEqual(check_google_ads(manifest), [])

    def test_missing_admin_policy_blocks_external_execution(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(authority, 'POLICY', Path(folder) / 'missing'):
            with self.assertRaises((ValueError, OSError)):
                authority.require_execution_authority('approvals.jsonl', 'executions.jsonl', 'mail.send')

    def test_same_user_forged_and_unregistered_policies_fail(self):
        config = {'executor_uid': 501, 'agent_uid': 501, 'code_root': '/', 'approvals': []}
        fake = SimpleNamespace(read_text=lambda **kw: json.dumps(config))
        with patch.object(authority, 'POLICY', fake), patch.object(authority, 'protected', side_effect=lambda path, *a, **kw: Path(path) if isinstance(path, (str, Path)) else Path('/policy')), patch.object(os, 'getuid', return_value=501), patch.object(os, 'geteuid', return_value=501):
            with self.assertRaisesRegex(ValueError, 'dedicated executor'):
                authority.require_execution_authority('/approvals', '/executions', 'mail.send')
            config['agent_uid'] = 502
            with self.assertRaisesRegex(ValueError, 'not registered'):
                authority.require_execution_authority('/approvals', '/executions', 'mail.send')

    def test_policy_and_parent_ownership_and_permissions_are_checked(self):
        for uid, mode in ((501, stat.S_IFREG | 0o600), (0, stat.S_IFREG | 0o666), (0, stat.S_IFLNK | 0o777)):
            with self.subTest(uid=uid, mode=mode), patch.object(Path, 'lstat', return_value=SimpleNamespace(st_uid=uid, st_mode=mode)):
                with self.assertRaises(ValueError):
                    authority.protected('/etc/agentic-marketing-suite/executor.json', {0})

    def test_registered_operator_can_use_only_the_canonical_journal(self):
        config = {'executor_uid':501, 'agent_uid':502, 'code_root':'/', 'approval_key_file':'/protected/key',
                  'approvals':[{'path':'/protected/approvals.jsonl','capabilities':['mail.send']}]}
        fake = SimpleNamespace(read_text=lambda **kw:json.dumps(config))
        with patch.object(authority,'POLICY',fake),patch.object(authority,'protected',side_effect=lambda path,*a,**kw:Path(path) if isinstance(path,(str,Path)) else Path('/policy')),patch.object(os,'getuid',return_value=501),patch.object(os,'geteuid',return_value=501),patch.object(Path,'stat',return_value=SimpleNamespace(st_mode=0o600)):
            self.assertEqual(authority.require_execution_authority('/protected/approvals.jsonl','/protected/executions.jsonl','mail.send'),config)
            with self.assertRaisesRegex(ValueError,'canonical'):
                authority.require_execution_authority('/protected/approvals.jsonl','/other.jsonl','mail.send')
            with self.assertRaisesRegex(ValueError,'not registered'):
                authority.require_execution_authority('/protected/approvals.jsonl','/protected/executions.jsonl','website.sftp')
