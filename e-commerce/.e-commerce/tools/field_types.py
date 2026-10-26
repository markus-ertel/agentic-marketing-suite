"""Bounded type checks for local preflights, not a full JSON Schema engine."""
import json
from pathlib import Path


def load_schema(name):
    return json.loads((Path(__file__).resolve().parents[1] / 'formate' / name).read_text(encoding='utf-8'))


def type_errors(value, schema, path='record'):
    expected = schema.get('type')
    checks = {'object': lambda x: isinstance(x, dict), 'array': lambda x: isinstance(x, list),
              'string': lambda x: isinstance(x, str), 'boolean': lambda x: isinstance(x, bool),
              'integer': lambda x: isinstance(x, int) and not isinstance(x, bool)}
    if expected in checks and not checks[expected](value):
        return [f'{path}: {expected} erwartet']
    found = []
    if isinstance(value, dict):
        for key, field in schema.get('properties', {}).items():
            if key in value:
                found.extend(type_errors(value[key], field, f'{path}.{key}'))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(type_errors(item, schema.get('items', {}), f'{path}[{index}]'))
    return found
