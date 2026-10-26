"""Opt-in real-provider smoke. Uses an isolated temporary directory, no domain files."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.app import load_config
from server.files import Files
from server.sessions import Sessions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=['pi','codex','all'], default='all')
    parser.add_argument('--timeout', type=int, default=75)
    args = parser.parse_args()
    config = load_config(Path(__file__).resolve().parents[1] / 'config.json')
    results = []
    with tempfile.TemporaryDirectory(prefix='dashboard-smoke-') as directory:
        manager = Sessions(config['agents'], Files(directory))
        try:
            for profile in manager.profiles():
                if args.profile != 'all' and args.profile != profile['id']:
                    continue
                result = {'profile': profile['id'], 'installed':profile['available']}
                if not profile['available']:
                    results.append(result)
                    continue
                try:
                    session = manager.connect(profile['id'], '')
                    result['connected_status'] = session['status']
                    manager.send(session['id'], 'Antworte ausschließlich mit DASHBOARD_OK. Verwende keine Werkzeuge und ändere keine Dateien.')
                    watched = manager.get(session['id'])
                    deadline = time.monotonic() + args.timeout
                    while time.monotonic() < deadline:
                        snapshot = watched.snapshot()
                        if snapshot['status'] in ('abgeschlossen','Fehler','nicht verbunden'):
                            break
                        time.sleep(0.2)
                    events = watched.events_after(0)
                    result.update({'status':watched.status, 'external_id_present':bool(watched.external_id),
                                   'streamed':any(e['type']=='agent.message.delta' for e in events),
                                   'working_observed':any(e.get('status')=='arbeitet' for e in events),
                                   'errors':[e['message'] for e in events if e['type']=='agent.error'],
                                   'reply': ''.join(e.get('text','') for e in events if e['type']=='agent.message.delta')[:500]})
                    manager.disconnect(session['id'])
                except Exception as exc:
                    result['error'] = str(exc)
                results.append(result)
                print(json.dumps(result, ensure_ascii=False), flush=True)
        finally:
            manager.close()
    return 0 if results and all(r.get('status')=='abgeschlossen' and r.get('streamed') for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
