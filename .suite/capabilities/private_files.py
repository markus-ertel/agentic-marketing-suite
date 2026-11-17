"""One deny list for files that must never be shown, attached or deployed. Standard library only."""
from pathlib import PurePosixPath

PRIVATE_NAMES = {'.git', '.hg', '.svn', '.aws', '.ssh', '.gnupg', '.codex', '.config',
                 '.netrc', '.npmrc', '.pypirc', '.pgpass', '.git-credentials', '.mcp.json',
                 'credentials', 'credentials.json', 'token.json', 'secrets', 'secrets.json',
                 'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519',
                 'approvals.jsonl', 'executions.jsonl', 'delivery-events.jsonl'}
PRIVATE_PREFIXES = ('.env', 'secrets.', 'client_secret', 'service-account', 'service_account')
PRIVATE_SUFFIXES = {'.pem', '.key', '.p12', '.pfx', '.keystore', '.jks'}
# Never part of a public website or a mail attachment, but fine to read locally.
EXPORT_SUFFIXES = {'.sql', '.sqlite', '.sqlite3', '.db', '.bak', '.dump'}


def is_private(name, export=False):
    """True if a single path component names credentials, keys or private logs."""
    folded = name.casefold()
    suffix = PurePosixPath(folded).suffix
    return (folded in PRIVATE_NAMES or folded.startswith(PRIVATE_PREFIXES) or suffix in PRIVATE_SUFFIXES
            or (export and suffix in EXPORT_SUFFIXES))
