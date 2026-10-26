#!/usr/bin/env python3
"""Preflight for the four *bounded* suite JSON contracts (v0.2); no network/side effects.
Single records:  validate_records.py <contract> record.json
Cross-record:    validate_records.py bundle bundle.json   (Gates G2/G3 -> G4 evidence chain)
This is NOT a full JSON Schema, security, compliance or legal validator.
"""
import argparse, json, math, re, sys
from datetime import datetime
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
SCHEMA_NAMES=('work-order','artifact','review','action-approval')
BUNDLE_KEYS={'work_orders':'work-order','artifacts':'artifact','reviews':'review','approvals':'action-approval'}
# G2 = fachliche/technische Qualität, G3 = Legal/Privacy/Assetrechte (GOVERNANCE.md)
G2_DIMENSIONS={'brief','expert','evidence','creative','technical','accessibility','consistency','security'}
G3_DIMENSIONS={'legal','privacy'}
EXECUTED={'queued','submitted','confirmed','failed','uncertain'}
EXTERNAL_RELEASE={'publish','send','print','modify_external'}
AI_AUTHORIZER=re.compile(r'\b(ki|ai|llm|gpt|chatgpt|claude|gemini|copilot|chatbot|bot|agent|assistant|assistent|model|modell)\b',re.I)
class CheckError(Exception):pass

def _dt(value):
    try:x=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:return None
    return x if x.tzinfo else None

def _field(key,value,spec,errors):
    typ=spec.get('type')
    if typ=='string' and not isinstance(value,str):errors.append(key+': string expected');return
    if typ=='integer' and (not isinstance(value,int) or isinstance(value,bool)):errors.append(key+': integer expected');return
    if typ=='boolean' and not isinstance(value,bool):errors.append(key+': boolean expected');return
    if typ=='number' and (not isinstance(value,(int,float)) or isinstance(value,bool)):errors.append(key+': number expected');return
    if typ=='array' and not isinstance(value,list):errors.append(key+': array expected');return
    if typ=='object' and not isinstance(value,dict):errors.append(key+': object expected');return
    if isinstance(value,str):
        if len(value)<spec.get('minLength',0):errors.append(key+': too short')
        if 'enum' in spec and value not in spec['enum']:errors.append(key+': invalid enum')
        if 'pattern' in spec and re.fullmatch(spec['pattern'],value) is None:errors.append(key+': invalid pattern')
        if spec.get('format')=='date-time':
            try:
                if datetime.fromisoformat(value.replace('Z','+00:00')).tzinfo is None:errors.append(key+': timezone required')
            except ValueError:errors.append(key+': invalid datetime')
    elif isinstance(value,(int,float)) and not isinstance(value,bool):
        if not math.isfinite(value):errors.append(key+': must be finite')
        elif value<spec.get('minimum',float('-inf')):errors.append(key+': below minimum')
    elif isinstance(value,list):
        if spec.get('uniqueItems') and len({json.dumps(v,sort_keys=True) for v in value})<len(value):errors.append(key+': duplicate')
        for i,item in enumerate(value):_field(f'{key}[{i}]',item,spec.get('items',{}),errors)
    elif isinstance(value,dict):
        props=spec.get('properties',{})
        for r in spec.get('required',[]):
            if r not in value:errors.append(f'{key}: required missing: {r}')
        for k,v in value.items():
            if k not in props:
                if spec.get('additionalProperties') is False:errors.append(f'{key}: unexpected field: {k}')
                continue
            _field(f'{key}.{k}',v,props[k],errors)

def check(name, record):
    if name not in SCHEMA_NAMES:raise CheckError('unknown contract')
    schema=json.loads((HERE/'contracts'/f'{name}.schema.json').read_text(encoding='utf8'))
    if not isinstance(record,dict):raise CheckError('object expected')
    errors=[]
    _field('record',record,{**schema,'type':'object'},errors)
    errors=[e.replace('record: ','').replace('record.','') for e in errors]
    if errors:raise CheckError('; '.join(errors))
    r=record
    if name=='work-order':
        if r['lead_module'] in r.get('supporting_modules',[]):errors.append('supporting_modules must not repeat lead_module')
    if name=='artifact':
        p=r['path']
        if p.startswith('/') or '\\' in p or '..' in p.split('/') or '://' in p or not p.strip():errors.append('path: unsafe/non-relative')
        if r['status'] in ('approved','published'):
            if 'sha256' not in r:errors.append(r['status']+' artifact needs sha256')
            if r['rights_status']=='pending':errors.append(r['status']+' artifact with pending rights')
    if name=='review':
        sev={f['severity'] for f in r['findings']}
        if r['status']=='pass':
            if not r.get('evidence_refs') and not any(f.get('evidence_ref') for f in r['findings']):errors.append('pass needs evidence reference')
            if sev&{'major','critical'}:errors.append('pass with major/critical finding')
        if r['status']=='blocked' and not sev&{'major','critical'}:errors.append('blocked needs at least one major/critical finding')
        if r['status']=='warning':
            if not r['findings']:errors.append('warning needs at least one finding')
            if 'critical' in sev:errors.append('critical finding must be blocked, not warning')
            if not r.get('risk_accepted_by'):errors.append('warning needs risk_accepted_by (authorized instance)')
            elif AI_AUTHORIZER.search(r['risk_accepted_by']):errors.append('risk_accepted_by must not be an AI system')
        if r['status']=='not_applicable':
            if not r.get('notes', '').strip():errors.append('not_applicable needs justification in notes')
            if sev&{'major','critical'}:errors.append('not_applicable with major/critical finding')
    if name=='action-approval':
        if AI_AUTHORIZER.search(r['authorizer']):errors.append('authorizer must be a human/accountable role, not an AI system')
        if 'budget_limit' in r and 'currency' not in r:errors.append('budget_limit needs currency')
        if r['action']=='spend' and 'budget_limit_eur' not in r and 'budget_limit' not in r:errors.append('spend needs budget_limit + currency (or legacy budget_limit_eur)')
        if r['decision']=='approved' and not r.get('review_refs'):errors.append('approved needs review_refs (G2/G3 evidence)')
        ex=r.get('execution_status','not_attempted')
        if ex in EXECUTED and r['decision']!='approved':errors.append(f'execution_status {ex} without decision approved')
        if ex=='confirmed' and not r.get('execution_external_id'):errors.append('confirmed needs external id')
        if 'expires_at' in r:
            d,e=_dt(r['decided_at']),_dt(r['expires_at'])
            if d and e and e<=d:errors.append('expires_at must be after decided_at')
    if errors:raise CheckError('; '.join(errors))
    return True

