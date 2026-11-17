#!/usr/bin/env python3
"""Read-only, standard-library CSV comparison for additive counts and weighted rates.
No causality, significance or API integrations are implied.
"""
import os
import argparse
import csv
import datetime as dt
import json
import math
import pathlib
from pathlib import Path
import sys


def window(text):
    try:
        a,b=text.split(':',1)
        lo,hi=dt.date.fromisoformat(a),dt.date.fromisoformat(b)
    except (ValueError,TypeError) as e:
        raise ValueError('Zeitraum muss YYYY-MM-DD:YYYY-MM-DD sein') from e
    if lo>hi: raise ValueError('Periodenanfang liegt nach Periodenende')
    return lo,hi


def number(value, column, line):
    if value is None or not str(value).strip():
        raise ValueError(f'Zeile {line}: fehlender Zahlenwert in {column}')
    try: n=float(value)
    except ValueError as e: raise ValueError(f'Zeile {line}: ungültige Zahl in {column}') from e
    if not math.isfinite(n) or n<0:
        raise ValueError(f'Zeile {line}: {column} muss endlich und nichtnegativ sein')
    return n


def analyze(path, date_column, numerator, denominator, period_a, period_b, segment_column=None, segment=None, expected_direction='unknown',source_id=None):
    if segment and not segment_column:
        raise ValueError('Mit --segment muss auch --segment-column angegeben werden')
    if period_a[0]<=period_b[1] and period_b[0]<=period_a[1]:
        raise ValueError('Vergleichszeiträume dürfen sich nicht überschneiden')
    if not path.is_file(): raise ValueError('CSV-Datei nicht gefunden')
    if path.stat().st_size > 30_000_000: raise ValueError('Datei für Demo-Werkzeug zu groß (max. 30 MB)')
    required={date_column,numerator}
    if denominator: required.add(denominator)
    if segment_column: required.add(segment_column)
    rows={'a':[],'b':[]}
    seen=set()
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames is None: raise ValueError('CSV enthält keine Kopfzeile')
        if len(reader.fieldnames)!=len(set(reader.fieldnames)): raise ValueError('Doppelte Spaltennamen')
        missing=required-set(reader.fieldnames)
        if missing: raise ValueError('Fehlende Spalten: '+', '.join(sorted(missing)))
        for line,row in enumerate(reader,2):
            try: date=dt.date.fromisoformat(row[date_column])
            except (ValueError,TypeError) as e: raise ValueError(f'Zeile {line}: Datum muss YYYY-MM-DD sein') from e
            if row.get(None): raise ValueError(f'Zeile {line}: zusätzliche CSV-Felder')
            if segment is not None and row[segment_column]!=segment: continue
            num=number(row[numerator],numerator,line)
            den=number(row[denominator],denominator,line) if denominator else None
            # A CSV row represents an observation at the supplied grain. Duplicates are possible
            # only if the provider guarantees multiple legitimate disjoint rows; this demo errs closed.
            key=(date,row[segment_column] if segment_column else None)
            if key in seen: raise ValueError(f'Zeile {line}: doppeltes Datum/Segment für unbestätigte Granularität')
            seen.add(key)
            bucket='a' if period_a[0]<=date<=period_a[1] else 'b' if period_b[0]<=date<=period_b[1] else None
            if bucket: rows[bucket].append((date,num,den))
    if not rows['a'] or not rows['b']: raise ValueError('Mindestens ein Vergleichszeitraum hat keine Messzeilen')
    def summary(data):
        n=sum(item[1] for item in data)
        d=sum(item[2] for item in data) if denominator else None
        return {'observations':len(data),'first_date':min(x[0] for x in data).isoformat(),
                'last_date':max(x[0] for x in data).isoformat(),
                'numerator_sum':n,'denominator_sum':d,
                'value':n/d if denominator and d!=0 else None if denominator else n}
    a,b=summary(rows['a']), summary(rows['b'])
    va,vb=a['value'],b['value']
    change=vb-va if va is not None and vb is not None else None
    relative=change/va if change is not None and va!=0 else None
    warnings=[]
    if a['observations']<5 or b['observations']<5: warnings.append('Wenige Messzeilen: Trend/Variabilität nicht robust abschätzbar.')
    if (period_a[1]-period_a[0]).days != (period_b[1]-period_b[0]).days:
        warnings.append('Vergleichsfenster sind unterschiedlich lang: Summen nicht unmittelbar fair vergleichbar.')
    if denominator and (a['denominator_sum']==0 or b['denominator_sum']==0): warnings.append('Rate nicht berechenbar: Nenner in mindestens einem Zeitfenster = 0.')
    if va==0: warnings.append('Relative Änderung bei Null-Baseline nicht definiert.')
    if denominator and (a['denominator_sum']<30 or b['denominator_sum']<30): warnings.append('Kleiner Nenner: ratebezogene Schlussfolgerungen besonders unsicher.')
    if expected_direction=='unknown': warnings.append('Keine Zielrichtung angegeben: Höhere oder niedrigere Werte sind nicht automatisch besser.')
    warnings += ['Beobachteter Unterschied ist kein Nachweis der Ursache oder Inkrementalität.',
                 'Datenqualität, Population, Quellendefinitionen und externe Effekte wurden nicht unabhängig validiert.',
                 'Keine Signifikanz- oder Konfidenzbehauptung ohne geeignetes Studiendesign.']
    direction='not_computable' if change is None else 'up' if change>0 else 'down' if change<0 else 'stable'
    suggestion=('Datenlage/Definitionen prüfen und besseres Messdesign aufsetzen.' if change is None
                else 'Veränderung anhand Tracking, Saisonalität, Zielgruppe und Alternativerklärungen prüfen; vor großem Eingriff klein testen.')
    return {'analysis_id':'csv-period-comparison-v0.1','source_id':source_id or path.name,'date_column':date_column,
            'numerator':numerator,'denominator':denominator,'segment':segment,'expected_direction':expected_direction,
            'period_a':{'start':period_a[0].isoformat(),'end':period_a[1].isoformat(),**a},
            'period_b':{'start':period_b[0].isoformat(),'end':period_b[1].isoformat(),**b},
            'difference':change,'relative_change':relative,'direction':direction,'evidence_level':'descriptive',
            'warnings':warnings,'recommendation':suggestion}



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

