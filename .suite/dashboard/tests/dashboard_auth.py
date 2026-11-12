"""Test helper: let urllib send the per-start dashboard token, as the browser cookie would."""
from urllib.request import build_opener, install_opener


def authenticate(server):
    opener = build_opener()
    opener.addheaders = [('X-Dashboard-Token', server.token)]
    install_opener(opener)
