"""Read the real suite tree; never write domain files."""
import csv
import html
import io
import json
import mimetypes
import re
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

MODULES = ('marketing', 'pr', 'social-media', 'website', 'advertising', 'creative', 'noCRM', 'analytics')
SKIP = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.DS_Store'}
TEXT = {'.txt', '.md', '.markdown', '.json', '.jsonl', '.csv', '.tsv', '.log', '.py', '.js', '.ts', '.tsx', '.jsx', '.css', '.html', '.htm', '.xml', '.svg', '.yaml', '.yml', '.toml', '.sh', '.sql', '.ini', '.cfg', '.rst'}


class Files:
    def __init__(self, root, max_mb=25):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError('suite.root muss ein Verzeichnis sein.')
        self.limit = int(max_mb * 1024 * 1024)

    def resolve(self, relative=''):
        path = (self.root / relative).resolve()
        try:
            path.relative_to(self.root)
        except ValueError:
            raise PermissionError('Pfad liegt außerhalb der Suite.')
        return path

    def modules(self):
        names = list(MODULES)
        for entry in sorted(self.root.iterdir(), key=lambda p: p.name.casefold()):
            if entry.name.startswith('.') or entry.name in names or not entry.is_dir():
                continue
            try:
                self.resolve(entry.name)
            except PermissionError:
                continue
            if (entry / 'AGENT.md').is_file():
                names.append(entry.name)
        return [{'name': name, 'path': name} for name in (*names, '.suite') if (self.root / name).is_dir()]

    def tree(self, relative='', hidden=False, query=''):
        parent = self.resolve(relative)
        if not parent.is_dir():
            raise FileNotFoundError('Verzeichnis nicht mehr vorhanden.')
        result = []
        def visit(directory):
            try:
                entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold()))
            except OSError:
                return
            for entry in entries:
                if entry.name in SKIP or (entry.name.startswith('.') and entry.name != '.suite' and not hidden):
                    continue
                # Symlinked directories are not traversed, preventing loops.
                try:
                    self.resolve(str(entry.relative_to(self.root)))
                    stat = entry.stat()
                except (OSError, PermissionError, ValueError):
                    continue
                rel = entry.relative_to(self.root).as_posix()
                directory_entry = entry.is_dir()
                if not query or query.casefold() in rel.casefold():
                    result.append({'name': entry.name, 'path': rel, 'directory': directory_entry,
                                   'size': stat.st_size, 'revision': f'{stat.st_mtime_ns}:{stat.st_size}'})
                if query and directory_entry and not entry.is_symlink():
                    visit(entry)
        visit(parent)
        return result

    def metadata(self, relative):
        path = self.resolve(relative)
        if not path.is_file():
            raise FileNotFoundError('Datei nicht mehr vorhanden.')
        stat = path.stat()
        suffix = path.suffix.lower()
        mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        kind = 'unsupported'
        if suffix in TEXT or mime.startswith('text/') or suffix == '':
            kind = 'text'
        if suffix in ('.md', '.markdown'):
            kind = 'markdown'
        elif suffix in ('.json', '.jsonl', '.csv', '.tsv'):
            kind = suffix[1:]
        elif mime.startswith('image/'):
            kind = 'image'
        elif mime == 'application/pdf':
            kind = 'pdf'
        elif suffix in ('.html', '.htm'):
            kind = 'html'
        elif mime.startswith(('audio/', 'video/')):
            kind = mime.split('/')[0]
        return {'path': path.relative_to(self.root).as_posix(), 'name': path.name, 'kind': kind,
                'mime': mime, 'size': stat.st_size, 'modified': stat.st_mtime,
                'revision': f'{stat.st_mtime_ns}:{stat.st_size}', 'inline': stat.st_size <= self.limit,
                'textual': suffix in TEXT or mime.startswith('text/') or suffix == ''}

    def preview(self, relative):
        meta = self.metadata(relative)
        if not meta['inline'] or not meta['textual']:
            return meta
        path = self.resolve(relative)
        # Bounded read also covers a file growing between stat and read.
        with path.open('rb') as stream:
            data = stream.read(self.limit + 1)
        if len(data) > self.limit:
            meta['inline'] = False
            return meta
        if b'\x00' in data:
            meta['kind'] = 'unsupported'
            meta['textual'] = False
            return meta
        text = data.decode('utf-8-sig', errors='replace')
        meta['source'] = text
        if meta['kind'] == 'markdown':
            try:
                from markdown_it import MarkdownIt
                renderer = MarkdownIt('commonmark', {'html': False}).enable('table')
                default = renderer.renderer.rules.get('link_open')
                def local_url(value, image=False):
                    url = urlsplit(value)
                    if url.scheme or url.netloc or value.startswith('#'):
                        return value
                    target = (self.root / unquote(url.path).lstrip('/')) if value.startswith('/') else (path.parent / unquote(url.path))
                    try:
                        relative = target.resolve().relative_to(self.root).as_posix()
                    except ValueError:
                        return '#'
                    return ('/api/raw?path=' if image else '/?file=') + quote(relative, safe='') + (('#' + url.fragment) if url.fragment else '')
                def link_open(tokens, idx, options, env):
                    token = tokens[idx]
                    href = token.attrGet('href') or ''
                    token.attrSet('href', local_url(href))
                    return default(tokens, idx, options, env) if default else renderer.renderer.renderToken(tokens, idx, options, env)
                def image_rule(tokens, idx, options, env):
                    token = tokens[idx]
                    src = token.attrGet('src') or ''
                    src = local_url(src, image=True)
                    return '<img loading="lazy" alt="' + html.escape(token.content, quote=True) + '" src="' + html.escape(src, quote=True) + '">'
                heading_ids = {}
                def heading_open(tokens, idx, options, env):
                    title = tokens[idx + 1].content
                    slug = re.sub(r'[^\w\s-]', '', title.lower()).strip().replace(' ', '-')
                    number = heading_ids.get(slug, 0)
                    heading_ids[slug] = number + 1
                    tokens[idx].attrSet('id', slug + (f'-{number}' if number else ''))
                    return renderer.renderer.renderToken(tokens, idx, options, env)
                renderer.renderer.rules['link_open'] = link_open
                renderer.renderer.rules['image'] = image_rule
                renderer.renderer.rules['heading_open'] = heading_open
                meta['html'] = renderer.render(text)
            except ImportError:
                meta['notice'] = 'Markdown-Vorschau benötigt markdown-it-py; Quelltext wird angezeigt.'
        elif meta['kind'] in ('csv', 'tsv'):
            reader = csv.reader(io.StringIO(text), delimiter='\t' if meta['kind'] == 'tsv' else ',')
            rows = []
            for row in reader:
                rows.append(row[:100])
                if len(rows) >= 501:
                    break
            meta['rows'] = rows[:500]
            meta['truncated'] = len(rows) > 500
        elif meta['kind'] == 'json':
            try:
                meta['formatted'] = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
            except ValueError:
                meta['notice'] = 'Ungültiges JSON – Rohtextansicht.'
        return meta