def check_bundle(bundle):
    """Cross-record checks: an approval must rest on reviews of exactly the approved artifact version."""
    if not isinstance(bundle,dict):raise CheckError('bundle object expected')
    unknown=set(bundle)-set(BUNDLE_KEYS)
    errors=['unknown bundle key: '+k for k in sorted(unknown)]
    for key,name in BUNDLE_KEYS.items():
        items=bundle.get(key,[])
        if not isinstance(items,list):errors.append(key+': array expected');continue
        ids=set()
        for i,rec in enumerate(items):
            try:check(name,rec)
            except CheckError as e:
                errors.append(f'{key}[{i}]: {e}')
                continue
            rid=rec.get('id') if isinstance(rec,dict) else None
            if rid in ids:errors.append(f'{key}: duplicate id {rid}')
            ids.add(rid)
    if errors:raise CheckError('; '.join(errors))
    artifacts={(a['id'],a['version']):a for a in bundle.get('artifacts',[])}
    reviews={r['id']:r for r in bundle.get('reviews',[])}
    approvals=bundle.get('approvals',[])
    for r in reviews.values():
        if (r['artifact_id'],r['artifact_version']) not in artifacts:errors.append(f"review {r['id']}: artifact {r['artifact_id']} v{r['artifact_version']} not in bundle")
    for a in approvals:
        key=(a['artifact_id'],a['artifact_version']);art=artifacts.get(key);tag='approval '+a['id']
        if a['decision']!='approved':continue
        if art is None:errors.append(f'{tag}: artifact {key[0]} v{key[1]} not in bundle');continue
        if art.get('sha256')!=a['artifact_sha256']:errors.append(f'{tag}: artifact_sha256 does not match artifact')
        if art['rights_status']=='pending':errors.append(f'{tag}: artifact rights pending')
        refs=[reviews.get(x) for x in a['review_refs']]
        if None in refs:errors.append(f'{tag}: unknown review_refs');refs=[x for x in refs if x]
        for rv in refs:
            if (rv['artifact_id'],rv['artifact_version'])!=key:errors.append(f"{tag}: review {rv['id']} covers another artifact/version")
            if rv['status'] in ('blocked','not_checked'):errors.append(f"{tag}: review {rv['id']} is {rv['status']}")
        ok={rv['dimension'] for rv in refs if (rv['artifact_id'],rv['artifact_version'])==key and rv['status'] in ('pass','warning','not_applicable')}
        if not ok&G2_DIMENSIONS:errors.append(f'{tag}: no G2 quality review (pass/warning)')
        if not ok&G3_DIMENSIONS:errors.append(f'{tag}: no G3 legal/privacy review (pass/warning/not_applicable)')
        for rv in reviews.values():
            if (rv['artifact_id'],rv['artifact_version'])==key and rv['status']=='blocked':errors.append(f"{tag}: blocking review {rv['id']} exists for this version")
    for art in artifacts.values():
        if art['status']=='published' and not any(a['artifact_id']==art['id'] and a['artifact_version']==art['version'] and a['decision']=='approved'
                and a['action'] in EXTERNAL_RELEASE and a.get('execution_status')=='confirmed' for a in approvals):
            errors.append(f"artifact {art['id']} v{art['version']}: published without approved+confirmed release action")
    if errors:raise CheckError('; '.join(dict.fromkeys(errors)))
    return True

def _reject_constant(name):raise ValueError('non-finite number not allowed: '+name)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('contract',choices=SCHEMA_NAMES+('bundle',));parser.add_argument('json_file',type=Path);args=parser.parse_args()
    try:
        data=json.loads(args.json_file.read_text(encoding='utf8'),parse_constant=_reject_constant)
        check_bundle(data) if args.contract=='bundle' else check(args.contract,data)
        print('STRUCTURAL_PREFLIGHT_OK (no compliance certification)')
    except (CheckError,OSError,ValueError) as e:
        print('PREFLIGHT_BLOCKED:',str(e),file=sys.stderr);return 2
    return 0
if __name__=='__main__':sys.exit(main())
