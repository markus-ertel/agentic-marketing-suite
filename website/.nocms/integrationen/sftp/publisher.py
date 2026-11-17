#!/usr/bin/env python3
"""Plan an immutable website transfer; execute only with current approval using OpenSSH SFTP."""
import argparse
import hashlib
import ipaddress
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / '.suite/capabilities'))
from runtime import (CapabilityError, CheckError, clean_string, digest, load_json, relative_file,
                     bound_execution_log, require_approval, run_once, snapshot_json, write_json)
from private_files import is_private
from execution_authority import require_execution_authority

PRIVATE = {'.git', '.aws', '.ssh', '.codex', '.nocrm', '.nocms', 'node_modules', '__pycache__'}


def safe_path(value, absolute=False):
    clean_string(value, 'path')
    if any(char in value for char in '\\"*?[]$`'):
        raise CapabilityError('Unsupported path metacharacter')
    path = PurePosixPath(value)
    if path.is_absolute() != absolute or '..' in path.parts or (absolute and str(path) == '/'):
        raise CapabilityError('Unsafe path')
    for part in path.parts:
        folded = part.casefold()
        if (folded in PRIVATE or is_private(part, export=True) or (folded.startswith('.') and folded != '.htaccess')):
            raise CapabilityError('Private files must not be deployed')
    return path


def validate_config(value):
    if not isinstance(value, dict) or set(value) != {'type', 'source', 'target', 'host', 'port', 'username', 'credential_ref', 'delete_remote', 'verify_upload', 'release_archive'}:
        raise CapabilityError('Deployment configuration fields do not match the SFTP contract')
    if value['type'] != 'sftp' or value['delete_remote'] is not False or value['verify_upload'] is not True:
        raise CapabilityError('Only SFTP with readback verification and no remote deletion is supported')
    if type(value['port']) is not int or not 1 <= value['port'] <= 65535:
        raise CapabilityError('Invalid port')
    if not isinstance(value['host'], str) or '%' in value['host']:
        raise CapabilityError('Invalid host')
    try:
        ipaddress.ip_address(value['host'])
    except ValueError:
        if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', value['host']):
            raise CapabilityError('Invalid host')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9._-]*', value['username']):
        raise CapabilityError('Invalid username')
    if not re.fullmatch(r'[A-Z][A-Z0-9_]*', value['credential_ref']):
        raise CapabilityError('credential_ref must name an environment-variable prefix')
    safe_path(value['source'])
    safe_path(value['release_archive'])
    safe_path(value['target'], absolute=True)
    return value


def target(config):
    host = '[' + config['host'] + ']' if ':' in config['host'] else config['host']
    return f"sftp:{config['username']}@{host}:{config['port']}{str(PurePosixPath(config['target']))}"


def source_files(root, source_value):
    root = Path(root).resolve(strict=True)
    safe_path(source_value)
    source = (root / source_value).resolve(strict=True)
    try:
        source.relative_to(root)
    except ValueError:
        raise CapabilityError('Source escapes project root')
    if not source.is_dir():raise CapabilityError('Source must be a directory')
    files = []
    for path in sorted(source.rglob('*')):
        relative = path.relative_to(source).as_posix()
        safe_path(relative)
        if path.is_symlink():raise CapabilityError('Symlinks are not published')
        if path.is_file():
            if path.stat().st_size > 100 * 1024 * 1024:raise CapabilityError('A file exceeds the 100 MiB transfer limit')
            files.append({'path': relative, 'sha256': digest(path), 'size': path.stat().st_size})
    if not files or not any(item['path']=='index.html' for item in files):
        raise CapabilityError('A noCMS release needs index.html at the site root')
    return root, source, files