def main(argv=None):
    p=argparse.ArgumentParser(description='Deskriptiver Vergleich CSV-Zeitfenster (keine Kausalanalyse).')
    p.add_argument('--input',required=True,type=pathlib.Path)
    p.add_argument('--date-column',default='date')
    p.add_argument('--metric',required=True,help='Additive Zählgröße oder Zähler einer gewichteten Rate')
    p.add_argument('--denominator',help='Nenner für gewichtete Rate (nicht Einzelquoten mitteln)')
    p.add_argument('--period-a',required=True,help='YYYY-MM-DD:YYYY-MM-DD')
    p.add_argument('--period-b',required=True,help='YYYY-MM-DD:YYYY-MM-DD')
    p.add_argument('--segment-column'); p.add_argument('--segment')
    p.add_argument('--source-id')
    p.add_argument('--expected-direction',choices=['up','down','unknown'],default='unknown')
    p.add_argument('--output',type=pathlib.Path,help='Optionaler JSON-Ergebnisexport')
    a=p.parse_args(argv)
    try:
        result=analyze(a.input,a.date_column,a.metric,a.denominator,window(a.period_a),window(a.period_b),a.segment_column,a.segment,a.expected_direction,a.source_id)
    except (ValueError,PermissionError,OSError) as e:
        print('PRECHECK_FAIL:',str(e),file=sys.stderr); return 2
    output=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if a.output:
        try:write_new_text(a.output,output)
        except (ValueError,OSError) as e:print('OUTPUT_BLOCKED:',str(e),file=sys.stderr);return 2
    else: print(output,end='')
    return 0
if __name__=='__main__': raise SystemExit(main())
