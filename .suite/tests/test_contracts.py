import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from validate_records import check,check_bundle,CheckError
T='2026-10-23T13:00:00+02:00'
H='a'*64
BUNDLE=json.loads((Path(__file__).resolve().parents[1]/'beispiele'/'demo-freigabe-bundle.json').read_text(encoding='utf8'))
def approval(**kw):
 r=dict(id='abcd',artifact_id='item1',artifact_version=1,artifact_sha256=H,action='publish',target='website',decision='approved',authorizer='authorized person',decided_at=T,review_refs=['rv01'])
 r.update(kw);return r
def review(**kw):
 r=dict(id='rv01',artifact_id='item1',artifact_version=1,dimension='legal',status='pass',reviewed_at=T,findings=[],evidence_refs=['x.md'])
 r.update(kw);return r
def artifact(**kw):
 r=dict(id='item1',owner_module='creative',path='creative/file.svg',version=1,status='draft',contains_personal_data=False,rights_status='pending')
 r.update(kw);return r
class TestSuiteContracts(unittest.TestCase):
 def test_work_order(self):
  check('work-order',dict(id='abcd',objective='Build a relevant campaign',lead_module='marketing',status='proposed',created_at=T,input_refs=[]))
 def test_ecommerce_module(self):
  check('work-order',dict(id='abcd',objective='Prepare a product feed',lead_module='e-commerce',supporting_modules=['advertising'],status='proposed',created_at=T,input_refs=[]))
  check('artifact',dict(id='feed1',owner_module='e-commerce',path='e-commerce/feeds/gmc.xml',version=1,status='draft',contains_personal_data=False,rights_status='not_applicable'))
 def test_invalid_module(self):
  with self.assertRaises(CheckError):check('work-order',dict(id='abcd',objective='Build a relevant campaign',lead_module='imaginary',status='proposed',created_at=T,input_refs=[]))
 def test_lead_repeated_in_supporting(self):
  with self.assertRaises(CheckError):check('work-order',dict(id='abcd',objective='Build a relevant campaign',lead_module='marketing',supporting_modules=['marketing'],status='proposed',created_at=T,input_refs=[]))
 def test_artifact_relpath(self):
  with self.assertRaises(CheckError):check('artifact',artifact(path='../secrets'))
 def test_artifact_draft(self):
  check('artifact',artifact(path='creative/projekt/x.svg'))
 def test_boolean_version_rejected(self):
  with self.assertRaises(CheckError):check('artifact',artifact(version=True))
 def test_published_artifact_needs_hash_and_rights(self):
  with self.assertRaises(CheckError):check('artifact',artifact(status='published',rights_status='cleared'))
  with self.assertRaises(CheckError):check('artifact',artifact(status='approved',sha256=H,rights_status='pending'))
  check('artifact',artifact(status='approved',sha256=H,rights_status='cleared'))
 def test_review_requires_evidence(self):
  with self.assertRaises(CheckError):check('review',review(evidence_refs=[]))
 def test_review_pass_with_critical_rejected(self):
  with self.assertRaises(CheckError):check('review',review(findings=[dict(severity='critical',message='Claim unbelegt')]))
 def test_review_blocked_needs_finding(self):
  with self.assertRaises(CheckError):check('review',review(status='blocked'))
  check('review',review(status='blocked',findings=[dict(severity='major',message='Bildrechte fehlen')]))
 def test_review_warning_needs_acceptance(self):
  r=review(status='warning',evidence_refs=[],findings=[dict(severity='minor',message='Need current terms')])
  with self.assertRaises(CheckError):check('review',r)
  with self.assertRaises(CheckError):check('review',dict(r,risk_accepted_by='KI-Assistent'))
  check('review',dict(r,risk_accepted_by='Geschäftsführung'))
 def test_review_not_applicable_needs_notes(self):
  with self.assertRaises(CheckError):check('review',review(status='not_applicable'))
  check('review',review(status='not_applicable',notes='Kein Personenbezug, kein Tracking'))
 def test_not_applicable_cannot_hide_blocking_findings(self):
  for severity in ('major','critical'):
   with self.subTest(severity=severity):
    with self.assertRaises(CheckError):check('review',review(status='not_applicable',notes='Nicht relevant',findings=[dict(severity=severity,message='Rechte fehlen')]))
  with self.assertRaises(CheckError):check('review',review(status='not_applicable',notes='   '))
 def test_finding_shape_enforced(self):
  with self.assertRaises(CheckError):check('review',review(findings=[dict(severity='info',message='ok ok',foo=1)]))
  with self.assertRaises(CheckError):check('review',review(findings=[dict(severity='info',message='ok ok',evidence_ref=123)]))
 def test_spend_budget(self):
  with self.assertRaises(CheckError):check('action-approval',approval(action='spend',target='google_ads'))
  with self.assertRaises(CheckError):check('action-approval',approval(action='spend',budget_limit=500))
  check('action-approval',approval(action='spend',budget_limit=500,currency='CHF'))
  check('action-approval',approval(action='spend',budget_limit_eur=500))
 def test_budget_must_be_finite(self):
  with self.assertRaises(CheckError):check('action-approval',approval(action='spend',budget_limit_eur=float('inf')))
 def test_confirmed_requires_id(self):
  with self.assertRaises(CheckError):check('action-approval',approval(execution_status='confirmed'))
 def test_basic_action(self):
  check('action-approval',approval(decision='pending',review_refs=[],execution_status='not_attempted'))
 def test_approved_needs_review_refs(self):
  with self.assertRaises(CheckError):check('action-approval',approval(review_refs=[]))
 def test_execution_requires_approved(self):
  with self.assertRaises(CheckError):check('action-approval',approval(decision='denied',execution_status='confirmed',execution_external_id='x'))
  with self.assertRaises(CheckError):check('action-approval',approval(decision='pending',execution_status='submitted'))
 def test_expiry_after_decision(self):
  with self.assertRaises(CheckError):check('action-approval',approval(expires_at='2020-01-01T00:00:00Z'))
 def test_ai_authorizer_rejected(self):
  for name in ('KI','AI agent','Claude','Marketing-Bot'):
   with self.assertRaises(CheckError):check('action-approval',approval(authorizer=name))
  check('action-approval',approval(authorizer='Leitung Agentur Müller'))
