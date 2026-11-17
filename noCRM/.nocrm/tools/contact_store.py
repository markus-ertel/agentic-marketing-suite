#!/usr/bin/env python3
"""noCRM minimal SINGLE-USER local CSV/JSONL store; no network or sending."""
from pathlib import Path
import argparse
import csv
import json
import os
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone

CONTACT_FIELDS='contact_id,display_name,organization,email,phone,preferred_channel,language,relationship_role,updated_at'.split(',')
CONSENT_FIELDS='contact_id,channel,purpose,status,recorded_at,evidence_ref,basis,valid_until,notes'.split(',')

def atomic_write(path,text):
    path=Path(path)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.tmp-',text=True)
    try:
        os.chmod(tmp,0o600)
        with os.fdopen(fd,'w',encoding='utf-8',newline='') as f: f.write(text)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

# Spreadsheet programs run cells starting with these characters as formulas (CSV injection).
FORMULA_START=('=','+','-','@','\t','\r')

def neutralize(value):
    value=value or ''
    return "'"+value if value.lstrip(' \t\r\n').startswith(FORMULA_START) else value

@contextmanager
def store_lock(path,timeout=10):
    """Serialize read-modify-write so parallel agents cannot silently drop contacts."""
    lock=Path(str(path)+'.lock');deadline=time.monotonic()+timeout
    while True:
        try:fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);break
        except FileExistsError:
            # No stale-lock takeover: after a crash a person removes the lock deliberately.
            if time.monotonic()>deadline:raise ValueError('Contact store is locked; retry later, do not delete an active lock')
            time.sleep(0.05)
    try:
        os.close(fd);yield
    finally:
        lock.unlink()

def init(root):
    root=Path(root).resolve()
    for name in ('kontakte','kommunikation'):
        path=root/name;path.mkdir(parents=True,exist_ok=True,mode=0o700)
    for name,header in [('kontakte/contacts.csv',CONTACT_FIELDS),('kontakte/consents.csv',CONSENT_FIELDS)]:
        p=root/name
        if not p.exists(): atomic_write(p,','.join(header)+'\n')
    p=root/'kommunikation/events.jsonl'
    if not p.exists():
        fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        os.close(fd)
    return root

def add(root,contact_id,display_name,email='',organization='',language=''):
    root=Path(root).resolve();p=root/'kontakte/contacts.csv'
    if not p.exists(): raise ValueError('Workspace not initialized: use init first')
    if not contact_id.strip() or not display_name.strip(): raise ValueError('Contact id and name required')
    if any(ch in contact_id for ch in ('\n','\r','/','\\')) or contact_id.lstrip(' \t\r\n').startswith(FORMULA_START): raise ValueError('Unsafe contact id')
    with store_lock(p):
        with open(p,encoding='utf-8',newline='') as f:
            rdr=csv.DictReader(f)
            if rdr.fieldnames!=CONTACT_FIELDS: raise ValueError('Unexpected CSV fields')
            rows=list(rdr)
        if any(x['contact_id']==contact_id for x in rows): raise ValueError('Contact already exists')
        now=datetime.now(timezone.utc).isoformat()
        rows.append(dict.fromkeys(CONTACT_FIELDS,''))
        rows[-1].update(contact_id=contact_id,display_name=neutralize(display_name),organization=neutralize(organization),
                        email=neutralize(email),language=neutralize(language),updated_at=now)
        from io import StringIO
        f=StringIO(newline='');wr=csv.DictWriter(f,fieldnames=CONTACT_FIELDS);wr.writeheader();wr.writerows(rows)
        atomic_write(p,f.getvalue())
    return True

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='.')
    sub=p.add_subparsers(dest='action',required=True)
    sub.add_parser('init')
    a=sub.add_parser('add-contact');a.add_argument('--id',required=True);a.add_argument('--name',required=True);a.add_argument('--email',default='');a.add_argument('--organization',default='');a.add_argument('--language',default='')
    x=p.parse_args()
    if x.action=='init': print('initialized:',init(x.root))
    elif x.action=='add-contact':add(x.root,x.id,x.name,x.email,x.organization,x.language);print('contact added, NO message sent')
if __name__=='__main__':main()
