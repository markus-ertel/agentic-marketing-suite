"""Opt-in: two real Codex sessions, external file edit and provider resume in temp dirs."""
import json
import shlex
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.app import load_config
from server.files import Files
from server.sessions import Sessions


def wait(manager, ids, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for sid in ids:
            observed = manager.get(sid)
            for event in list(observed.interactions.values()):
                request = event['request']
                method = request.get('method')
                params = request.get('params', {})
                # Test authorization is limited to the isolated temporary working directory.
                cwd = Path(params.get('cwd') or observed.adapter.cwd).resolve()
                test_root = manager.files.root
                in_test = cwd == test_root or test_root in cwd.parents
                if method == 'item/fileChange/requestApproval' and in_test:
                    manager.respond(sid, event['request_id'], {'decision':'accept'})
                elif method == 'item/commandExecution/requestApproval' and in_test:
                    command = shlex.split(params.get('command') or '')
                    if len(command) == 3 and command[0] in ('/bin/zsh','/bin/bash','/bin/sh') and command[1] == '-lc' and command[2] == 'printf %s DASHBOARD_FILE_OK > probe.txt':
                        manager.respond(sid, event['request_id'], {'decision':'accept'})
                    else:
                        raise RuntimeError('Unreviewed test command: '+str(params.get('command')))
                else:
                    raise RuntimeError('Unsupported test interaction: '+str(request))
        if all(manager.get(sid).status in ('abgeschlossen', 'Fehler') for sid in ids):
            break
        time.sleep(.2)
    for sid in ids:
        session = manager.get(sid)
        if session.status != 'abgeschlossen':
            errors = [e.get('message') for e in session.events_after(0) if e['type']=='agent.error']
            raise RuntimeError(str({'status':session.status,'errors':errors}))


def main():
    config = load_config(Path(__file__).resolve().parents[1]/'config.json')
    with tempfile.TemporaryDirectory(prefix='dashboard-e2e-') as directory:
        root = Path(directory)
        (root/'marketing').mkdir()
        (root/'creative').mkdir()
        files = Files(root)
        manager = Sessions(config['agents'], files)
        try:
            one = manager.connect('codex','marketing')
            two = manager.connect('codex','creative')
            manager.send(one['id'],'Führe in diesem Arbeitsverzeichnis exakt den Shellbefehl `printf %s DASHBOARD_FILE_OK > probe.txt` aus. Ändere nichts anderes und antworte danach kurz.')
            manager.send(two['id'],'Antworte ausschließlich mit SECOND_SESSION_OK. Verwende keine Werkzeuge und ändere keine Dateien.')
            wait(manager,[one['id'],two['id']])
            assert files.preview('marketing/probe.txt')['source'].strip() == 'DASHBOARD_FILE_OK'
            assert not list((root/'creative').iterdir())
            assert manager.get(one['id']).external_id != manager.get(two['id']).external_id
            external = manager.get(one['id']).external_id
            manager.disconnect(one['id'])
            resumed = manager.connect('codex','marketing',external)
            assert resumed['external_id'] == external
            manager.send(resumed['id'],'Antworte ausschließlich mit RESUME_OK. Verwende keine Werkzeuge.')
            wait(manager,[resumed['id']])
            print(json.dumps({'two_real_sessions':'pass','separate_cwd':'pass','external_file_change_visible':'pass','external_resume':'pass'},ensure_ascii=False))
        finally:
            manager.close()


if __name__ == '__main__':
    main()