def make_archive(root, source_value, relative):
    root, source, files = source_files(root, source_value)
    safe_path(relative)
    archive = root / relative
    archive.parent.resolve(strict=True).relative_to(root)
    if source == archive.parent or source in archive.parents or archive.is_symlink():
        raise CapabilityError('Release archive must be outside the published source')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as output:
        for item in files:output.write(source/item['path'], arcname=item['path'])
    return {'path':relative, 'sha256':digest(archive)}


def plan(root, config):
    validate_config(config)
    root, source, files = source_files(root, config['source'])
    archive = relative_file(root, config['release_archive'])
    if source == archive.parent or source in archive.parents:raise CapabilityError('Archive must not be published')
    expected = {item['path']:item for item in files}
    with zipfile.ZipFile(archive) as zipped:
        members = [item for item in zipped.infolist() if not item.is_dir()]
        if len(members)!=len(expected) or len({item.filename for item in members})!=len(members):
            raise CapabilityError('Release archive or source changed')
        for member in members:
            item = expected.get(member.filename)
            if item is None or member.file_size!=item['size']:raise CapabilityError('Release archive or source changed')
            checksum=hashlib.sha256()
            with zipped.open(member) as stream:
                for block in iter(lambda:stream.read(65536), b''):checksum.update(block)
            if checksum.hexdigest()!=item['sha256']:raise CapabilityError('Release archive or source changed')
    value = {'capability':'website.sftp','version':'0.1','deployment':config,'files':files,
             'release_archive':{'path':config['release_archive'],'sha256':digest(archive)},
             'action':'publish','target':target(config)}
    if len(json.dumps(value).encode())>1024*1024:raise CapabilityError('Plan exceeds 1 MiB')
    return value


def quoted(path):
    # All command-language metacharacters have already been rejected; spaces stay quoted.
    return '"' + str(path) + '"'