class TestBundle(unittest.TestCase):
 def test_demo_bundle_ok(self):
  check_bundle(BUNDLE)
 def test_hash_mismatch(self):
  b=copy.deepcopy(BUNDLE);b['approvals'][0]['artifact_sha256']='b'*64
  with self.assertRaises(CheckError):check_bundle(b)
 def test_review_of_other_version(self):
  b=copy.deepcopy(BUNDLE);a=dict(b['artifacts'][0],version=2);b['artifacts'].append(a);b['reviews'][1]['artifact_version']=2
  with self.assertRaises(CheckError):check_bundle(b)
 def test_missing_legal_review(self):
  b=copy.deepcopy(BUNDLE);b['approvals'][0]['review_refs']=['rv-topaca-landing-expert-1']
  with self.assertRaises(CheckError):check_bundle(b)
 def test_unreferenced_blocking_review(self):
  b=copy.deepcopy(BUNDLE);b['reviews'].append(dict(b['reviews'][0],id='rv-block',dimension='privacy',status='blocked',evidence_refs=[],findings=[dict(severity='major',message='Pixel ohne Einwilligung')]))
  with self.assertRaises(CheckError):check_bundle(b)
 def test_unknown_review_ref(self):
  b=copy.deepcopy(BUNDLE);b['approvals'][0]['review_refs'].append('rv-missing')
  with self.assertRaises(CheckError):check_bundle(b)
 def test_published_needs_confirmed_release(self):
  b=copy.deepcopy(BUNDLE);b['artifacts'][0]['status']='published'
  with self.assertRaises(CheckError):check_bundle(b)
  b['approvals'][0].update(execution_status='confirmed',execution_external_id='deploy-123');check_bundle(b)
 def test_invalid_bundle_records_fail_cleanly(self):
  for invalid in ([], None, {'id': []}, dict(BUNDLE['reviews'][0],id={})):
   with self.subTest(record=invalid):
    b=copy.deepcopy(BUNDLE);b['reviews'].append(invalid)
    with self.assertRaises(CheckError):check_bundle(b)
 def test_not_applicable_cannot_bypass_bundle_gate(self):
  b=copy.deepcopy(BUNDLE)
  b['reviews'][1].update(status='not_applicable',notes='Nicht anwendbar',findings=[dict(severity='critical',message='Rechte fehlen')])
  with self.assertRaises(CheckError):check_bundle(b)
 def test_duplicate_ids(self):
  b=copy.deepcopy(BUNDLE);b['reviews'].append(copy.deepcopy(b['reviews'][0]))
  with self.assertRaises(CheckError):check_bundle(b)
if __name__=='__main__':unittest.main()
