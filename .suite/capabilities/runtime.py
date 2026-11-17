"""Shared local contracts/gates for optional adapters; no implicit human authority or network."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from validate_records import check
from approval_audit import CheckError, load_key, parse_json, read_events, replay, summarize, verify_file, verify_signature


class CapabilityError(ValueError):
    pass


def load_json(path):
    return parse_json(Path(path).read_text(encoding='utf-8'))


def snapshot_json(path):
    data = Path(path).read_bytes()
    if len(data) > 1024 * 1024:
        raise CapabilityError('Plan exceeds 1 MiB')
    return parse_json(data.decode('utf-8')), hashlib.sha256(data).hexdigest()


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            value.update(block)
    return value.hexdigest()


def relative_file(root, relative):
    if (not isinstance(relative, str) or not relative or '\\' in relative
            or Path(relative).is_absolute() or '..' in relative.split('/')):
        raise CapabilityError('A relative artifact path is required')
    root = Path(root).resolve(strict=True)
    path = (root / relative).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError:
        raise CapabilityError('Artifact escapes its root')
    if not path.is_file():
        raise CapabilityError('Artifact is not a regular file')
    return path


def write_new(path, data):
    """Explicit local outputs never silently overwrite existing user files."""
    path = Path(path)
    descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def write_json(path, value):
    write_new(path, (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode())


def clean_string(value, name):
    if not isinstance(value, str) or not value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise CapabilityError(name + ': invalid string')
    return value


def require_approval(log, request_id, root, plan_path, action, target, expected_sha256, key_path=None):
    """An execution preflight in the adapter, never in the dashboard.

    The harness additionally authenticates the actual person and authority, validates
    legal basis and tool rights, and prevents racing external actions/revocations.
    """
    states = replay(read_events(log))
    state = states.get(request_id)
    if state is None:
        raise CapabilityError('No approval request')
    request, event = state['request'], state['event']
    row = next(row for row in summarize(log) if row['request_id'] == request_id)
    if row['status'] != 'approved' or event['type'] != 'approved':
        raise CapabilityError('Approval is absent, revoked or expired')
    # Only a decision signed by the approving harness counts; an agent without the key cannot forge one.
    verify_signature(event, load_key(path=key_path, root=root))
    actual = Path(plan_path).resolve(strict=True)
    expected = relative_file(root, request['artifact']['path'])
    if actual != expected or request['action'] != action or request['target'] != target:
        raise CapabilityError('Approval covers a different plan, action or target')
    if request['artifact']['sha256'] != expected_sha256:
        raise CapabilityError('Loaded plan is not the approved file snapshot')
    verify_file(root, request)
    return {'request_id': request_id, 'approval_event_id': event['id'],
            'approval_log': str(Path(log).resolve(strict=True)),
            'artifact_sha256': request['artifact']['sha256'], 'action': action, 'target': target}


def bound_execution_log(approvals, execution_log):
    """Executions live next to their approval log so a second log cannot hide a repeat."""
    expected = Path(approvals).parent.resolve(strict=True) / 'executions.jsonl'
    if Path(execution_log).parent.resolve(strict=True) / Path(execution_log).name != expected:
        raise CapabilityError('Execution log must be executions.jsonl next to the approval log')
    return expected


@contextmanager
def execution_lock(log):
    path = Path(log).absolute()
    lock = path.with_name(path.name + '.lock')
    try:
        descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise CapabilityError('Execution log is locked; no automatic takeover')
    try:
        os.close(descriptor)
        if path.is_symlink():
            raise CapabilityError('Execution log must not be a symlink')
        yield path
    finally:
        lock.unlink()


def read_execution_log(path):
    path = Path(path)
    if not path.exists():
        return []
    data = path.read_bytes()
    if data and not data.endswith(b'\n'):
        raise CapabilityError('Incomplete execution log; investigate instead of retrying')
    events = [parse_json(line) for line in data.decode().split('\n')[:-1]]
    for event in events:
        check('capability-execution', event)
    return events


def append_execution(path, event):
    event = dict(event, id='exec-' + str(uuid.uuid4()), recorded_at=datetime.now(timezone.utc).isoformat())
    check('capability-execution', event)
    data = (json.dumps(event, ensure_ascii=False, allow_nan=False) + '\n').encode()
    descriptor = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(descriptor, 'ab') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return event


def run_once(log, key, capability, approval, operation):
    clean_string(key, 'idempotency_key')
    approval = dict(approval)
    source = approval.pop('approval_log', None)
    if approval.get('approval_event_id'):
        if source is None:
            raise CapabilityError('Approval journal required to select canonical execution log')
        bound_execution_log(source, log)
    with execution_lock(log) as path:
        events = read_execution_log(path)
        prior = [event for event in events if event['key'] == key]
        identity = {'capability': capability, **approval}
        approval_event = approval.get('approval_event_id')
        if approval_event and any(event.get('approval_event_id') == approval_event and event['key'] != key for event in events):
            # One human approval authorizes one execution; a retry needs a new approval, not a new key.
            raise CapabilityError('Approval was already used for an execution; request a new approval')
        if prior:
            if any(prior[0].get(field) != value for field, value in identity.items()):
                raise CapabilityError('Idempotency key was used for a different operation')
            # A crashed process leaves started; never repeat an ambiguous external action.
            return {**prior[-1], 'replayed': True,
                    'status': 'uncertain' if prior[-1]['status'] == 'started' else prior[-1]['status']}
        append_execution(path, {'key': key, **identity, 'status': 'started'})
        try:
            outcome = operation()
            if outcome.get('status') not in ('accepted', 'confirmed', 'failed', 'uncertain'):
                raise CapabilityError('Invalid transport outcome')
        except Exception as error:
            # Provider errors may contain credentials, message bodies or account data.
            outcome = {'status': 'uncertain', 'error_type': type(error).__name__, 'notice': 'Transport interrupted; investigate before any new attempt'}
        return append_execution(path, {'key': key, **identity, **outcome})
