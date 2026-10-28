#!/usr/bin/env python3
"""One-shot technical weekly review. Scheduling and model interpretation belong to the harness."""
import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import uuid
from zoneinfo import ZoneInfo

import evaluate_csv
import fetch_google

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = Path(__file__).resolve().parents[1] / 'beispiele'
BOUNDARY = ROOT if (ROOT / '.suite').is_dir() else Path(__file__).resolve().parents[2]
pending = None
if (ROOT / '.suite/tools/pending.py').is_file():
    spec = importlib.util.spec_from_file_location('_suite_pending_weekly', ROOT / '.suite/tools/pending.py')
    pending = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pending)

LIMIT = 30 * 1024 * 1024
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}')
PRIVACY = {'public','internal','confidential','personal','special_category'}


class StepFailure(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code=code


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def decode(data):
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing or symlinked file')
    with path.open('rb') as stream:
        value = stream.read(LIMIT + 1)
    if len(value) > LIMIT:
        raise ValueError('Input too large')
    return value


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def write(path, value):
    data = value if isinstance(value, bytes) else encoded(value)
    descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return digest(data)


def sync_directory(path):
    descriptor=os.open(str(path),os.O_RDONLY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)


def fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value)-set(required)-set(optional):
        raise ValueError('Unknown or missing profile fields')


def text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 2000 or any(ord(c) < 32 for c in value):
        raise ValueError('Nonempty text without control characters required')
    return value


def identifier(value):
    if not isinstance(value, str) or ID.fullmatch(value) is None:
        raise ValueError('Invalid identifier')
    return value


def zoned(value):
    if not isinstance(value, str):
        raise ValueError('Zoned ISO timestamp required')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Zoned ISO timestamp required')
    return result


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('Integer outside supported range')
    return value


def local_path(value, directory):
    path = Path(text(value)).expanduser()
    return path if path.is_absolute() else directory / path


def private_output(value, directory):
    path = local_path(value, directory)
    if path.is_symlink():
        raise ValueError('Output root must not be symlinked')
    path = path.resolve()
    if path.parent == path or path == BOUNDARY or BOUNDARY in path.parents or (path.exists() and not path.is_dir()):
        raise ValueError('Private run outputs must be outside the Suite checkout')
    return path


