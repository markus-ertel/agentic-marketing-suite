"""Provider-specific transports. No model or domain decisions."""
from .pi_rpc import PiRPC
from .codex_appserver import CodexAppServer

ADAPTERS = {'pi-rpc': PiRPC, 'codex-appserver': CodexAppServer}
