"""Spreadsheet formula injection guard for CSV files that people may open in Excel, Calc or Sheets."""

# Leading characters spreadsheet programs evaluate. '+'/'-' followed by a digit or space ("-20 %", "- Punkt")
# are ordinary text or numbers; '+cmd|...' or '-HYPERLINK(...)' are not.
FORMULA_START = ('=', '@', '\t', '\r')


def formula_like(value):
    if not isinstance(value, str) or not value:
        return False
    if value.startswith(FORMULA_START):
        return True
    return value[0] in '+-' and len(value) > 1 and not (value[1].isdigit() or value[1] in ' .,')


def neutralize(value):
    """Prefix risky text cells with an apostrophe so they are shown as text, not executed."""
    return "'" + value if formula_like(value) else value
