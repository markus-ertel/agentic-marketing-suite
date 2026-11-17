"""Conservative spreadsheet formula guard for textual CSV cells."""
import re

# Preserve simple numbers, phone-like numbers and plain promotional labels only.
SAFE_SIGNED = re.compile(r"(?:[+-](?:[0-9]+(?:[ .,][0-9]+)*|[.,][0-9]+)(?:\s*%(?:\s+[A-Za-zÄÖÜäöüß]+)*)?|-[ ]+[A-Za-zÄÖÜäöüß]+(?:[ ]+[A-Za-zÄÖÜäöüß]+)*)\Z")


def formula_like(value):
    if not isinstance(value, str) or not value:
        return False
    if value[0] in '\t\r\n':
        return True
    probe = value.lstrip(' \t\r\n')
    if not probe:
        return False
    if probe[0] in '=@':
        return True
    return probe[0] in '+-' and SAFE_SIGNED.fullmatch(probe) is None


def neutralize(value):
    return "'" + value if formula_like(value) else value
