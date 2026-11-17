"""Fail-closed POSIX execution boundary, provisioned by an administrator.

No command-line flag or agent-controlled environment selects this policy. The
executor must run from a protected installation under a different OS identity.
This is a prerequisite check, not a privilege-changing or authentication service.
"""
import json
import os
from pathlib import Path
import stat
import sys

POLICY = Path('/private/etc/agentic-marketing-suite/executor.json' if sys.platform == 'darwin'
              else '/etc/agentic-marketing-suite/executor.json')


def protected(path, owners, directory=False):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid not in owners or info.st_mode & 0o022:
            raise ValueError('Execution boundary requires protected paths without symlinks')
    if directory and not path.is_dir():
        raise ValueError('Expected protected directory')
    if not directory and not path.is_file():
        raise ValueError('Expected protected file')
    return path


def require_execution_authority(approval_log, execution_log, capability):
    if os.name != 'posix':
        raise ValueError('External execution requires a separately provisioned POSIX executor')
    protected(POLICY, {0})
    config = json.loads(POLICY.read_text(encoding='utf-8'))
    uid, agent_uid = config['executor_uid'], config['agent_uid']
    if (type(uid) is not int or type(agent_uid) is not int or uid <= 0 or agent_uid <= 0
            or uid == agent_uid or os.getuid() != uid or os.geteuid() != uid):
        raise ValueError('Run external actions as the dedicated executor, never as the agent')
    if not Path(config['code_root']).is_absolute():
        raise ValueError('The protected installation path must be absolute')
    code_root = protected(config['code_root'], {0}, directory=True)
    protected(Path(__file__), {0}).relative_to(code_root)
    from runtime import __file__ as runtime_file
    protected(runtime_file, {0}).relative_to(code_root)
    # The admin registers individual approval journals, capabilities and the canonical journal.
    source = Path(approval_log).absolute()
    matches = [row for row in config['approvals'] if isinstance(row, dict)
               and isinstance(row.get('capabilities'), list) and row.get('path') == str(source)
               and capability in row['capabilities']]
    if len(matches) != 1:
        raise ValueError('Approval journal or capability is not registered by the operator')
    protected(source, {0, uid})
    journal = source.with_name('executions.jsonl')
    if Path(execution_log).absolute() != journal:
        raise ValueError('The registered canonical execution journal is required')
    protected(journal.parent, {0, uid}, directory=True)
    if journal.exists() or journal.is_symlink():
        protected(journal, {0, uid})
    # A caller-controlled environment must not select an attacker's signing key.
    if not Path(config['approval_key_file']).is_absolute():
        raise ValueError('The operator signing key path must be absolute')
    key_path = protected(config['approval_key_file'], {0, uid})
    if key_path.stat().st_mode & 0o077:
        raise ValueError('Approval key must only be accessible to its owner')
    return config