def transfer(value, root, runner=subprocess.run, revalidate=None):
    if revalidate is None:raise CapabilityError('An execution-gate callback is required')
    config = validate_config(value['deployment'])
    if value != plan(root, config):
        raise CapabilityError('Deployment plan or source files changed')
    prefix = config['credential_ref']
    key = Path(os.environ[prefix + '_KEY_FILE']).resolve(strict=True)
    known = Path(os.environ[prefix + '_KNOWN_HOSTS_FILE']).resolve(strict=True)
    if any(char in str(key) + str(known) for char in '\r\n\"%'):
        raise CapabilityError('Credential paths contain unsupported SSH option tokens')
    if not key.is_file() or not known.is_file():
        raise CapabilityError('SSH key and preverified known_hosts must exist')
    executable = shutil.which('sftp')
    if not executable:
        raise CapabilityError('OpenSSH sftp is not installed')
    host = '[' + config['host'] + ']' if ':' in config['host'] else config['host']
    command = [executable, '-F', os.devnull, '-q', '-b', '-', '-P', str(config['port']), '-i', str(key),
               '-oBatchMode=yes', '-oIdentitiesOnly=yes', '-oStrictHostKeyChecking=yes',
               '-oUserKnownHostsFile=' + quoted(known), '-oGlobalKnownHostsFile=' + os.devnull,
               '-oPermitLocalCommand=no', '-oClearAllForwardings=yes', '-oForwardAgent=no',
               '-oControlMaster=no', '-oControlPath=none', '-oConnectTimeout=15', config['username'] + '@' + host]
    with tempfile.TemporaryDirectory(prefix='suite-publish-') as temporary:
        stage = Path(temporary)
        upload, activate, verify = [], [], []
        directories = sorted({str(PurePosixPath(item['path']).parent) for item in value['files'] if '/' in item['path']}, key=lambda p: (p.count('/'), p))
        # The target must exist. Subdirectory creation never deletes an existing remote file.
        upload.append('cd ' + quoted(config['target']))
        all_directories = set()
        for directory in directories:
            path = PurePosixPath(directory)
            all_directories.update(str(parent) for parent in (path, *path.parents) if str(parent) != '.')
        for directory in sorted(all_directories, key=lambda p: (p.count('/'), p)):
            upload.append('-mkdir ' + quoted(str(PurePosixPath(config['target']) / directory)))
        for index, item in enumerate(value['files']):
            original = relative_file(root, str(PurePosixPath(config['source']) / item['path']))
            staged = stage / ('source-' + str(index))
            shutil.copyfile(original, staged)
            if digest(staged) != item['sha256']:
                raise CapabilityError('File changed while staging')
            final = PurePosixPath(config['target']) / item['path']
            # Preserve the extension so temporary PHP uploads cannot be served as plain source.
            remote = final.parent / ('.suite-upload-' + uuid.uuid4().hex + final.suffix)
            upload += ['put ' + quoted(staged) + ' ' + quoted(remote),
                       'get ' + quoted(remote) + ' ' + quoted(stage / ('check-' + str(index)))]
            activate.append('rename ' + quoted(remote) + ' ' + quoted(final))
            verify.append('get ' + quoted(final) + ' ' + quoted(stage / ('final-' + str(index))))
        def batch(lines):
            result = runner(command, input='\n'.join(lines) + '\n', text=True, capture_output=True, timeout=300)
            if result.returncode:
                raise CapabilityError('SFTP transfer interrupted; partial remote state requires investigation')
        revalidate()
        batch(upload)
        for index, item in enumerate(value['files']):
            if digest(stage / ('check-' + str(index))) != item['sha256']:
                raise CapabilityError('Uploaded bytes do not match the approved release')
        revalidate()
        batch(activate)
        batch(verify)
        for index, item in enumerate(value['files']):
            if digest(stage / ('final-' + str(index))) != item['sha256']:
                raise CapabilityError('Final readback differs')
    return {'status': 'confirmed', 'verification': 'sftp-readback-sha256', 'file_count': len(value['files']),
            'notice': 'Transfer verified; HTTP rendering, PHP behavior and whole-release atomicity are not certified'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    archive = sub.add_parser('archive');archive.add_argument('--source',required=True);archive.add_argument('--output',required=True)
    prepare = sub.add_parser('plan');prepare.add_argument('--config', type=Path, required=True);prepare.add_argument('--output', type=Path, required=True)
    execute = sub.add_parser('execute')
    for name in ('plan', 'approvals', 'request-id', 'execution-log', 'key'):
        execute.add_argument('--' + name, required=True)
    execute.add_argument('--harness-authorized', action='store_true', help='Harness has verified identity, legal basis and tool authority')
    args = parser.parse_args()
    try:
        if args.command == 'archive':
            result = {'status':'archived', **make_archive(args.root,args.source,args.output)}
        elif args.command == 'plan':
            configuration = load_json(args.config)
            if isinstance(configuration, dict) and set(configuration) == {'deployment'}:configuration = configuration['deployment']
            value = plan(args.root, configuration);write_json(args.output, value)
            result = {'status': 'planned', 'file_count': len(value['files']), 'target': value['target']}
        else:
            if not args.harness_authorized:
                raise CapabilityError('Harness authority attestation is required')
            value, loaded_hash = snapshot_json(args.plan)
            if value != plan(args.root, value['deployment']):
                raise CapabilityError('Plan changed')
            def gate():
                authority = require_execution_authority(args.approvals, args.execution_log, 'website.sftp')
                return require_approval(args.approvals, args.request_id, args.root, args.plan, 'publish', value['target'], loaded_hash,
                                        key_path=authority['approval_key_file'])
            approval = gate()
            result = run_once(bound_execution_log(args.approvals, args.execution_log), args.key, 'website.sftp', approval, lambda: transfer(value, args.root, revalidate=gate))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'] in ('archived', 'planned', 'confirmed') else 2
    except (CapabilityError, CheckError, OSError, ValueError, KeyError, TypeError, RuntimeError, zipfile.BadZipFile):
        print('SFTP_BLOCKED: invalid plan, credentials, approval or transport configuration', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
