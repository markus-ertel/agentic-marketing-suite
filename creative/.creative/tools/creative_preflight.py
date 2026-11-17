#!/usr/bin/env python3
"""Creative v0.1: structured job preflight, NOT a PDF/X validator.
Usage: python creative_preflight.py /path/to/creative-job.json [--report report.json]
Exit 0 = structurally acceptable draft/proof; 2 = blocking structural issues.
"""
import os
import json, argparse, sys, hashlib, re
from pathlib import Path

ALLOWED_MEDIUM={'print','digital_image','video','audio','animation','multimedia'}
ALLOWED_STATUSES={'draft','concept_review','production','technical_qa','visual_qa','rework','approval_pending','approved','released'}

def check(job):
    problems=[]; warnings=[]
    def fail(msg): problems.append(msg)
    def warn(msg): warnings.append(msg)
    for field in ('schema_version','job_id','title','medium','status','assets','deliverables'):
        if field not in job: fail('Pflichtfeld fehlt: '+field)
    if job.get('schema_version')!='0.1': fail('schema_version muss 0.1 sein')
    if job.get('medium') not in ALLOWED_MEDIUM: fail('Ungültiges Medium')
    if job.get('status') not in ALLOWED_STATUSES: fail('Ungültiger Status')
    if not isinstance(job.get('job_id'),str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{2,63}',job.get('job_id','')): fail('job_id ungültig')
    if not isinstance(job.get('deliverables'),list) or not job['deliverables']: fail('Mindestens ein Ergebnis benötigt')
    assets=job.get('assets',[])
    if not isinstance(assets,list): fail('assets muss Liste sein');assets=[]
    for a in assets:
        if not isinstance(a,dict) or not all(k in a for k in ('id','source','rights_status')): fail('Asset-Metadaten unvollständig');continue
        if a['rights_status']!='verified': warn(f"Asset {a['id']}: Rechte noch nicht geprüft")
    ps=job.get('print_spec',{})
    if job.get('medium')=='print':
        if not isinstance(ps,dict): fail('print_spec muss Objekt sein');ps={}
        for k in ['trim_width_mm','trim_height_mm']:
            if not isinstance(ps.get(k),(int,float)) or ps.get(k)<=0: fail('Ungültiges Druckformat: '+k)
        if ps.get('bleed_mm') is not None and (not isinstance(ps['bleed_mm'],(int,float)) or ps['bleed_mm']<0): fail('Ungültiger Beschnitt')
        for k in ['provider','output_profile','acceptance_profile']:
            if not ps.get(k): warn('Vor Druckfreigabe fehlt Druckereiparameter: '+k)
        # A requested PDF/X format is only a request, NEVER evidence.
        if ps.get('requested_pdf_standard') and not job.get('qa',{}).get('pdfx_report'):
            warn('PDF/X angefordert, aber kein externer PDF/X-Prüfbericht vorhanden')
    qa=job.get('qa') or {}
    if not isinstance(qa,dict): fail('qa muss Objekt sein');qa={}
    approved=job.get('status') in {'approved','released'}
    if approved:
        if any(a.get('rights_status')!='verified' for a in assets if isinstance(a,dict)) or qa.get('rights')!='passed':fail('Freigabe nicht möglich: Rechte nicht geprüft')
        if qa.get('technical')!='passed' or qa.get('visual')!='passed':fail('Freigabe nicht möglich: technische und visuelle QA fehlen')
        if not qa.get('qa_artifact_sha256') or not re.fullmatch('[0-9a-f]{64}',str(qa.get('qa_artifact_sha256'))): fail('Freigabe braucht gültigen geprüften Datei-Hash')
        ap=job.get('approval') or {}
        if not isinstance(ap,dict) or not all(ap.get(k) for k in ('approved_by','approved_at','scope')): fail('Freigabe braucht Person, Zeitpunkt und Scope')
        if job.get('medium')=='print':
            for k in ('provider','output_profile','acceptance_profile'):
                if not ps.get(k):fail('Printfreigabe ohne '+k+' unzulässig')
            if not qa.get('pdfx_validator') or not qa.get('pdfx_report'):fail('Printfreigabe ohne externen PDF/X-Validator und Report unzulässig')
            finals=[d for d in job.get('deliverables',[]) if isinstance(d,dict) and d.get('purpose')=='final']
            if not any(d.get('format','').lower()=='pdf' for d in finals):fail('Printfreigabe ohne finalen PDF-Eintrag unzulässig')
    # A report reference does not prove it exists or validates a real PDF.
    return {'ok':not problems,'blockers':problems,'warnings':warnings,'scope':'manifest_structure_only','print_ready_claim':False}


def safe_output(path):
    """Write only new files below the current directory: no overwrite, no symlink, no escape."""
    base = Path.cwd().resolve()
    target = (base / Path(path)).resolve()
    if target != base and base not in target.parents:
        raise ValueError('Output must stay inside the current working directory')
    for parent in [base / Path(path), *(base / Path(path)).parents]:
        if parent == base:
            break
        if parent.is_symlink():
            raise ValueError('Output path must not contain symlinks')
    if target.exists():
        raise ValueError('Output already exists; choose a new file name')
    return target


def write_new_text(path, text):
    target = safe_output(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(str(target), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        stream.write(text)

def main():
    p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('--report');a=p.parse_args()
    try: job=json.loads(Path(a.manifest).read_text(encoding='utf-8'))
    except Exception as e: print(json.dumps({'ok':False,'blockers':['JSON-Ladefehler: '+str(e)]},ensure_ascii=False,indent=2));return 2
    if not isinstance(job,dict):print(json.dumps({'ok':False,'blockers':['JSON muss Objekt sein']},ensure_ascii=False));return 2
    result=check(job);result['manifest_sha256']=hashlib.sha256(Path(a.manifest).read_bytes()).hexdigest()
    if a.report:
        try:write_new_text(a.report,json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        except (ValueError,OSError) as e:print('REPORT_BLOCKED:',e,file=sys.stderr);return 2
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['ok'] else 2

if __name__=='__main__':sys.exit(main())
