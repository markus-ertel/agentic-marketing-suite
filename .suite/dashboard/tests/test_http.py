import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.app import DashboardServer
from server.files import MODULES
from server.sessions import Sessions


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        for module in (*MODULES, '.suite'):
            (cls.root/module).mkdir()
        cls.config = {'server':{'host':'127.0.0.1','port':0},'suite':{'root':str(cls.root),'refresh_interval_ms':500},'viewer':{'max_inline_file_mb':1},'agents':{'profiles':[]}}
        cls.server = DashboardServer(cls.config)
        cls.server.sessions = Sessions(cls.config['agents'], cls.server.files)
        cls.thread = threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:'+str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def get(self, path, headers=None):
        return urlopen(Request(self.base+path, headers=headers or {}), timeout=5)

    def test_tree_and_change_delete(self):
        self.assertEqual(len(json.load(self.get('/api/modules'))),9)
        path = self.root/'marketing'/'temporary.md'
        path.write_text('# Erste Version')
        first = json.load(self.get('/api/file?path=marketing/temporary.md'))
        self.assertIn('Erste Version',first['html'])
        path.write_text('# Zweite Version')
        second = json.load(self.get('/api/file?path=marketing/temporary.md'))
        self.assertNotEqual(first['revision'], second['revision'])
        self.assertIn('Zweite Version',second['html'])
        path.unlink()
        with self.assertRaises(HTTPError) as error:
            self.get('/api/file?path=marketing/temporary.md')
        self.assertEqual(error.exception.code,404)

    def test_media_range_and_html_isolation(self):
        (self.root/'movie.mp4').write_bytes(b'0123456789')
        response = self.get('/api/raw?path=movie.mp4', {'Range':'bytes=2-5'})
        self.assertEqual(response.status,206)
        self.assertEqual(response.read(),b'2345')
        self.assertEqual(response.headers['Content-Range'],'bytes 2-5/10')
        self.assertEqual(self.get('/api/raw?path=movie.mp4', {'Range':'bytes=-3'}).read(), b'789')
        with self.assertRaises(HTTPError) as error:
            self.get('/api/raw?path=movie.mp4', {'Range':'bytes=100-200'})
        self.assertEqual(error.exception.code,416)
        folder = self.root/'site'
        folder.mkdir(exist_ok=True)
        (folder/'page.html').write_text('<h1>Hallo</h1><link rel="stylesheet" href="style.css">')
        (folder/'style.css').write_text('h1 {color: green}')
        response = self.get('/view/site/page.html')
        self.assertIn('sandbox;',response.headers['Content-Security-Policy'])
        self.assertIn(b'Hallo',response.read())
        self.assertIn(b'green',self.get('/view/site/style.css').read())

    def test_root_containment_and_read_only_routes(self):
        with self.assertRaises(HTTPError) as error:
            self.get('/api/file?path='+quote('../outside'))
        self.assertEqual(error.exception.code,403)
        request = Request(self.base+'/api/chat',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://another.invalid'})
        with self.assertRaises(HTTPError) as error:
            urlopen(request,timeout=5)
        self.assertEqual(error.exception.code,403)
        self.assertEqual(json.load(self.get('/api/agents')),[])
        self.assertEqual(json.load(self.get('/api/sessions')),[])
        self.assertIn(b'Dein Arbeitsraum.',self.get('/').read())

    def test_event_replay_and_parallel_sessions(self):
        from server.sessions import Session
        profile = {'id':'test','label':'Test','adapter':'pi-rpc'}
        sessions = [Session(profile,'marketing'),Session(profile,'creative')]
        for session in sessions:
            # No process: this is a controlled protocol replay test.
            session.adapter = type('Idle',(),{'capabilities':{},'close':lambda self:None})()
            self.server.sessions.items[session.id] = session
        sessions[0].emit({'type':'agent.status','status':'arbeitet'})
        sessions[1].emit({'type':'agent.status','status':'bereit'})
        self.assertEqual(len(json.load(self.get('/api/sessions'))),2)
        response = self.get('/api/events?session='+sessions[0].id)
        self.assertEqual(response.readline().strip(),b'id: 1')
        event = json.loads(response.readline()[len(b'data: '):])
        self.assertEqual(event['status'],'arbeitet')
        response.close()
        # A browser reload/reconnect gets the same observed working event, never synthetic success.
        response = self.get('/api/events?session='+sessions[0].id)
        response.readline()
        self.assertEqual(json.loads(response.readline()[6:])['status'],'arbeitet')
        response.close()
        for session in sessions:
            self.server.sessions.items.pop(session.id)
