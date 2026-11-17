#!/usr/bin/env python3
"""Create a deliberately generic, editable RGB SVG concept PROOF for print layout.
Not a PDF/X generator. No commercial rights, prepress, or brand compliance implied.
Usage: python svg_proof.py creative-job.json output.svg
"""
import os
import argparse,json,sys,html
from pathlib import Path

def make(job):
    if job.get('medium')!='print': raise ValueError('Only print manifests supported')
    ps=job.get('print_spec') or {};w=float(ps['trim_width_mm']);h=float(ps['trim_height_mm']);b=float(ps.get('bleed_mm') or 0)
    if not (10<=w<=3000 and 10<=h<=3000 and 0<=b<=50):raise ValueError('Invalid geometry')
    # SVG user-space matches mm; trim and bleed shown as separate guides, not proof of adequate bleed content.
    title=html.escape(str(job.get('title','KONZEPT')))[:90]
    jobid=html.escape(str(job.get('job_id','demo')))[:64]
    full_w=w+2*b;full_h=h+2*b
    title_size=min(15,max(5,w/12))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{full_w:g}mm" height="{full_h:g}mm" viewBox="0 0 {full_w:g} {full_h:g}">
  <title>Creative Layout Proof – NOT PRINT READY</title>
  <desc>Editable RGB concept with trim guide. Color management, font embedding and PDF/X validation are NOT performed.</desc>
  <rect x="0" y="0" width="{full_w:g}" height="{full_h:g}" fill="#f0ebe4"/>
  <rect x="{b:g}" y="{b:g}" width="{w:g}" height="{h:g}" fill="#f0ebe4" stroke="#e96b4e" stroke-width="0.5" stroke-dasharray="2 2"/>
  <rect x="{b+10:g}" y="{b+10:g}" width="{max(1,w-20):g}" height="{max(1,h-20):g}" fill="none" stroke="#9a9a9a" stroke-width="0.35" stroke-dasharray="1.5 3"/>
  <rect x="{b+15:g}" y="{b+18:g}" width="{max(1,w-30):g}" height="{max(1,h*0.42):g}" rx="2" fill="#203440"/>
  <text x="{b+18:g}" y="{b+h*0.55:g}" fill="#172b37" font-size="{title_size:g}" font-family="sans-serif" font-weight="bold">KONZEPTPROOF</text>
  <text x="{b+18:g}" y="{b+h*0.62:g}" fill="#172b37" font-size="4.4" font-family="sans-serif">{title}</text>
  <text x="{b+18:g}" y="{b+h*0.72:g}" fill="#5c6265" font-size="3.3" font-family="sans-serif">Beispiel: Hier entsteht ein verifizierter Werbetext.</text>
  <text x="{b+18:g}" y="{b+h-18:g}" fill="#a6442f" font-size="3.2" font-family="sans-serif">NUR ENTWURF · KEIN DRUCK-PDF/X · {jobid}</text>
</svg>
"""

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
    p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('output');a=p.parse_args()
    try:
        job=json.loads(Path(a.manifest).read_text(encoding='utf-8'));data=make(job)
        write_new_text(a.output,data)
        print('SVG-PROOF:',a.output,'– NOT PRINT READY');return 0
    except Exception as e: print('ERROR:',e,file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
