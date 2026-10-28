#!/usr/bin/env python3
"""Offline Context Pack exporter. Filtering is NOT authentication or publishing approval."""
import argparse
import json
import sys
from datetime import date,datetime,timezone
from pathlib import Path
from lint_records import load_jsonl,validate_claims

VISIBILITY={'public':0,'shared':1,'restricted':2}
ACTIVE={'verified','declared','planned'}

def validate_request(request):
    keys={'request_id','requester','purpose','topics','max_characters','visibility_max','as_of'}
    if not isinstance(request,dict) or not keys <= set(request) or set(request)-keys-{'include_hypotheses'}:
        raise ValueError('request must contain the required context-request fields and known options only')
    if type(request.get('include_hypotheses', False)) is not bool:
        raise ValueError('include_hypotheses must be boolean')
    if request.get('include_hypotheses') and request.get('visibility_max') == 'public':
        raise ValueError('Hypothesis analysis requires a nonpublic context and actual recipient permission')
    for name in ('request_id','requester','purpose'):
        if not isinstance(request[name],str) or not request[name].strip():
            raise ValueError(name+' must be non-empty text')
    if not isinstance(request['topics'],list) or any(not isinstance(t,str) or not t.strip() for t in request['topics']):
        raise ValueError('topics must be an array of non-empty strings')
    if type(request['max_characters']) is not int or request['max_characters']<500:
        raise ValueError('max_characters must be an integer >= 500')
    if not isinstance(request['visibility_max'],str) or request['visibility_max'] not in VISIBILITY:
        raise ValueError('invalid visibility_max')
    try:
        if date.fromisoformat(request['as_of']).isoformat()!=request['as_of']:
            raise ValueError('noncanonical date')
    except (TypeError,ValueError):
        raise ValueError('as_of must be an ISO calendar date YYYY-MM-DD')


def compose(claims,sources,requester,purpose,topics,visibility,as_of,max_characters, *, request_id=None, include_hypotheses=False, source_snapshot=None):
    validate_request(dict(request_id=request_id or 'request-cli',requester=requester,purpose=purpose,
                          topics=topics,visibility_max=visibility,as_of=as_of,max_characters=max_characters,include_hypotheses=include_hypotheses))
    if visibility not in VISIBILITY: raise ValueError('invalid visibility')
    indexed={s['source_id']:s for s in sources}
    now=datetime.now(timezone.utc).isoformat()
    pack={'request_id':request_id or 'request-cli-'+now.replace(':','').replace('+',''),
          'requester':requester,'purpose':purpose,'generated_at':now,'as_of':as_of,
          'version':'0.1','claims':[],'sources':[],'excluded_count':0,
          'limitations':['Status declared/planned is not independently verified',
                         'CLI filtering is not a technical authorization mechanism']}
    if include_hypotheses:
        pack['limitations'].append('Hypotheses are unverified interpretations, not established target-group facts or publication approval')
    if source_snapshot is not None:
        pack['source_snapshot'] = source_snapshot
    chosen=[]; selected_sources={}
    for claim in claims:
        if claim['status'] not in (ACTIVE | {'hypothesis'} if include_hypotheses else ACTIVE) or VISIBILITY[claim['visibility']]>VISIBILITY[visibility]:continue
        if topics and not any(t.casefold() in {v.casefold() for v in (claim.get('tags',[])+[claim['predicate'],claim['subject']])} for t in topics):continue
        if claim.get('updated_at','')[:10]>as_of:continue
        if claim.get('valid_until') and claim['valid_until'] < as_of:continue
        if claim.get('valid_from') and claim['valid_from'] > as_of:continue
        source_records=[indexed[x] for x in claim['source_refs']]
        if not all(VISIBILITY[s['visibility']]<=VISIBILITY[visibility] for s in source_records):continue
        chosen.append((claim,source_records))
    for claim,src_records in chosen:
        proposal_claims=pack['claims']+[claim]
        proposal_sources={**selected_sources,**{s['source_id']:s for s in src_records}}
        proposal={**pack,'claims':proposal_claims,'sources':list(proposal_sources.values()),
                  'excluded_count':len(chosen)-len(proposal_claims)}
        serialized=json.dumps(proposal,ensure_ascii=False)
        if len(serialized)>max_characters:
            continue
        pack['claims']=proposal_claims
        selected_sources=proposal_sources
    pack['sources']=list(selected_sources.values())
    pack['excluded_count']=len(chosen)-len(pack['claims'])
    if pack['excluded_count']:
        pack['limitations'].append('Some eligible claims were omitted due to character budget')
    if len(json.dumps(pack,ensure_ascii=False))>max_characters:
        raise ValueError('character budget too small even for output metadata')
    return pack

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('claims',type=Path,nargs='?');ap.add_argument('--sources',type=Path)
    ap.add_argument('--store',type=Path,help='Versioned feedback/knowledge store instead of individual JSONL paths')
    ap.add_argument('--include-hypotheses',action='store_const',const=True,default=None,help='Explicit nonpublic hypothesis analysis; no factual promotion')
    ap.add_argument('--request',type=Path,help='JSON context-request; do not combine with selection flags')
    ap.add_argument('--requester');ap.add_argument('--purpose')
    ap.add_argument('--topics');ap.add_argument('--visibility',choices=list(VISIBILITY))
    ap.add_argument('--as-of')
    ap.add_argument('--max-characters',type=int)
    args=ap.parse_args()
    try:
        source_snapshot = None
        if args.store:
            if args.claims or args.sources:
                raise ValueError('--store cannot be combined with individual JSONL paths')
            from import_feedback import read_store
            state, reference = read_store(args.store)
            claims, sources = state['claims'], state['sources']
            if reference:
                source_snapshot = reference['generation'] + ':sha256:' + reference['manifest_sha256']
        else:
            if not args.claims or not args.sources:
                raise ValueError('Provide claims and --sources, or --store')
            claims=load_jsonl(args.claims);sources=load_jsonl(args.sources)
        errors=validate_claims(claims,sources)
        if errors: raise ValueError('; '.join(errors))
        if args.request:
            if any(value is not None for value in (args.requester,args.purpose,args.topics,args.visibility,args.as_of,args.max_characters,args.include_hypotheses)):
                raise ValueError('--request cannot be combined with selection flags')
            request=json.loads(args.request.read_text(encoding='utf-8'))
        else:
            request=dict(request_id='request-cli-'+datetime.now(timezone.utc).isoformat(),
                         requester=args.requester,purpose=args.purpose,
                         topics=[x.strip() for x in (args.topics or '').split(',') if x.strip()],
                         visibility_max=args.visibility or 'shared',
                         as_of=args.as_of or datetime.now(timezone.utc).date().isoformat(),
                         max_characters=args.max_characters if args.max_characters is not None else 6000,
                         include_hypotheses=args.include_hypotheses or False)
        validate_request(request)
        pack=compose(claims,sources,request['requester'],request['purpose'],request['topics'],
                     request['visibility_max'],request['as_of'],request['max_characters'],
                     request_id=request['request_id'], include_hypotheses=request.get('include_hypotheses',False),
                     source_snapshot=source_snapshot)
    except (OSError,ValueError,KeyError,TypeError) as ex:
        print(f'FAIL: {ex}',file=sys.stderr);return 1
    print(json.dumps(pack,indent=2,ensure_ascii=False))
    return 0
if __name__=='__main__':sys.exit(main())
