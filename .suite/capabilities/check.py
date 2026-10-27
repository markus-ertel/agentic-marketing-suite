#!/usr/bin/env python3
"""Offline capability contract/entrypoint checks, not a live account or hosting approval."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from validate_records import check,CheckError
ROOT=Path(__file__).resolve().parents[2]


def main():
    try:
        modules=json.loads((ROOT/'.suite/contracts/work-order.schema.json').read_text())['properties']['lead_module']['enum']
        ids=set();count=0
        for directory in ('website/.nocms/module','website/.nocms/integrationen','noCRM/.nocrm/integrationen','analytics/.analytics/tools','.suite/tools'):
            for path in (ROOT/directory).rglob('capability.json'):
                value=json.loads(path.read_text());check('capability',value)
                if value['id'] in ids:raise CheckError('Duplicate capability ID')
                if value['owner_module'] not in modules:raise CheckError('Unknown capability owner')
                for field in ('entrypoint','configuration'):
                    relative=Path(value[field])
                    if relative.is_absolute() or '..' in relative.parts:raise CheckError('Unsafe capability reference')
                    target=(ROOT/relative).resolve(strict=True)
                    target.relative_to(ROOT)
                    if not target.is_file():raise CheckError('Missing capability reference')
                ids.add(value['id']);count+=1
        if count<8:raise CheckError('Incomplete capability package')
        print(f'CAPABILITY_CONTRACTS_OK: {count} optional capabilities; no live execution')
        return 0
    except (CheckError,ValueError,OSError,KeyError,TypeError) as error:
        print('CAPABILITY_CHECK_BLOCKED:',str(error),file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
