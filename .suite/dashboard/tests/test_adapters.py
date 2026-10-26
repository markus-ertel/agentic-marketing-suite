from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.adapters.pi_rpc import PiRPC
from server.adapters.codex_appserver import CodexAppServer
from server.sessions import Session, Sessions
from server.files import Files


class AdapterTests(unittest.TestCase):
    def make(self, cls):
        events = []
        adapter = cls({'command':['missing'], 'id':'test'}, Path('/tmp'), events.append)
        adapter.failed = False
        return adapter, events

    def test_pi_acceptance_and_agent_end_are_not_completion(self):
        adapter, events = self.make(PiRPC)
        adapter.request = lambda record: {'disposition':'started'}
        adapter.send('Hallo')
        adapter.handle({'type':'agent_end'})
        self.assertEqual(events, [])
        adapter.handle({'type':'agent_start'})
        adapter.handle({'type':'message_update','assistantMessageEvent':{'type':'text_delta','delta':'Hallo'}})
        adapter.handle({'type':'agent_settled'})
        self.assertEqual(events[0]['status'], 'arbeitet')
        self.assertEqual(events[-1]['status'], 'abgeschlossen')
        self.assertEqual(events[1]['text'], 'Hallo')

    def test_pi_failed_message_stays_failed_when_settled(self):
        adapter, events = self.make(PiRPC)
        adapter.handle({'type':'message_end','message':{'role':'assistant','stopReason':'error','errorMessage':'Auth fehlt'}})
        adapter.handle({'type':'agent_settled'})
        self.assertEqual(events[-1]['status'], 'Fehler')

    def test_codex_completion_failure_and_approval_are_distinct(self):
        adapter, events = self.make(CodexAppServer)
        adapter.handle({'method':'turn/started','params':{}})
        adapter.handle({'method':'item/agentMessage/delta','params':{'delta':'Hi','itemId':'one'}})
        adapter.handle({'id':42,'method':'item/fileChange/requestApproval','params':{'reason':'Datei schreiben'}})
        self.assertEqual(events[-2]['status'], 'wartet auf Eingabe')
        self.assertEqual(events[-1]['rpc_id'],42)
        adapter.handle({'method':'turn/completed','params':{'turn':{'status':'failed','error':{'message':'failure'}}}})
        self.assertEqual(events[-1]['status'],'Fehler')
        self.assertFalse(any(e.get('status')=='abgeschlossen' for e in events))

    def test_multiple_sessions_replay_status_and_buffer_gap(self):
        one = Session({'id':'pi','label':'Pi','adapter':'pi-rpc'},'marketing')
        two = Session({'id':'codex','label':'Codex','adapter':'codex-appserver'},'creative')
        one.emit({'type':'agent.status','status':'arbeitet'})
        two.emit({'type':'agent.status','status':'bereit'})
        self.assertEqual(one.snapshot()['status'],'arbeitet')
        self.assertEqual(two.snapshot()['status'],'bereit')
        self.assertNotEqual(one.id,two.id)
        self.assertEqual(one.events_after(0)[0]['status'],'arbeitet')
        for i in range(2001):
            one.emit({'type':'agent.message.delta','text':'x'})
        self.assertEqual(one.events_after(0)[0]['type'],'stream.gap')

    def test_missing_cli_and_unknown_session(self):
        root = Path(__file__).resolve().parents[3]
        manager = Sessions({'profiles':[{'id':'none','label':'None','adapter':'pi-rpc','command':['definitely-absent-cli-993']}]}, Files(root))
        self.assertFalse(manager.profiles()[0]['available'])
        with self.assertRaises(ValueError):
            manager.connect('none','')
        with self.assertRaises(ValueError):
            manager.get('unknown')


if __name__ == '__main__':
    unittest.main()
