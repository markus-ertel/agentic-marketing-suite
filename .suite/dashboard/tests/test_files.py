import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.files import Files, MODULES
from server.app import load_config


class FileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.files = Files(self.root, 0.001)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        return target

    def test_dynamic_tree_hidden_search_and_modules(self):
        for module in (*MODULES, '.suite'):
            (self.root / module).mkdir()
        self.write('marketing/.marketing/method.md', '# Intern')
        self.assertEqual(len(self.files.modules()), 9)
        self.assertEqual(self.files.tree('marketing'), [])
        self.assertEqual(self.files.tree(hidden=True, query='method')[0]['path'], 'marketing/.marketing/method.md')
        self.write('marketing/new.md', '# Neu')
        self.assertEqual(self.files.tree('marketing')[0]['name'], 'new.md')
        self.assertIn('.suite', [e['name'] for e in self.files.tree()])

    def test_preview_and_external_change_delete(self):
        path = self.write('note.md', '# Titel\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```py\nprint(1)\n```')
        first = self.files.preview('note.md')
        self.assertIn('<table>', first['html'])
        self.assertIn('<pre><code', first['html'])
        path.write_text('changed')
        self.assertNotEqual(first['revision'], self.files.preview('note.md')['revision'])
        self.assertEqual(path.read_text(), 'changed')
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            self.files.preview('note.md')

    def test_formats_limits_and_no_mutation(self):
        fixtures = {'data.json':'{"a":1}', 'data.jsonl':'{"a":1}\n', 'data.csv':'A,B\n"a,b",c', 'page.html':'<h1>Hallo</h1>', 'note.txt':'Text', 'picture.svg':'<svg/>', 'sample.pdf':'%PDF-1.4', 'unknown.xyz':'binary'}
        expected = ['json', 'jsonl', 'csv', 'html', 'text', 'image', 'pdf', 'unsupported']
        for (name, content), kind in zip(fixtures.items(), expected):
            self.write(name, content)
            before = (self.root / name).read_bytes()
            meta = self.files.preview(name)
            self.assertEqual(meta['kind'], kind)
            self.assertEqual((self.root / name).read_bytes(), before)
        self.assertEqual(self.files.preview('data.csv')['rows'][1], ['a,b','c'])
        self.write('big.txt','x'*2000)
        self.assertFalse(self.files.preview('big.txt')['inline'])
        self.assertNotIn('source', self.files.preview('big.txt'))

    def test_containment_and_escaped_markdown(self):
        with self.assertRaises(PermissionError):
            self.files.resolve('../outside')
        (self.root / 'escape').symlink_to(self.root.parent)
        self.assertNotIn('escape', [e['name'] for e in self.files.tree()])
        self.write('bad.md','<script>alert(1)</script>\n\n[bad](javascript:alert(1))')
        self.assertNotIn('<script>', self.files.preview('bad.md')['html'])
        self.assertNotIn('href="javascript:', self.files.preview('bad.md')['html'])

    def test_relative_config_and_invalid_port(self):
        config = self.write('config.json', json.dumps({'suite':{'root':'.'},'server':{'port':0}}))
        self.assertEqual(load_config(config)['suite']['root'], str(self.root.resolve()))
        for port in [-1, 65536, True, '9000']:
            config.write_text(json.dumps({'suite':{'root':'.'},'server':{'port':port}}))
            with self.assertRaises(ValueError):
                load_config(config)

    def test_real_suite(self):
        root = Path(__file__).resolve().parents[3]
        files = Files(root)
        self.assertEqual(len(files.modules()), 9)
        self.assertIn('<table>', files.preview('README.md')['html'])

    def test_invalid_config_sections_and_markdown_paths(self):
        config = self.root / 'config.json'
        for value in ([], {'server': []}, {'suite': {'root': True}}, {'viewer': {'default_mode': 'edit'}}, {'agents': {'profiles': ['invalid']}}):
            if isinstance(value, dict):
                value.setdefault('suite', {'root': '.'})
            config.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                load_config(config)
        self.write('note.md', '# Titel\n\n[root](/README.md)\n\n[out](../../outside.md)')
        rendered = self.files.preview('note.md')['html']
        self.assertIn('id="titel"', rendered)
        self.assertIn('/?file=README.md', rendered)
        self.assertIn('href="#"', rendered)
