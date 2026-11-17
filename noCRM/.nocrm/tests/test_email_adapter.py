import importlib.util
import json
import os
from pathlib import Path
import smtplib
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('mail_adapter',ROOT/'noCRM/.nocrm/integrationen/email/adapter.py')
mail=importlib.util.module_from_spec(spec);spec.loader.exec_module(mail)


class SMTP:
    def __init__(self,*args,**kwargs):self.steps=[];self.context=kwargs.get('context');self.sent=[]
    def ehlo(self):self.steps.append('ehlo')
    def starttls(self,context):self.steps.append('tls');assert context.check_hostname
    def login(self,user,password):self.steps.append('login')
    def sendmail(self,sender,recipients,data):self.sent.append((sender,recipients,data));return {}
    def quit(self):pass
    def close(self):pass


class IMAP:
    message=b'From: visitor@example.invalid\r\nTo: owner@example.invalid\r\nSubject: Anfrage\r\nMessage-ID: <new@example.invalid>\r\nReferences: <old@example.invalid>\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nUntrusted incoming text.\r\n'
    def __init__(self,*args,**kwargs):self.commands=[];self.appended=[];assert kwargs['ssl_context'].check_hostname
    def login(self,*args):pass
    def logout(self):pass
    def select(self,mailbox,readonly=False):self.readonly=readonly;return ('OK',[])
    def response(self,name):return ('UIDVALIDITY',[b'7'])
    def uid(self,command,*args):
        self.commands.append((command,args))
        if command=='search':return ('OK',[b'12'])
        if args[-1]=='(RFC822.SIZE)':return ('OK',[b'1 (RFC822.SIZE 200)'])
        return ('OK',[(b'1 (BODY[] {200}',self.message),b')'])
    def append(self,*args):self.appended.append(args);return ('OK',[b'accepted'])


class MailAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.account={'id':'account-one','credential_ref':'MAIL_ONE','username':'owner','from':'owner@example.invalid','imap':{'host':'imap.example.invalid','port':993},'smtp':{'host':'smtp.example.invalid','port':587,'tls':'starttls'},'allowed_mailboxes':['INBOX'],'draft_mailbox':'Drafts','read_enabled':True}
        self.message={'to':['visitor@example.invalid'],'subject':'Individuelle Antwort','body':'Fiktiver Testentwurf.','purpose':'service','contact_id':'contact-demo','legal_basis_evidence_ref':'fixture:service-request'}
    def prepare(self,**kwargs):return mail.prepare(self.root,self.account,self.message,'draft.eml','plan.json',**kwargs)
    def test_frozen_message_reply_and_blind_recipients(self):
        self.message.update(bcc=['blind@example.invalid'],in_reply_to='<original@example.invalid>',references=['<original@example.invalid>'])
        value=self.prepare();data=mail.validate_plan(self.root,value)
        self.assertIn(b'In-Reply-To: <original@example.invalid>',data);self.assertNotIn(b'Bcc:',data)
        self.assertIn('blind@example.invalid',value['envelope_to'])
        (self.root/'draft.eml').write_bytes(data+b'changed')
        with self.assertRaises(mail.CapabilityError):mail.validate_plan(self.root,value)
    def test_header_injection_invalid_recipients_and_missing_consent_reference(self):
        for field,value in [('subject','Hi\r\nBcc: evil@example.invalid'),('to',['x@example.invalid\r\nBcc: evil@example.invalid']),('legal_basis_evidence_ref','')]:
            original=self.message[field];self.message[field]=value
            with self.subTest(field=field),self.assertRaises((ValueError,mail.CapabilityError)):self.prepare()
            self.assertFalse((self.root/'draft.eml').exists());self.message[field]=original
    def test_smtp_requires_tls_before_login_and_reports_acceptance_not_delivery(self):
        value=self.prepare();data=mail.validate_plan(self.root,value);client=SMTP()
        with patch.dict(os.environ,{'MAIL_ONE_PASSWORD':'fictional-secret'}):
            result=mail.execute_transport(value,data,smtp_starttls=lambda *a,**k:client,revalidate=lambda:None)
        self.assertEqual(result['status'],'accepted');self.assertNotIn('delivered',result)
        self.assertLess(client.steps.index('tls'),client.steps.index('login'));self.assertEqual(client.sent[0][2],data)
    def test_current_gate_is_rechecked_immediately_before_send(self):
        value=self.prepare();client=SMTP()
        def deny():raise mail.CapabilityError('revoked')
        with patch.dict(os.environ,{'MAIL_ONE_PASSWORD':'fictional-secret'}):
            with self.assertRaises(mail.CapabilityError):mail.execute_transport(value,mail.validate_plan(self.root,value),smtp_starttls=lambda *a,**k:client,revalidate=deny)
        self.assertEqual(client.sent,[])
    def test_imap_is_read_only_uses_peek_and_groups_thread_references(self):
        client=IMAP(ssl_context=__import__('ssl').create_default_context())
        with patch.dict(os.environ,{'MAIL_ONE_PASSWORD':'fictional-secret'}):
            messages=mail.read_mail(self.account,'INBOX',imap_factory=lambda *a,**k:client,search='Anfrage')
        self.assertTrue(client.readonly);self.assertEqual(messages[0]['thread_ref'],'<old@example.invalid>')
        self.assertEqual(messages[0]['uidvalidity'],'7');self.assertIn(('fetch',(b'12','(BODY.PEEK[])')),client.commands)
        self.assertIn('OR',client.commands[0][1]);self.assertIn('untrusted',messages[0]['trust'])
    def test_imap_search_quotes_are_escaped(self):
        client=IMAP(ssl_context=__import__('ssl').create_default_context())
        with patch.dict(os.environ,{'MAIL_ONE_PASSWORD':'fictional-secret'}):
            mail.read_mail(self.account,'INBOX',imap_factory=lambda *a,**k:client,search='x" ALL "')
        criteria=client.commands[0][1]
        self.assertIn('"x\\" ALL \\""',criteria);self.assertNotIn('"x" ALL ""',criteria)
    def test_private_files_cannot_be_attached(self):
        for name in ('.env','token.json','client_secret_web.json','id_ed25519','approvals.jsonl','dump.sql','sub/secrets.json'):
            path=self.root/name;path.parent.mkdir(exist_ok=True);path.write_text('fictional-secret')
            self.message['attachments']=[{'path':name}]
            with self.subTest(name=name),self.assertRaises(mail.CapabilityError):self.prepare()
    def test_draft_append_is_separate_from_send(self):
        value=self.prepare(mode='draft');client=IMAP(ssl_context=__import__('ssl').create_default_context())
        with patch.dict(os.environ,{'MAIL_ONE_PASSWORD':'fictional-secret'}):
            result=mail.execute_transport(value,mail.validate_plan(self.root,value),imap_factory=lambda *a,**k:client,revalidate=lambda:None)
        self.assertEqual(result['status'],'accepted');self.assertEqual(len(client.appended),1);self.assertEqual(value['action'],'modify_external')
    def test_attachments_are_frozen_and_extracted_only_to_explicit_local_paths(self):
        (self.root/'proof.txt').write_text('Fiktiver Anhang');self.message['attachments']=[{'path':'proof.txt'}]
        value=self.prepare();parsed=mail.BytesParser(policy=mail.policy.default).parsebytes(mail.validate_plan(self.root,value))
        part=next(index for index,item in enumerate(parsed.walk()) if item.get_content_disposition()=='attachment')
        mail.extract_attachment(self.root,'draft.eml',part,'saved.txt')
        self.assertEqual((self.root/'saved.txt').read_text(),'Fiktiver Anhang')
        with self.assertRaises(mail.CapabilityError):mail.extract_attachment(self.root,'draft.eml',part,'../escape')
    def test_multiple_accounts_and_read_scope_remain_separate(self):
        account=dict(self.account,id='account-two',credential_ref='MAIL_TWO',read_enabled=False)
        with self.assertRaises(mail.CapabilityError):mail.read_mail(account,'INBOX')
        with self.assertRaises(mail.CapabilityError):mail.read_mail(self.account,'OtherMailbox')
        account['smtp']=dict(account['smtp'],tls='none')
        with self.assertRaises(mail.CapabilityError):mail.validate_account(account)
    def test_contact_outbox_import_never_grants_consent_or_sends(self):
        source=self.root/'inbound.json';source.write_text(json.dumps({'schema_version':'0.1','kind':'contact','id':'fixture','untrusted_input':True,'reply_to':'visitor@example.invalid','to':'owner@example.invalid','subject':'Website-Anfrage','body':'Bitte um Rückruf.'}))
        result=mail.import_contact(self.root,source,'inbound-normalized.json')
        self.assertEqual(result['message_count'],1)
        self.assertIn('not instructions, consent',json.loads((self.root/'inbound-normalized.json').read_text())['messages'][0]['trust'])

    def test_raw_import_is_explicit_and_partial_refusals_are_not_delivery(self):
        imap=IMAP(ssl_context=__import__('ssl').create_default_context())
        with patch.dict(os.environ,{'MAIL_ONE_PASSWORD':'fictional-secret'}):
            messages=mail.read_mail(self.account,'INBOX',imap_factory=lambda *a,**k:imap,include_raw=True)
        self.assertEqual(messages[0]['_raw_message'],IMAP.message)
        self.message['cc']=['refused@example.invalid'];value=self.prepare();client=SMTP()
        client.sendmail=lambda *args:{'refused@example.invalid':(550,b'rejected')}
        with patch.dict(os.environ,{'MAIL_ONE_PASSWORD':'fictional-secret'}):
            result=mail.execute_transport(value,mail.validate_plan(self.root,value),smtp_starttls=lambda *a,**k:client,revalidate=lambda:None)
        self.assertEqual(result['status'],'accepted');self.assertEqual(result['accepted_count'],1);self.assertEqual(result['refused_count'],1)

    def test_cli_send_uses_full_approval_and_never_repeats_smtp(self):
        import contextlib,io
        sys.path.insert(0,str(ROOT/'.suite/tests'))
        from test_capability_runtime import approve
        value=self.prepare();log,plan,request,event=approve(self.root,value,'send',value['target']);client=SMTP()
        original=mail.execute_transport
        def transport(value,data,revalidate):return original(value,data,smtp_starttls=lambda *a,**k:client,revalidate=revalidate)
        arguments=['adapter.py','--root',str(self.root),'execute','--plan',str(plan),'--approvals',str(log),'--request-id',request['id'],'--execution-log',str(self.root/'executions.jsonl'),'--key','send-once','--harness-authorized']
        with patch.dict(os.environ,{'MAIL_ONE_PASSWORD':'fictional-secret'}),patch.object(mail,'execute_transport',side_effect=transport),patch.object(sys,'argv',arguments):
            for attempt in range(2):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):self.assertEqual(mail.main(),0)
                result=json.loads(output.getvalue());self.assertEqual(result['status'],'accepted')
                if attempt:self.assertTrue(result['replayed'])
        self.assertEqual(len(client.sent),1)
        self.assertNotIn('fictional-secret',(self.root/'executions.jsonl').read_text())

    def test_cli_read_saves_originals_only_in_explicit_private_directory(self):
        import contextlib,io
        account=self.root/'account.json';account.write_text(json.dumps(self.account));client=IMAP(ssl_context=__import__('ssl').create_default_context())
        original=mail.read_mail
        def fetch(*args,**kwargs):return original(*args,imap_factory=lambda *a,**k:client,**kwargs)
        arguments=['adapter.py','--root',str(self.root),'read','--account',str(account),'--mailbox','INBOX','--authorization-ref','fixture:read','--execution-log',str(self.root/'executions.jsonl'),'--key','read-once','--output','inbound.json','--raw-dir','originals','--harness-authorized']
        with patch.dict(os.environ,{'MAIL_ONE_PASSWORD':'fictional-secret'}),patch.object(mail,'read_mail',side_effect=fetch),patch.object(sys,'argv',arguments),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(mail.main(),0)
        result=json.loads((self.root/'inbound.json').read_text());path=self.root/result['messages'][0]['raw_message_path']
        self.assertEqual(path.read_bytes(),IMAP.message);self.assertNotIn('_raw_message',result['messages'][0])