def load_profile(path):
    path = Path(path).resolve()
    data = read(path)
    profile = decode(data)
    fields(profile, ('schema_version','id','purpose','time_zone','output_dir','authorization_ref',
                     'model_context','sources'), ('window_days','approvals','schedule'))
    if profile['schema_version'] != '0.1' or profile['model_context'] != 'summaries_only':
        raise ValueError('Unsupported profile version or model context policy')
    identifier(profile['id']);text(profile['purpose']);text(profile['authorization_ref'])
    ZoneInfo(text(profile['time_zone']))
    private_output(profile['output_dir'], path.parent)
    integer(profile.get('window_days',7),1,90)
    if not isinstance(profile['sources'],list) or not 1 <= len(profile['sources']) <= 10:
        raise ValueError('One to ten explicit sources required')
    ids=set()
    for source in profile['sources']:
        fields(source, ('id','kind','time_zone','metrics'),
               ('csv_path','manifest_path','property','site','dimension','token_env','lag_days','allowed_privacy_classes'))
        identifier(source['id'])
        if source['id'] in ids:raise ValueError('Duplicate source ID')
        ids.add(source['id'])
        ZoneInfo(text(source['time_zone']))
        integer(source.get('lag_days',3 if source['kind']=='gsc' else 1),1,60)
        allowed=source.get('allowed_privacy_classes',['public','internal'])
        if not isinstance(allowed,list) or not allowed or any(not isinstance(item,str) or item not in PRIVACY for item in allowed):
            raise ValueError('Explicit allowed privacy classes required')
        kind=source['kind']
        if kind=='csv':
            if set(source)&{'property','site','dimension','token_env'}:raise ValueError('Mixed source settings')
            if local_path(source.get('csv_path'),path.parent).suffix.lower()!='.csv':raise ValueError('Explicit CSV path required')
            if local_path(source.get('manifest_path'),path.parent).suffix.lower()!='.json':raise ValueError('Explicit manifest required')
        elif kind in ('ga4','gsc'):
            if set(source)&{'csv_path','manifest_path'}:raise ValueError('Mixed source settings')
            if re.fullmatch(r'[A-Z][A-Z0-9_]*',source.get('token_env','GOOGLE_OAUTH_ACCESS_TOKEN')) is None:
                raise ValueError('Credential environment reference required, never a token value')
            if kind=='ga4':
                if set(source)&{'site','dimension'} or not isinstance(source.get('property'),str) or not re.fullmatch(r'[0-9]{1,32}',source['property']):
                    raise ValueError('GA4 requires only a numeric property reference')
            else:
                text(source.get('site'))
                if 'property' in source or source.get('dimension') not in (None,'query','page','country','device'):
                    raise ValueError('Unsupported GSC settings')
                if source['time_zone']!='America/Los_Angeles':raise ValueError('GSC requires Pacific Time')
        else:raise ValueError('Only CSV, GA4 and GSC sources are supported')
        if not isinstance(source['metrics'],list) or not 1 <= len(source['metrics']) <= 10:
            raise ValueError('One to ten metrics required')
        metric_ids=set()
        for metric in source['metrics']:
            fields(metric, ('id','numerator'), ('denominator','segment_column','segment','expected_direction'))
            identifier(metric['id']);text(metric['numerator'])
            if metric['id'] in metric_ids:raise ValueError('Duplicate metric ID')
            metric_ids.add(metric['id'])
            for key in ('denominator','segment_column','segment'):
                if key in metric:text(metric[key])
            if 'segment' in metric and 'segment_column' not in metric:raise ValueError('Segment column required')
            if metric.get('expected_direction','unknown') not in ('up','down','unknown'):raise ValueError('Invalid direction')
    if 'approvals' in profile:
        section=profile['approvals']
        fields(section, (), ('config_path','logs','include_titles'))
        if ('config_path' in section)==('logs' in section):raise ValueError('Choose approval config or explicit logs')
        if type(section.get('include_titles',False)) is not bool:raise ValueError('Boolean title sharing required')
        if 'config_path' in section:local_path(section['config_path'],path.parent)
        else:
            if not isinstance(section['logs'],list) or not 1 <= len(section['logs']) <= 20:raise ValueError('Explicit approval logs required')
            for item in section['logs']:
                fields(item,('label','path'));text(item['label']);local_path(item['path'],path.parent)
    if 'schedule' in profile:
        schedule=profile['schedule']
        fields(schedule,('kind','weekday','local_time','time_zone','missed_run'))
        if schedule['kind']!='harness' or schedule['weekday'] not in ('monday','tuesday','wednesday','thursday','friday','saturday','sunday'):
            raise ValueError('Harness scheduling intent required')
        if re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]',schedule['local_time']) is None:raise ValueError('Invalid schedule time')
        if schedule['time_zone']!=profile['time_zone'] or schedule['missed_run'] not in ('ask','skip','latest_only'):
            raise ValueError('Explicit missed-run policy and profile timezone required')
    return profile,path.parent,digest(data),data


def windows(profile, source, as_of):
    days=profile.get('window_days',7)
    end=as_of.astimezone(ZoneInfo(source['time_zone'])).date()-timedelta(days=source.get('lag_days',3 if source['kind']=='gsc' else 1))
    b=(end-timedelta(days=days-1),end)
    a=(b[0]-timedelta(days=days),b[0]-timedelta(days=1))
    return a,b


def plan(path, as_of=None):
    profile,directory,sha,_=load_profile(path)
    at=zoned(as_of) if as_of else datetime.now(timezone.utc)
    return {'profile_id':profile['id'],'profile_sha256':sha,'purpose':profile['purpose'],
            'logical_as_of':at.isoformat(),'output_dir':str(private_output(profile['output_dir'],directory)),
            'sources':[{'id':s['id'],'kind':s['kind'],'time_zone':s['time_zone'],
                        'period_a':[d.isoformat() for d in windows(profile,s,at)[0]],
                        'period_b':[d.isoformat() for d in windows(profile,s,at)[1]]} for s in profile['sources']],
            'schedule_intent':profile.get('schedule'), 'schedule_runtime_status':'not_checked_or_configured_by_this_tool',
            'network_called':False,'model_called':False}


def manifest_check(manifest, source, csv_data, a, b):
    required={'dataset_id','source_system','extracted_at','time_zone','grain','period_start','period_end','privacy_class','metric_definitions'}
    fields(manifest,required,('filters','permissions','notes','file_sha256'))
    for key in ('dataset_id','source_system','grain'):text(manifest[key])
    zoned(manifest['extracted_at'])
    if manifest['time_zone']!=source['time_zone']:raise StepFailure('SOURCE_TIMEZONE_MISMATCH')
    if manifest['privacy_class'] not in PRIVACY:raise StepFailure('SOURCE_PRIVACY_CLASS_UNKNOWN')
    if manifest['privacy_class'] not in source.get('allowed_privacy_classes',['public','internal']):raise StepFailure('SOURCE_PRIVACY_CLASS_NOT_ALLOWED')
    if not isinstance(manifest['metric_definitions'],dict):raise ValueError('Missing metric definitions')
    period_a=evaluate_csv.window(manifest['period_start']+':'+manifest['period_end'])
    if period_a[0]>a[0] or period_a[1]<b[1]:raise StepFailure('SOURCE_WINDOW_NOT_COVERED')
    if 'file_sha256' in manifest and manifest['file_sha256']!=digest(csv_data):raise StepFailure('SOURCE_HASH_MISMATCH')


