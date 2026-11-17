import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'.suite/capabilities'))
sys.path.insert(0,str(ROOT/'.suite/tools'))
import os
from unittest.mock import patch
from approval_audit import CheckError
from runtime import CapabilityError, append_execution, bound_execution_log, require_approval, run_once, snapshot_json
from approval_audit import load_key, record_request, record_decision
sys.path.insert(0,str(Path(__file__).resolve().parent))
from approval_key import use_test_key


def approve(root, plan, action, target):
    path=root/'plan.json';path.write_text(json.dumps(plan))
    request={'id':'request-demo','title':'Fiktive Aktion','summary':'Nur Test, keine echte Freigabe.',
             'requested_by':'Fachspezialist','requested_at':'2026-10-24T10:00:00+02:00',
             'artifact':{'id':'artifact-demo','owner_module':'website','path':'plan.json','version':1,'status':'review',
                         'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'contains_personal_data':False,'rights_status':'cleared'},
             'action':action,'target':target,'reviews':[]}
    for dimension in ('expert','legal'):
        request['reviews'].append({'id':'review-'+dimension,'artifact_id':'artifact-demo','artifact_version':1,'dimension':dimension,'status':'pass','reviewed_at':'2026-10-24T09:00:00+02:00','findings':[],'evidence_refs':['fictional-review']})
    log=root/'approvals.jsonl';event=record_request(log,request,root)
    decision=record_decision(log,request['id'],'approved','Erika Beispiel (fiktiv)','2026-10-24T11:00:00+02:00','fixture:human','Fiktiver Testentscheid',event['id'],root,key=load_key())
    return log,path,request,decision


class CapabilityRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.key=use_test_key(self)
    def test_unsigned_or_forged_approvals_never_pass_the_gate(self):
        # H1: an agent without the key can write the log, but cannot produce an accepted approval.
        path=self.root/'plan.json';path.write_text('{}')
        log,path,request,event=approve(self.root,{'fixture':True},'publish','sftp:test')
        _,sha=snapshot_json(path)
        require_approval(log,request['id'],self.root,path,'publish','sftp:test',sha)
        lines=log.read_text().splitlines();last=json.loads(lines[-1])
        forged=dict(last);forged['signature']=dict(last['signature'],value='0'*64)
        log.write_text('\n'.join(lines[:-1]+[json.dumps(forged,ensure_ascii=False,separators=(',',':'))])+'\n')
        with self.assertRaises((CapabilityError,CheckError)):require_approval(log,request['id'],self.root,path,'publish','sftp:test',sha)
        unsigned=dict(last);unsigned.pop('signature')
        log.write_text('\n'.join(lines[:-1]+[json.dumps(unsigned,ensure_ascii=False,separators=(',',':'))])+'\n')
        with self.assertRaises((CapabilityError,CheckError)):require_approval(log,request['id'],self.root,path,'publish','sftp:test',sha)
    def test_gate_refuses_missing_key_and_key_inside_suite(self):
        log,path,request,event=approve(self.root,{'fixture':True},'publish','sftp:test')
        _,sha=snapshot_json(path)
        with patch.dict(os.environ,{},clear=True),self.assertRaises((CapabilityError,CheckError)):
            require_approval(log,request['id'],self.root,path,'publish','sftp:test',sha)
        inside=self.root/'approval.key';inside.write_bytes(self.key)
        with patch.dict(os.environ,{'SUITE_APPROVAL_KEY_FILE':str(inside)}),self.assertRaises((CapabilityError,CheckError)):
            require_approval(log,request['id'],self.root,path,'publish','sftp:test',sha)
    def test_one_approval_allows_one_execution(self):
        log,path,request,event=approve(self.root,{'fixture':True},'publish','sftp:test')
        _,sha=snapshot_json(path);approval=require_approval(log,request['id'],self.root,path,'publish','sftp:test',sha)
        executions=self.root/'executions.jsonl';calls=[]
        run_once(executions,'key-one','website.sftp',approval,lambda:calls.append(1) or {'status':'confirmed'})
        with self.assertRaises(CapabilityError):
            run_once(executions,'key-two','website.sftp',approval,lambda:calls.append(2) or {'status':'confirmed'})
        self.assertTrue(run_once(executions,'key-one','website.sftp',approval,lambda:calls.append(3))['replayed'])
        self.assertEqual(calls,[1])
    def test_execution_log_is_bound_to_the_approval_log(self):
        approvals=self.root/'approvals.jsonl'
        self.assertEqual(bound_execution_log(approvals,self.root/'executions.jsonl'),self.root.resolve()/'executions.jsonl')
        for other in (self.root/'other.jsonl',self.root/'sub'/'executions.jsonl'):
            with self.subTest(other=other),self.assertRaises((CapabilityError,OSError)):bound_execution_log(approvals,other)
    def test_exact_frozen_plan_and_scope_required(self):
        log,path,request,event=approve(self.root,{'fixture':True},'publish','sftp:test')
        _,sha=snapshot_json(path)
        result=require_approval(log,request['id'],self.root,path,'publish','sftp:test',sha)
        self.assertEqual(result['approval_event_id'],event['id'])
        receipt=run_once(self.root/'executions.jsonl','approved-operation','website.sftp',result,lambda:{'status':'confirmed','verification':'fixture-readback','file_count':1})
        self.assertEqual(receipt['status'],'confirmed');self.assertEqual(receipt['action'],'publish')
        for action,target,hash_value in [('send','sftp:test',sha),('publish','wrong',sha),('publish','sftp:test','a'*64)]:
            with self.subTest(action=action,target=target),self.assertRaises(CapabilityError):
                require_approval(log,request['id'],self.root,path,action,target,hash_value)
        record_decision(log,request['id'],'revoked','Erika Beispiel (fiktiv)','2026-10-24T12:00:00+02:00','fixture:revoke','Zurückgenommen',event['id'],self.root)
        with self.assertRaises(CapabilityError):require_approval(log,request['id'],self.root,path,'publish','sftp:test',sha)
    def test_execution_is_once_and_receipts_append(self):
        log=self.root/'executions.jsonl';calls=[]
        result=run_once(log,'key1','fixture',{'target':'demo'},lambda:calls.append(1) or {'status':'accepted'})
        prefix=log.read_bytes()
        replayed=run_once(log,'key1','fixture',{'target':'demo'},lambda:calls.append(2))
        self.assertEqual(calls,[1]);self.assertTrue(replayed['replayed']);self.assertEqual(result['status'],'accepted')
        self.assertEqual(log.read_bytes(),prefix)
        with self.assertRaises(CapabilityError):run_once(log,'key1','different',{'target':'demo'},lambda:None)
    def test_crashed_or_ambiguous_operations_are_never_retried(self):
        log=self.root/'executions.jsonl';append_execution(log,{'key':'key1','capability':'fixture','target':'demo','status':'started'})
        result=run_once(log,'key1','fixture',{'target':'demo'},lambda:self.fail('must not run'))
        self.assertEqual(result['status'],'uncertain')
        def fail():raise RuntimeError('secret-password-do-not-log')
        result=run_once(log,'key2','fixture',{'target':'demo'},fail)
        self.assertEqual(result['status'],'uncertain');self.assertNotIn('secret-password',log.read_text())
    def test_partial_logs_and_active_locks_fail_closed(self):
        log=self.root/'executions.jsonl';log.write_text('{')
        with self.assertRaises(CapabilityError):run_once(log,'key1','fixture',{},lambda:None)
        self.assertEqual(log.read_text(),'{')
        log.with_name(log.name+'.lock').touch()
        with self.assertRaises(CapabilityError):run_once(log,'key1','fixture',{},lambda:None)
