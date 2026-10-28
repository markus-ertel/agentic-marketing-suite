"""Fictional reviewed feedback; temp stores only, no real consent, identity or external action."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE / 'tools'))
import import_feedback as feedback
from build_context import compose, validate_request

T = datetime(2026, 10, 28, 10, tzinfo=timezone.utc)
EXAMPLE = json.loads((MODULE / 'beispiele/feedback-intake-demo.json').read_text())


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = self.root / 'wissen'
        self.intake = self.root / 'intake.json'
        self.proposal = self.root / 'proposal.json'
        self.decision = self.root / 'decision.json'
        self.intake.write_bytes(feedback.canonical(EXAMPLE))

    def prepare(self, value=None, proposal=None, now=T):
        if value is not None:
            self.intake.write_bytes(feedback.canonical(value))
        path = proposal or self.proposal
        feedback.prepare(self.intake, self.store, path, now=now)
        return path

    def approve(self, proposal=None, **changes):
        path = proposal or self.proposal
        body = json.loads(path.read_text())
        value = dict(decision_id='decision-' + body['proposal_id'], decision='approved', decider='Erika Beispiel',
                     decided_at=(T + timedelta(minutes=1)).isoformat(), claim_refs=[item['claim_id'] for item in body['claims']],
                     source_refs=[item['source_id'] for item in body['sources']],
                     proposal_sha256=feedback.sha(path.read_bytes()), confirmation_ref='demo:trusted-human-confirmation')
        value.update(changes)
        self.decision.write_bytes(feedback.canonical(value))
        return self.decision

    def apply(self, proposal=None):
        return feedback.apply(proposal or self.proposal, self.decision, self.store, True, now=T+timedelta(minutes=2))

    def initialized(self):
        self.prepare()
        self.approve()
        return self.apply()

    def revision(self):
        state, reference = feedback.read_store(self.store)
        intake = deepcopy(EXAMPLE)
        source = deepcopy(intake['sources'][0])
        source.update(source_id='src-demo-feedback-002', locator='demo:independent-feedback-002')
        intake['sources'] = [source]
        claim = deepcopy(state['claims'][0])
        claim['source_refs'].append(source['source_id'])
        intake['claims'] = [claim]
        proposal = self.prepare(intake, self.root / 'revision.json')
        self.approve(proposal)
        return proposal

    def test_prepare_does_not_import_or_change_input_and_check_is_read_only(self):
        before = self.intake.read_bytes()
        result = feedback.prepare(self.intake, self.store, self.proposal, now=T)
        self.assertEqual(result['status'], 'proposed')
        self.assertFalse(self.store.exists())
        self.assertEqual(self.intake.read_bytes(), before)
        self.assertEqual(self.proposal.stat().st_mode & 0o777, 0o600)
        self.assertEqual(feedback.main(['check', '--proposal', str(self.proposal), '--store', str(self.store)]), 0)
        self.assertFalse(self.store.exists())
        with self.assertRaises(FileExistsError):
            feedback.prepare(self.intake, self.store, self.proposal, now=T)

    def test_no_attestation_rejection_wrong_scope_hash_and_ai_cannot_apply(self):
        self.prepare()
        self.approve()
        with self.assertRaises(ValueError):
            feedback.apply(self.proposal, self.decision, self.store, now=T+timedelta(minutes=2))
        for changes in ({'decision':'rejected'}, {'proposal_sha256':'a'*64}, {'confirmation_ref':''},
                        {'decider':'AI assistant'}, {'claim_refs':['another-claim']}, {'source_refs':[]},
                        {'decided_at':(T-timedelta(minutes=1)).isoformat()}):
            with self.subTest(changes=changes):
                self.approve(**changes)
                with self.assertRaises(ValueError):
                    self.apply()
                self.assertFalse(self.store.exists())

    def test_import_creates_consistent_private_snapshot_and_replay_is_noop(self):
        result = self.initialized()
        state, pointer = feedback.read_store(self.store)
        self.assertEqual(result['snapshot'], pointer)
        self.assertEqual(len(state['claims']), 1)
        self.assertEqual(state['claims'][0]['status'], 'hypothesis')
        self.assertEqual(state['claims'][0]['visibility'], 'restricted')
        self.assertEqual(len(state['decisions']), 1)
        self.assertEqual([event['event_type'] for event in state['events']], ['claim.created','decision.recorded'])
        files = {p.relative_to(self.store):p.read_bytes() for p in self.store.rglob('*') if p.is_file()}
        self.assertEqual(self.apply()['status'], 'already_applied')
        self.assertEqual(files, {p.relative_to(self.store):p.read_bytes() for p in self.store.rglob('*') if p.is_file()})
        for p in self.store.rglob('*'):
            self.assertEqual(p.stat().st_mode & 0o777, 0o700 if p.is_dir() else 0o600)

    def test_revision_preserves_ids_evidence_previous_snapshot_and_events(self):
        first = self.initialized()['snapshot']
        old_state, _ = feedback.read_store(self.store)
        proposal = self.revision()
        self.apply(proposal)
        state, second = feedback.read_store(self.store)
        self.assertNotEqual(first, second)
        self.assertEqual(len(state['claims']), 1)
        self.assertEqual(state['claims'][0]['version'], 2)
        self.assertEqual(len(state['claims'][0]['source_refs']), 2)
        self.assertEqual(state['events'][:2], old_state['events'])
        self.assertEqual(state['events'][2]['event_type'], 'claim.revised')
        self.assertEqual(len(state['decisions']), 2)
        old = self.store / 'generations' / first['generation'] / 'claims.jsonl'
        self.assertEqual(json.loads(old.read_text())['version'], 1)
        self.assertTrue((self.store / 'proposals' / (feedback.sha(proposal.read_bytes())+'.json')).is_file())

    def test_stale_parallel_proposal_cannot_overwrite_a_new_version(self):
        self.prepare()
        parallel = self.prepare(proposal=self.root / 'parallel.json')
        self.approve()
        self.apply()
        pointer = (self.store / 'CURRENT.json').read_bytes()
        self.approve(parallel)
        with self.assertRaises(ValueError):
            self.apply(parallel)
        self.assertEqual(pointer, (self.store / 'CURRENT.json').read_bytes())

    def test_duplicate_decision_id_and_modified_proposal_block(self):
        self.initialized()
        first_decision = json.loads(self.decision.read_text())['decision_id']
        revision = self.revision()
        value = json.loads(self.decision.read_text())
        value['decision_id'] = first_decision
        self.decision.write_bytes(feedback.canonical(value))
        with self.assertRaises(ValueError):self.apply(revision)
        self.approve(revision)
        revision.write_bytes(revision.read_bytes()+b' ')
        with self.assertRaises(ValueError):self.apply(revision)

    def test_invalid_or_unreviewed_intake_never_creates_store_or_proposal(self):
        invalid = []
        for key in ('usage_review_ref','deidentification_review_ref'):
            item = deepcopy(EXAMPLE);item['origin'].pop(key);invalid.append(item)
        for status in ('verified','declared','planned'):
            item = deepcopy(EXAMPLE);item['claims'][0]['status']=status;invalid.append(item)
        item=deepcopy(EXAMPLE);item['sources'][0]['visibility']='shared';invalid.append(item)
        item=deepcopy(EXAMPLE);item['claims'][0]['visibility']='public';invalid.append(item)
        item=deepcopy(EXAMPLE);item['claims']*=6;invalid.append(item)
        item=deepcopy(EXAMPLE);item['claims'][0]['source_refs']=['missing'];invalid.append(item)
        item=deepcopy(EXAMPLE);item['sources']*=2;invalid.append(item)
        for item in invalid:
            with self.subTest(item=item), self.assertRaises(ValueError):self.prepare(item)
            self.assertFalse(self.store.exists())
            self.assertFalse(self.proposal.exists())

    def test_provenance_cannot_be_removed_and_existing_sources_cannot_change(self):
        self.initialized()
        state, _ = feedback.read_store(self.store)
        intake = deepcopy(EXAMPLE)
        intake['claims'] = [state['claims'][0]]
        intake['sources'][0]['description'] = 'Changed provenance under the same ID'
        with self.assertRaises(ValueError):self.prepare(intake, self.root/'bad-source.json')
        intake = deepcopy(EXAMPLE)
        intake['sources'][0]['source_id']='new-source'
        intake['claims'][0]['source_refs']=['new-source']
        with self.assertRaises(ValueError):self.prepare(intake, self.root/'bad-provenance.json')

    def test_failure_before_pointer_switch_preserves_current_and_retry_is_safe(self):
        first = self.initialized()['snapshot']
        proposal = self.revision()
        with patch.object(feedback.os, 'replace', side_effect=OSError('simulated interruption')):
            with self.assertRaises(OSError):self.apply(proposal)
        self.assertEqual(feedback.read_store(self.store)[1], first)
        self.assertFalse((self.store/feedback.LOCK).exists())
        self.assertEqual(self.apply(proposal)['status'], 'applied')
        self.assertEqual(feedback.read_store(self.store)[0]['claims'][0]['version'], 2)

    def test_failure_after_switch_is_reconciled_by_exact_replay(self):
        self.initialized()
        proposal = self.revision()
        original=feedback.sync_directory
        def sync(path):
            if path==self.store.resolve():raise OSError('simulated post-publication sync failure')
            original(path)
        with patch.object(feedback,'sync_directory',side_effect=sync):
            with self.assertRaises(OSError):self.apply(proposal)
        self.assertEqual(self.apply(proposal)['status'], 'already_applied')
        self.assertEqual(feedback.read_store(self.store)[0]['claims'][0]['version'], 2)

    def test_locks_corruption_and_symlinks_never_yield_a_trusted_snapshot(self):
        pointer = self.initialized()['snapshot']
        lock = self.store/feedback.LOCK
        lock.touch()
        with self.assertRaises(ValueError):feedback.read_store(self.store)
        with self.assertRaises(FileExistsError):self.apply()
        lock.unlink()
        file = self.store/'generations'/pointer['generation']/'claims.jsonl'
        before=file.read_bytes();file.write_bytes(before+b' ')
        with self.assertRaises(ValueError):feedback.read_store(self.store)
        file.write_bytes(before)
        other=self.root/'outside.jsonl';other.write_bytes(before)
        file.unlink();file.symlink_to(other)
        with self.assertRaises(ValueError):feedback.read_store(self.store)

    def test_legacy_bootstrap_preserves_flat_records_and_binds_all_referenced_sources(self):
        self.store.mkdir()
        legacy=deepcopy(EXAMPLE)
        legacy['claims'][0]['claim_id']='legacy-claim'
        legacy['sources'][0]['source_id']='legacy-source'
        legacy['claims'][0]['source_refs']=['legacy-source']
        for key in ('claims','sources'):
            (self.store/(key+'.jsonl')).write_text(''.join(json.dumps(item)+'\n' for item in legacy[key]))
        originals = {p.name:p.read_bytes() for p in self.store.iterdir()}
        intake=deepcopy(EXAMPLE)
        intake['claims'][0]['source_refs'].append('legacy-source')
        self.prepare(intake)
        body=json.loads(self.proposal.read_text())
        self.assertIn('legacy-source',body['base_source_sha256'])
        self.approve()
        self.apply()
        state,_=feedback.read_store(self.store)
        self.assertEqual(len(state['claims']),2)
        for name,data in originals.items():self.assertEqual((self.store/name).read_bytes(),data)

    def test_explicit_hypothesis_analysis_respects_visibility_and_keeps_status(self):
        self.initialized()
        state,_=feedback.read_store(self.store)
        args=(state['claims'],state['sources'],'marketing','Review customer language',['customer_feedback'],'restricted','2026-10-28',8000)
        self.assertEqual(compose(*args)['claims'],[])
        included=compose(*args,include_hypotheses=True)
        self.assertEqual(included['claims'][0]['status'],'hypothesis')
        self.assertEqual(included['claims'][0]['source_refs'],EXAMPLE['claims'][0]['source_refs'])
        self.assertTrue(any('Hypotheses' in line for line in included['limitations']))
        changed=list(args);changed[5]='shared'
        self.assertEqual(compose(*changed,include_hypotheses=True)['claims'],[])
        changed[5]='public'
        with self.assertRaises(ValueError):compose(*changed,include_hypotheses=True)
        changed[5]='restricted';changed[4]=['other-topic']
        self.assertEqual(compose(*changed,include_hypotheses=True)['claims'],[])

    def test_context_cli_reads_the_atomic_store_and_rejects_mixed_request_options(self):
        pointer=self.initialized()['snapshot']
        command=[sys.executable,str(MODULE/'tools/build_context.py'),'--store',str(self.store),
                 '--requester','branding','--purpose','Fictional analysis','--topics','customer_feedback',
                 '--visibility','restricted','--as-of','2026-10-28','--include-hypotheses']
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        pack=json.loads(result.stdout)
        self.assertTrue(pack['claims'])
        self.assertIn(pointer['generation'],pack['source_snapshot'])
        request=dict(request_id='demo-request',requester='marketing',purpose='Hypothesis analysis',
                     topics=['customer_feedback'],max_characters=8000,visibility_max='restricted',
                     as_of='2026-10-28',include_hypotheses=True)
        validate_request(request)
        path=self.root/'request.json';path.write_text(json.dumps(request))
        base=[sys.executable,str(MODULE/'tools/build_context.py'),'--store',str(self.store),'--request',str(path)]
        result=subprocess.run(base,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['request_id'],'demo-request')
        self.assertNotEqual(subprocess.run(base+['--include-hypotheses'],capture_output=True).returncode,0)
        request['include_hypotheses']='yes'
        with self.assertRaises(ValueError):validate_request(request)

    def test_duplicate_json_keys_and_oversized_inputs_rejected(self):
        self.intake.write_text('{"origin":1,"origin":2}')
        with self.assertRaises(ValueError):self.prepare()
        self.intake.write_bytes(feedback.canonical(EXAMPLE))
        with patch.object(feedback,'MAX_BYTES',10), self.assertRaises(ValueError):self.prepare()


    def test_full_cli_prepare_apply_and_replay_with_fictional_confirmation(self):
        base=[sys.executable,str(MODULE/'tools/import_feedback.py')]
        prepared=subprocess.run(base+['prepare','--intake',str(self.intake),'--store',str(self.store),'--out',str(self.proposal)],capture_output=True,text=True)
        self.assertEqual(prepared.returncode,0,prepared.stderr)
        body=json.loads(self.proposal.read_text())
        self.approve(decided_at=body['created_at'])
        apply=base+['apply','--proposal',str(self.proposal),'--decision',str(self.decision),'--store',str(self.store)]
        rejected=subprocess.run(apply,capture_output=True,text=True)
        self.assertEqual(rejected.returncode,2)
        self.assertFalse(self.store.exists())
        imported=subprocess.run(apply+['--harness-authorized'],capture_output=True,text=True)
        self.assertEqual(imported.returncode,0,imported.stderr)
        self.assertEqual(json.loads(imported.stdout)['status'],'applied')
        replayed=subprocess.run(apply+['--harness-authorized'],capture_output=True,text=True)
        self.assertEqual(replayed.returncode,0,replayed.stderr)
        self.assertEqual(json.loads(replayed.stdout)['status'],'already_applied')

    def test_referenced_legacy_evidence_change_invalidates_prepared_proposal(self):
        self.store.mkdir()
        existing=deepcopy(EXAMPLE['sources'][0]);existing['source_id']='previous-source'
        (self.store/'sources.jsonl').write_text(json.dumps(existing)+'\n')
        (self.store/'claims.jsonl').write_text('')
        intake=deepcopy(EXAMPLE)
        intake['claims'][0]['source_refs'].append(existing['source_id'])
        self.prepare(intake)
        self.approve()
        existing['description']='Different evidence after preparation'
        (self.store/'sources.jsonl').write_text(json.dumps(existing)+'\n')
        with self.assertRaises(ValueError):self.apply()
        self.assertFalse((self.store/'CURRENT.json').exists())

    def test_library_output_and_dangling_legacy_symlinks_are_blocked(self):
        self.intake.write_bytes(feedback.canonical(EXAMPLE))
        private=self.root/'.business-dna';private.mkdir()
        with self.assertRaises(ValueError):feedback.prepare(self.intake,private/'store',self.proposal,now=T)
        with self.assertRaises(ValueError):feedback.prepare(self.intake,self.store,private/'proposal.json',now=T)
        self.store.mkdir()
        (self.store/'claims.jsonl').symlink_to(self.root/'missing')
        with self.assertRaises(ValueError):feedback.read_store(self.store,allow_empty=True)


if __name__=='__main__':unittest.main()