def acquire(source, profile_dir, destination, a, b, post):
    destination.mkdir(mode=0o700)
    if source['kind']=='csv':
        csv_data=read(local_path(source['csv_path'],profile_dir))
        manifest_data=read(local_path(source['manifest_path'],profile_dir))
        manifest=decode(manifest_data)
        manifest_check(manifest,source,csv_data,a,b)
        csv_path=destination/'data.csv';manifest_path=destination/'data.manifest.json'
        write(csv_path,csv_data);write(manifest_path,manifest_data)
    else:
        if source['kind']=='gsc' and source.get('dimension') in ('query','page') and 'confidential' not in source.get('allowed_privacy_classes',['public','internal']):
            raise StepFailure('SOURCE_PRIVACY_CLASS_NOT_ALLOWED')
        token=os.environ.get(source.get('token_env','GOOGLE_OAUTH_ACCESS_TOKEN'))
        if not token:raise StepFailure('READ_CREDENTIAL_UNAVAILABLE')
        if source['kind']=='ga4':
            result=fetch_google.fetch_ga4(source['property'],a[0],b[1],token,post=post,expected_zone=source['time_zone'])
        else:
            result=fetch_google.fetch_gsc(source['site'],a[0],b[1],token,source.get('dimension'),post=post)
        csv_path,manifest_path=fetch_google.write_dataset(destination,source['id'],*result,a[0],b[1],source['time_zone'],
            privacy_class='confidential' if source.get('dimension') in ('query','page') else 'internal')
        csv_data=read(csv_path);manifest_data=read(manifest_path);manifest=decode(manifest_data)
        manifest_check(manifest,source,csv_data,a,b)
    sync_directory(destination)
    return csv_path,manifest_path,manifest,{'csv_sha256':digest(csv_data),'manifest_sha256':digest(manifest_data)}


def evaluate_metric(csv_path, manifest, source, metric, a, b):
    definitions=manifest['metric_definitions']
    for key in ('numerator','denominator'):
        if key in metric:
            definition=definitions.get(metric[key],{})
            if not isinstance(definition,dict) or definition.get('aggregation')!='sum':
                raise StepFailure('METRIC_NOT_DECLARED_ADDITIVE')
    segment_column=metric.get('segment_column') or ('channel' if source['kind']=='ga4' else source.get('dimension') if source['kind']=='gsc' else None)
    result=evaluate_csv.analyze(csv_path,'date',metric['numerator'],metric.get('denominator'),a,b,
        segment_column,metric.get('segment'),metric.get('expected_direction','unknown'),source['id'])
    seen={}
    with csv_path.open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            if 'segment' in metric and row.get(segment_column)!=metric['segment']:continue
            if not a[0].isoformat()<=row['date']<=b[1].isoformat():continue
            group=row.get(segment_column) if segment_column else None
            seen.setdefault(group,set()).add(row['date'])
    expected={ (a[0]+timedelta(days=n)).isoformat() for n in range((b[1]-a[0]).days+1)}
    missing=sorted(set().union(*(expected-dates for dates in seen.values())))
    computable=result['period_a']['value'] is not None and result['period_b']['value'] is not None
    return result,missing,computable,segment_column


def approval_snapshot(section, profile_dir):
    if section is None:return {'status':'disabled','items':[],'errors':[],'observed_at':None}
    if pending is None:return {'status':'blocked','items':[],'observed_at':datetime.now(timezone.utc).isoformat(),'errors':[{'code':'APPROVAL_TOOLS_UNAVAILABLE'}]}
    try:
        logs=(pending.configured_logs(local_path(section['config_path'],profile_dir)) if 'config_path' in section
              else [(item['label'],local_path(item['path'],profile_dir)) for item in section['logs']])
        if not logs:raise ValueError('No configured approval logs')
        items,errors=pending.collect(logs)
        selected=[]
        keys=('request_id','module','status','artifact_version','log')+ (('title',) if section.get('include_titles') else ())
        for item in items:selected.append({key:item[key] for key in keys if key in item})
        return {'status':'blocked' if errors else 'complete','items':selected,'observed_at':datetime.now(timezone.utc).isoformat(),
                'errors':[{'code':'APPROVAL_LOG_UNAVAILABLE'} for error in errors]}
    except (OSError,ValueError,TypeError,KeyError):
        return {'status':'blocked','items':[],'observed_at':datetime.now(timezone.utc).isoformat(),'errors':[{'code':'APPROVAL_CONFIGURATION_INVALID'}]}


