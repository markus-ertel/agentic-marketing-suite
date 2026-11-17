#!/usr/bin/env python3
"""Append-only, hash-chained local approval records with signed human decisions.

No external execution or dashboard writes. The signing key authenticates the approving harness,
not a person; it only helps if the AI agent cannot read the key file (separate OS user/service).
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import sys
import secrets
import stat
import uuid

from validate_records import CheckError, check, check_bundle, _dt

DECISIONS = ('approved', 'denied', 'changes_requested', 'revoked')
TRANSITIONS = {'requested': DECISIONS[:3], 'approved': ('revoked',)}
SUBJECT_FIELDS = ('artifact_id', 'artifact_version', 'artifact_sha256', 'action', 'target',
                  'budget_limit', 'currency')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CheckError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def _constant(value):
    raise CheckError('Non-finite JSON number: ' + value)


KEY_ENV = 'SUITE_APPROVAL_KEY_FILE'
GENESIS = '0' * 64


def load_key(path=None, root=None):
    """Signing key of the approving harness. Never inside the suite root, where agents work."""
    path = path or os.environ.get(KEY_ENV)
    if not path:
        raise CheckError('Signing key required: set ' + KEY_ENV + ' (see APPROVALS.md)')
    path = Path(path).resolve(strict=True)
    if root is not None:
        try:
            path.relative_to(Path(root).resolve(strict=True))
            raise CheckError('Signing key must not be stored inside the suite root')
        except ValueError:
            pass
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > 4096:
        raise CheckError('Signing key must be a bounded regular file')
    if os.name == 'posix' and info.st_mode & 0o077:
        raise CheckError('Signing key must have owner-only permissions')
    data = path.read_bytes().strip()
    if len(data) < 32:
        raise CheckError('Signing key too short')
    return data


def key_id(key):
    return hashlib.sha256(key).hexdigest()[:16]


def _signed_bytes(event):
    unsigned = {k: v for k, v in event.items() if k != 'signature'}
    return json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sign(event, key):
    return {'alg': 'hmac-sha256', 'key_id': key_id(key),
            'value': hmac.new(key, _signed_bytes(event), hashlib.sha256).hexdigest()}


def verify_signature(event, key):
    signature = event.get('signature')
    if not isinstance(signature, dict) or signature.get('key_id') != key_id(key):
        raise CheckError('Decision is not signed with the configured approval key')
    expected = hmac.new(key, _signed_bytes(event), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature.get('value', '')):
        raise CheckError('Decision signature does not match; the record was altered or forged')


def keygen(out):
    """Create a new key file with owner-only permissions; never overwrite an existing key."""
    descriptor = os.open(str(out), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(secrets.token_hex(32) + '\n')
    return {'key_file': str(Path(out).resolve()), 'key_id': key_id(Path(out).read_bytes().strip())}


def parse_json(text):
    return json.loads(text, object_pairs_hook=_unique_object, parse_constant=_constant)


def _timestamp(now=None):
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise CheckError('Timezone required')
    return value.isoformat()


def subject(request):
    artifact = request['artifact']
    result = {'artifact_id': artifact['id'], 'artifact_version': artifact['version'],
              'artifact_sha256': artifact['sha256'], 'action': request['action'],
              'target': request['target']}
    for key in ('budget_limit', 'currency'):
        if key in request:
            result[key] = request[key]
    return result


def verify_file(root, request):
    """Hash actual bytes inside the selected root, including resolved symlink containment."""
    root = Path(root).resolve(strict=True)
    path = (root / request['artifact']['path']).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError:
        raise CheckError('Artifact file escapes root')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            digest.update(block)
    if digest.hexdigest() != request['artifact']['sha256']:
        raise CheckError('Artifact file changed: a new version and approval request are required')


def action_approval(request, event):
    """A candidate for the existing contract, never an execution permission by itself."""
    result = {'id': event['id'], **subject(request), 'decision': 'approved',
              'authorizer': event['actor'], 'decided_at': event['occurred_at'],
              'review_refs': [review['id'] for review in request['reviews']],
              'execution_status': 'not_attempted'}
    if 'actor_role' in event:
        result['authorizer_role'] = event['actor_role']
    if 'expires_at' in request:
        result['expires_at'] = request['expires_at']
    return result


def _approved_gates(request, event):
    if 'expires_at' in request and _dt(request['expires_at']) <= _dt(event['recorded_at']):
        raise CheckError('Approval request has expired')
    if any(_dt(review['reviewed_at']) > _dt(event['occurred_at']) for review in request['reviews']):
        raise CheckError('Decision predates review evidence')
    check_bundle({'artifacts': [request['artifact']], 'reviews': request['reviews'],
                  'approvals': [action_approval(request, event)]})


def replay(events):
    """Fail closed on corrupt records, duplicate IDs, subject changes or illegal transitions."""
    states, ids = {}, set()
    previous_recorded = None
    for event in events:
        check('approval-event', event)
        if event['id'] in ids:
            raise CheckError('Duplicate event ID')
        ids.add(event['id'])
        recorded = _dt(event['recorded_at'])
        if previous_recorded and recorded < previous_recorded:
            raise CheckError('Recording times run backwards')
        previous_recorded = recorded
        key = event['request_id']
        prior = states.get(key)
        if event['type'] == 'requested':
            if prior:
                raise CheckError('Duplicate request ID; requests cannot be replaced')
            request = event['request']
            for existing in states.values():
                earlier = existing['request']['artifact']
                artifact = request['artifact']
                if (earlier['id'], earlier['version']) == (artifact['id'], artifact['version']):
                    if any(earlier.get(field) != artifact.get(field) for field in ('path', 'sha256', 'owner_module')):
                        raise CheckError('Artifact version already identifies different content or path')
            if (key != request['id'] or event['actor'] != request['requested_by']
                    or event['occurred_at'] != request['requested_at']):
                raise CheckError('Initial event does not match request')
        else:
            if not prior:
                raise CheckError('Decision without request')
            request = prior['request']
            last = prior['event']
            if event['previous_event_id'] != last['id']:
                raise CheckError('Stale or invalid previous_event_id')
            if event['type'] not in TRANSITIONS.get(last['type'], ()):
                raise CheckError('Invalid transition; create a new request after a terminal decision')
            if _dt(event['occurred_at']) < _dt(last['occurred_at']):
                raise CheckError('Decision times run backwards')
        actual = {field: event[field] for field in SUBJECT_FIELDS if field in event}
        if actual != subject(request):
            raise CheckError('Event changes the requested artifact, action, target or budget')
        if event['type'] == 'approved':
            _approved_gates(request, event)
        states[key] = {'request': request, 'event': event}
    return states


def read_events(log, max_bytes=None):
    path = Path(log)
    if path.is_symlink():
        raise CheckError('Audit log must not be a symlink')
    if not path.exists():
        return []
    with path.open('rb') as stream:
        data = stream.read() if max_bytes is None else stream.read(max_bytes + 1)
    if max_bytes is not None and len(data) > max_bytes:
        raise CheckError('Audit log exceeds read limit')
    if data and not data.endswith(b'\n'):
        raise CheckError('Incomplete audit log; do not overwrite or silently repair it')
    events = []
    previous, chained = GENESIS, False
    for number, line in enumerate(data.split(b'\n')[:-1], 1):
        try:
            event = parse_json(line.decode('utf-8'))
        except (ValueError, CheckError) as exc:
            raise CheckError(f'Invalid audit line {number}: {exc}') from exc
        # Once the chain starts (v0.2.6+), every later line must link to the exact previous bytes.
        if isinstance(event, dict) and 'prev_hash' in event:
            if event['prev_hash'] != previous:
                raise CheckError(f'Hash chain broken at line {number}: earlier records were changed or removed')
            chained = True
        elif chained:
            raise CheckError(f'Unchained record after chained records at line {number}')
        previous = hashlib.sha256(line + b'\n').hexdigest()
        events.append(event)
    replay(events)
    return events


def chain_head(log):
    """Hash of the last record; store it outside the suite to detect later truncation or rewriting."""
    path = Path(log)
    data = path.read_bytes() if path.exists() else b''
    lines = data.split(b'\n')[:-1]
    return {'events': len(lines), 'head': hashlib.sha256(lines[-1] + b'\n').hexdigest() if lines else GENESIS}


def verify_checkpoint(log, events, head):
    """A stored checkpoint must still be a record in the log (append-only, nothing rewritten)."""
    if (type(events) is not int or events < 0 or not isinstance(head, str) or len(head) != 64
            or any(char not in '0123456789abcdef' for char in head) or (events == 0 and head != GENESIS)):
        raise CheckError('Invalid checkpoint; expected a non-negative count and SHA-256 head')
    path = Path(log)
    lines = path.read_bytes().split(b'\n')[:-1] if path.exists() else []
    if len(lines) < events or (events and hashlib.sha256(lines[events - 1] + b'\n').hexdigest() != head):
        raise CheckError('Log no longer contains the checkpoint: records were removed or rewritten')
    return {'checkpoint': 'pass', 'events_now': len(lines)}


@contextmanager
def _writer(log):
    path = Path(log).absolute()
    lock = path.with_name(path.name + '.lock')
    # Exclusive sidecar serializes cooperating writers on Unix and Windows. No stale-lock takeover.
    try:
        descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise CheckError('Audit log is locked; retry later, do not delete an active lock')
    try:
        os.close(descriptor)
        if path.is_symlink():
            raise CheckError('Audit log must not be a symlink')
        yield path
    finally:
        lock.unlink()


def _append(path, events, event, key=None):
    event = dict(event, prev_hash=chain_head(path)['head'])
    if key is not None:
        event['signature'] = sign(event, key)
    replay(events + [event])
    data = (json.dumps(event, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n').encode('utf-8')
    descriptor = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        offset = 0
        while offset < len(data):
            count = os.write(descriptor, data[offset:])
            if not count:
                raise OSError('Incomplete audit write')
            offset += count
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return event


def record_request(log, request, root, now=None):
    check('approval-request', request)
    # Capture a detached snapshot rather than retaining a mutable caller-owned object.
    request = parse_json(json.dumps(request, allow_nan=False))
    with _writer(log) as path:
        events = read_events(path)
        verify_file(root, request)
        event = {'id': 'evt-' + str(uuid.uuid4()), 'request_id': request['id'], 'type': 'requested',
                 'actor': request['requested_by'], 'occurred_at': request['requested_at'],
                 'recorded_at': _timestamp(now), **subject(request), 'reason': request['summary'],
                 'request': request}
        return _append(path, events, event)


def record_decision(log, request_id, decision, actor, occurred_at, evidence_ref, reason,
                    previous_event_id, root, actor_role=None, now=None, key=None):
    """key: bytes from load_key(). Unsigned decisions are recorded but never accepted for execution."""
    if decision not in DECISIONS:
        raise CheckError('Unknown human decision')
    with _writer(log) as path:
        events = read_events(path)
        state = replay(events).get(request_id)
        if state is None:
            raise CheckError('Unknown request ID')
        request = state['request']
        event = {'id': 'evt-' + str(uuid.uuid4()), 'request_id': request_id, 'type': decision,
                 'actor': actor, 'occurred_at': occurred_at, 'recorded_at': _timestamp(now),
                 **subject(request), 'reason': reason, 'evidence_ref': evidence_ref,
                 'previous_event_id': previous_event_id}
        if actor_role is not None:
            event['actor_role'] = actor_role
        # Read-only hash check is repeated immediately before recording approval.
        if decision == 'approved':
            verify_file(root, request)
        return _append(path, events, event, key)


def summarize(log, now=None, max_bytes=None):
    """Read-only projection for viewers; ignores no later revocation."""
    at = _dt(_timestamp(now))
    result = []
    for request_id, state in replay(read_events(log, max_bytes=max_bytes)).items():
        request, event = state['request'], state['event']
        status = 'pending' if event['type'] == 'requested' else event['type']
        if status in ('pending', 'approved') and 'expires_at' in request and _dt(request['expires_at']) <= at:
            status = 'expired'
        row = {'request_id': request_id, 'title': request['title'],
               'module': request['artifact']['owner_module'], 'path': request['artifact']['path'],
               **subject(request), 'status': status, 'event_type': event['type'], 'event_id': event['id'],
               'actor': event['actor'], 'occurred_at': event['occurred_at'],
               'recorded_at': event['recorded_at'], 'reason': event['reason']}
        if 'actor_role' in event:
            row['actor_role'] = event['actor_role']
        row['signed'] = 'signature' in event
        if status == 'approved':
            row['action_approval_candidate'] = action_approval(request, event)
        result.append(row)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    request = sub.add_parser('request')
    request.add_argument('--request', type=Path, required=True)
    request.add_argument('--root', type=Path, required=True)
    decide = sub.add_parser('decide')
    decide.add_argument('--decision', type=Path, required=True,
                        help='Human decision captured by a trusted harness; never inferred from model output')
    decide.add_argument('--root', type=Path, required=True)
    decide.add_argument('--unsigned', action='store_true',
                        help='Record without signature (documentation only; executors reject it)')
    sub.add_parser('status')
    check_parser = sub.add_parser('check')
    check_parser.add_argument('--expect', help='Checkpoint EVENTS:HEAD from an earlier "checkpoint" run')
    sub.add_parser('checkpoint')
    generate = sub.add_parser('keygen', help='Create a signing key outside the suite, for the approving harness only')
    generate.add_argument('--out', type=Path, required=True)
    for name, command in sub.choices.items():
        if name != 'keygen':
            command.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'request':
            result = record_request(args.log, parse_json(args.request.read_text(encoding='utf-8')), args.root)
        elif args.command == 'decide':
            data = parse_json(args.decision.read_text(encoding='utf-8'))
            if not isinstance(data, dict) or set(data) - {'request_id', 'decision', 'actor', 'actor_role',
                    'occurred_at', 'evidence_ref', 'reason', 'previous_event_id'}:
                raise CheckError('Invalid decision input fields')
            key = None if args.unsigned else load_key(root=args.root)
            result = record_decision(args.log, root=args.root, key=key, **data)
        elif args.command == 'status':
            result = summarize(args.log)
        elif args.command == 'keygen':
            result = keygen(args.out)
        elif args.command == 'checkpoint':
            read_events(args.log)
            result = chain_head(args.log)
        else:
            result = {'events': len(read_events(args.log)), 'structural_check': 'pass'}
            if args.expect:
                count, _, head = args.expect.partition(':')
                result.update(verify_checkpoint(args.log, int(count), head))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (CheckError, OSError, ValueError, TypeError) as exc:
        print('APPROVAL_AUDIT_BLOCKED:', str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
