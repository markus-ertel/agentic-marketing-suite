"""The draft schema must allow every field preflight.py reads; otherwise valid drafts fail strict validation."""
import json
from pathlib import Path
import re
import unittest

NOCRM = Path(__file__).resolve().parents[1]


class DraftSchemaTests(unittest.TestCase):
    def test_schema_lists_every_draft_field_preflight_reads(self):
        schema = json.loads((NOCRM / 'schemas/draft.schema.json').read_text(encoding='utf-8'))
        source = (NOCRM / 'tools/preflight.py').read_text(encoding='utf-8')
        used = set(re.findall(r"draft\.get\('([a-z0-9_]+)'", source))
        self.assertTrue(used)
        self.assertEqual(sorted(used - set(schema['properties'])), [])
        self.assertIs(schema['additionalProperties'], False)


if __name__ == '__main__':
    unittest.main()