def markdown(result):
    labels={'complete':'Datenteil vollständig','partial':'Datenteil teilweise ausgewertet','blocked':'Datenteil blockiert'}
    lines=['# Technischer Wochencheck', '', labels[result['status']], '',
           'Fachliche Einordnung durch den Harness steht aus. Keine Freigabe oder Außenaktion.', '',
           'Lauf: '+result['run_id'], 'Stichtag: '+result['logical_as_of'], '']
    for source in result['sources']:
        lines.extend(['## '+source['id'], 'Zeitzone: '+source['time_zone'],
                      'A: '+' bis '.join(source['period_a']), 'B: '+' bis '.join(source['period_b'])])
        if source.get('error'):lines.append('Quelle konnte nicht verlässlich ausgewertet werden: '+source['error'])
        for metric in source.get('metrics',[]):
            lines.append('- '+metric['id']+': '+metric['status'])
            if metric.get('error'):lines.append('  Prüfcode: '+metric['error'])
            if 'result' in metric:
                lines.append('  A: '+str(metric['result']['period_a']['value'])+'; B: '+str(metric['result']['period_b']['value']))
            if metric.get('missing_dates'):lines.append('  Datenlücken: '+', '.join(metric['missing_dates']))
    approvals=result['approvals']
    lines.extend(['','## Offene Freigaben','Prüfstatus: '+approvals['status']])
    for item in approvals['items']:lines.append('- '+item['request_id']+': '+item['status'])
    if approvals['errors']:lines.append('Keine Entwarnung: mindestens eine Freigabequelle ist unklar.')
    lines.extend(['','## Nächster Schritt','Der Harness prüft Definitionen, Unsicherheit und Alternativerklärungen und schreibt eine separate fachliche Einordnung.',''])
    return '\n'.join(lines).encode('utf-8')


