#!/usr/bin/env python3
"""noCRM v0.1 local preflight. NO NETWORK and NO SENDING.\n\nExample: python3 .nocrm/tools/preflight.py --contacts path.csv --consents path.csv --draft draft.json\n"""
import argparse
import csv
import json
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

ALLOWED_CHANNELS = {'email','whatsapp','signal','telegram','website-chat','telefon','sms','social-dm','brief','meeting','contact-form'}
ALLOWED_PURPOSES = {'service','personal','marketing','transactional'}
ALLOW_MARKETING = {'granted'}  # No unverified soft-opt-in by default.


def read_csv(path, required):
    if not Path(path).exists():
        raise ValueError(f'CSV not found: {path}')
    return parse_csv(Path(path).read_text(encoding='utf-8-sig'), required)


def parse_csv(text, required):
    r=csv.DictReader(io.StringIO(text))
    missing=set(required) - set(r.fieldnames or [])
    if missing:
        raise ValueError(f'CSV missing columns: {sorted(missing)}')
    return list(r)


def iso_date(x):
    if not x: return None
    try:
        dt=datetime.fromisoformat(x.replace('Z','+00:00'))
        if dt.tzinfo is None: return None
        return dt
    except Exception: return None


def marketing_consent(consents, cid, channel, now):
    """Shared with the mail adapter: returns (problems, valid consent rows) for one contact and channel."""
    problems=[]; valid=[]
    matches=[c for c in consents if c.get('contact_id','').strip()==cid and c.get('channel','').strip()==channel and c.get('purpose','').strip()=='marketing']
    if not matches:
        problems.append('Marketing consent missing; no marketing send')
    elif any(c.get('status') in {'revoked','denied','objected'} for c in matches):
        problems.append('Marketing permission revoked/denied/objected; blocked')
    else:
        for c in matches:
            if c.get('status') in ALLOW_MARKETING and c.get('evidence_ref','').strip() and c.get('basis','')=='consent':
                t=iso_date(c.get('recorded_at',''))
                expiry=iso_date(c.get('valid_until','')) if c.get('valid_until','') else None
                if t and t<=now and (not c.get('valid_until') or (expiry and expiry>now)):
                    valid.append(c)
        if not valid:
            problems.append('No verifiable, current, channel-specific marketing consent; special legal exceptions require separate expert review')
    return problems, valid


def run(contacts, consents, draft, now=None):
    now=now or datetime.now(timezone.utc)
    problems=[]; notes=[]
    if not isinstance(draft,dict): return {'eligible':False,'problems':['Draft must be a JSON object'],'notes':[],'action':'NONE'}
    cid=str(draft.get('contact_id','')).strip()
    channel=str(draft.get('channel','')).strip()
    purpose=str(draft.get('purpose','')).strip()
    text=draft.get('body','')
    if not cid: problems.append('Missing contact_id')
    if channel not in ALLOWED_CHANNELS: problems.append('Unsupported channel')
    if purpose not in ALLOWED_PURPOSES: problems.append('Unsupported purpose')
    if not isinstance(text,str) or not text.strip(): problems.append('Empty message body')
    matches=[c for c in contacts if c.get('contact_id','').strip()==cid]
    if len(matches)!=1: problems.append(f'Exactly one contact required, found {len(matches)}')
    if len(matches)==1:
        c=matches[0]
        if channel=='email' and not c.get('email','').strip(): problems.append('Email address missing')
        if channel in {'sms','whatsapp','telefon'} and not c.get('phone','').strip(): problems.append('Phone number missing')
    if purpose=='marketing':
        problems.extend(marketing_consent(consents,cid,channel,now)[0])
        if not bool(draft.get('authorization',{}).get('allowed',False)):
            problems.append('Specific sender authorization missing')
        if not bool(draft.get('review',{}).get('approved',False)):
            problems.append('Content review not approved')
    else:
        if not bool(draft.get('context_verified',False)):
            problems.append('Non-marketing purpose requires verified request/contractual context')
        if not bool(draft.get('authorization',{}).get('allowed',False)):
            problems.append('Specific sender authorization missing')
        if not bool(draft.get('review',{}).get('approved',False)):
            problems.append('Content review not approved')
    if channel=='whatsapp':
        if not (draft.get('within_24h') is True or draft.get('template_approved') is True):
            problems.append('WhatsApp: 24h window or approved template required')
        if draft.get('escalation_route_confirmed') is not True:
            problems.append('WhatsApp automation: clear escalation route required')
    if channel=='telegram' and draft.get('recipient_initiated') is not True:
        problems.append('Telegram Bot: recipient must initiate chat first')
    if draft.get('direct_ai_interaction') is True and draft.get('ai_disclosure_confirmed') is not True:
        problems.append('Direct AI interaction: transparency check not confirmed')
    if draft.get('status') not in {'drafted','reviewed','approved'}:
        problems.append('Draft state must be drafted, reviewed or approved')
    if not draft.get('idempotency_key'):
        problems.append('Idempotency key required')
    notes.append('No external action performed; eligibility does not prove legal compliance or authorize dispatch')
    notes.append('Account permission, jurisdiction, content hash and connector capability must be checked by the production adapter')
    return {'eligible':not problems,'problems':problems,'notes':notes,'action':'DRY_RUN_ONLY'}


def main(argv=None):
    p=argparse.ArgumentParser(description='noCRM local non-sending preflight')
    p.add_argument('--contacts',required=True)
    p.add_argument('--consents',required=True)
    p.add_argument('--draft',required=True)
    args=p.parse_args(argv)
    try:
        contacts=read_csv(args.contacts,{'contact_id','display_name','email','phone'})
        consents=read_csv(args.consents,{'contact_id','channel','purpose','status','recorded_at','evidence_ref','basis'})
        draft=json.loads(Path(args.draft).read_text(encoding='utf-8'))
        result=run(contacts,consents,draft)
    except (ValueError, OSError, json.JSONDecodeError) as ex:
        result={'eligible':False,'problems':[f'Invalid input: {ex}'],'notes':[],'action':'NONE'}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['eligible'] else 2

if __name__=='__main__':sys.exit(main())