def run(profile_path, harness_authorized=False, as_of=None, post=None):
    if harness_authorized is not True:raise ValueError('Current source/report permissions must be checked by the harness')
    profile,profile_dir,sha,profile_bytes=load_profile(profile_path)
    at=zoned(as_of) if as_of else datetime.now(timezone.utc)
    output=private_output(profile['output_dir'],profile_dir)
    output.mkdir(mode=0o700,parents=True,exist_ok=True)
    lock=output/('.weekly-'+profile['id']+'.lock')
    fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    try:
        folder=output/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex)
        folder.mkdir(mode=0o700)
        write(folder/'profile.json',profile_bytes)
        events=folder/'events.jsonl'
        write(events,b'')
        def event(kind, **values):
            with events.open('ab') as stream:
                stream.write(json.dumps({'type':kind,'recorded_at':datetime.now(timezone.utc).isoformat(),**values},ensure_ascii=False).encode()+b'\n')
                stream.flush();os.fsync(stream.fileno())
        result={'schema_version':'0.1','run_id':folder.name,'profile_id':profile['id'],'profile_sha256':sha,
                'logical_as_of':at.isoformat(),'started_at':datetime.now(timezone.utc).isoformat(),
                'scope':'technical_data_review_only','review_status':'pending_harness_review','sources':[]}
        event('started',profile_sha256=sha,logical_as_of=at.isoformat())
        computed=0;imperfect=False
        for source in profile['sources']:
            a,b=windows(profile,source,at)
            row={'id':source['id'],'kind':source['kind'],'time_zone':source['time_zone'],
                 'period_a':[d.isoformat() for d in a],'period_b':[d.isoformat() for d in b],'metrics':[]}
            result['sources'].append(row)
            try:
                csv_path,manifest_path,manifest,hashes=acquire(source,profile_dir,folder/source['id'],a,b,post or fetch_google.http_post)
                row['dataset_extracted_at']=manifest['extracted_at']
                row['privacy_class']=manifest['privacy_class']
                row['dataset']={key:manifest[key] for key in ('dataset_id','extracted_at','time_zone','period_start','period_end','grain','privacy_class')}
                row.update(hashes,csv_path=csv_path.relative_to(folder).as_posix(),manifest_path=manifest_path.relative_to(folder).as_posix())
            except (OSError,ValueError,TypeError,KeyError,IndexError,AttributeError,OverflowError) as error:
                row.update(status='blocked',error=error.code if isinstance(error,StepFailure) else 'SOURCE_UNAVAILABLE_OR_INVALID');imperfect=True
                event('source_blocked',source_id=source['id'],code=row['error']);continue
            for metric in source['metrics']:
                item={'id':metric['id']};row['metrics'].append(item)
                try:
                    calculation,missing,computable,segment_column=evaluate_metric(csv_path,manifest,source,metric,a,b)
                    item.update(result=calculation,missing_dates=missing,segment_column=segment_column,status='complete' if computable and not missing else 'partial')
                    if computable:computed+=1
                    if missing or not computable:imperfect=True
                except (OSError,ValueError,TypeError,KeyError) as error:
                    item.update(status='blocked',error=error.code if isinstance(error,StepFailure) else 'METRIC_UNAVAILABLE_OR_INVALID');imperfect=True
            row['status']='complete' if all(item['status']=='complete' for item in row['metrics']) else 'partial' if any('result' in item for item in row['metrics']) else 'blocked'
            event('source_evaluated',source_id=source['id'],status=row['status'],**hashes)
        result['approvals']=approval_snapshot(profile.get('approvals'),profile_dir)
        if result['approvals']['status']=='blocked':imperfect=True
        result['status']='blocked' if not computed else 'partial' if imperfect else 'complete'
        result['computed_metrics']=computed
        result['finished_at']=datetime.now(timezone.utc).isoformat()
        context={'run_id':result['run_id'],'profile_sha256':sha,'purpose':profile['purpose'],
                 'logical_as_of':result['logical_as_of'],'technical_status':result['status'],
                 'review_status':result['review_status'],'sources':[{k:v for k,v in source.items() if k not in ('csv_path','manifest_path','dataset')}
                                                                   for source in result['sources']],
                 'approvals':result['approvals'],
                 'limitations':['Aggregate summaries only; raw CSV and source notes are not included.',
                                'Different source timezones/lags may produce different comparison windows.',
                                'Technical completeness is not a factual, causal or legal approval.']}
        write(folder/'harness-context.json',context)
        write(folder/'report.md',markdown(result))
        event('finished',status=result['status'],computed_metrics=computed)
        result['artifacts']={name:digest(read(folder/name)) for name in ('profile.json','harness-context.json','report.md','events.jsonl')}
        # Final marker written last. A run without result.json is incomplete, never "all clear".
        temporary=folder/'result.tmp'
        write(temporary,result)
        sync_directory(folder)
        os.replace(str(temporary),str(folder/'result.json'))
        sync_directory(folder)
        sync_directory(output)
        return {'status':result['status'],'review_status':result['review_status'],'run_dir':str(folder),
                'result_sha256':digest(read(folder/'result.json')),'context':str(folder/'harness-context.json')}
    finally:
        lock.unlink()
        sync_directory(output)


def init_demo(directory):
    directory=private_output(str(directory),Path.cwd())
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    profile=decode(read(EXAMPLES/'weekly-review-demo.json'))
    for name in ('weekly-review-demo.csv','weekly-review-demo.manifest.json'):
        write(directory/name,read(EXAMPLES/name))
    profile['output_dir']='runs'
    profile['sources'][0]['csv_path']='weekly-review-demo.csv'
    profile['sources'][0]['manifest_path']='weekly-review-demo.manifest.json'
    write(directory/'profile.json',profile)
    return {'profile':str(directory/'profile.json'),'synthetic':True,'schedule_installed':False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    demo=commands.add_parser('demo');demo.add_argument('--directory',type=Path,required=True)
    for name in ('plan','run'):
        sub=commands.add_parser(name);sub.add_argument('--profile',type=Path,required=True)
        sub.add_argument('--as-of',help='Explicit zoned logical cutoff, recorded separately from actual execution')
        if name=='run':sub.add_argument('--harness-authorized',action='store_true')
    args=parser.parse_args(argv)
    try:
        if args.command=='demo':result=init_demo(args.directory)
        elif args.command=='plan':result=plan(args.profile,args.as_of)
        else:result=run(args.profile,args.harness_authorized,args.as_of)
    except (OSError,ValueError,TypeError,KeyError,OverflowError) as error:
        print(json.dumps({'status':'blocked','error':'CONFIGURATION_OR_RUN_FAILURE','error_type':type(error).__name__,
                          'notice':'Bei einem Abbruch private Laufartefakte/Sperre prüfen; keine erfolgreiche Auswertung behaupten.'}),file=sys.stderr)
        return 2
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return {'complete':0,'partial':1,'blocked':2}.get(result.get('status'),0)


if __name__=='__main__':sys.exit(main())
