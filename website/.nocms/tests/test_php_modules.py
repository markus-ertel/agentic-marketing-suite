"""Real PHP HTTP tests on temporary sites. No external delivery; the transport is a private outbox."""
from datetime import datetime, timedelta, timezone
from html import unescape
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit, parse_qs
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[3]
PHP=shutil.which('php')
if os.environ.get('REQUIRE_PHP_TESTS')=='1' and not PHP:raise RuntimeError('PHP is required for this CI job')
spec=importlib.util.spec_from_file_location('php_webmodules',ROOT/'website/.nocms/tools/webmodules.py');web=importlib.util.module_from_spec(spec);spec.loader.exec_module(web)


@unittest.skipUnless(PHP,'PHP runtime not installed; mandatory PHP coverage runs in CI')
class PHPCLISafetyTests(unittest.TestCase):
    def test_csv_guard_blocks_formula_bypasses_and_keeps_plain_labels(self):
        values=['+1+HYPERLINK("x")','-1+WEBSERVICE("x")',' =SUM(A1)','- HYPERLINK("x")',
                '-20 % Rabatt','+43 1 234','-.5']
        code='require $argv[1]; $values=json_decode($argv[2],true); echo json_encode(array_map("wm_csv_cell",$values));'
        result=subprocess.run([PHP,'-r',code,str(ROOT/'website/.nocms/module/common/runtime.php'),json.dumps(values)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),["'"+v for v in values[:4]]+values[4:])


@unittest.skipUnless(PHP,'PHP runtime not installed; mandatory PHP HTTP coverage runs in CI')
class PHPModuleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.site=self.root/'site';self.site.mkdir();self.data=self.root/'private';self.data.mkdir(mode=0o700)
        for module in ('contact-form','newsletter','analytics-lite'):web.install(self.site,module)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        self.base='http://127.0.0.1:'+str(port)
        auth={'approval_ref':'fixture:bounded-service-mandate','expires_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}
        self.config={'origin':self.base,'privacy_url':'/privacy.html','data_dir':str(self.data),
                     'contact':{'enabled':True,'authorization':auth,'transport':'outbox','from':'website@example.invalid','to':'owner@example.invalid'},
                     'newsletter':{'enabled':True,'authorization':auth,'transport':'outbox','from':'website@example.invalid','consent_text':'Fiktiver Newsletter, jederzeit abmeldbar.','consent_version':'test-v1','endpoint_path':'/api/newsletter.php'},
                     'analytics':{'enabled':True,'authorization':auth,'pages':['/','/about.html'],'retention_days':2}}
        self.config_path=self.root/'config.json';self.save_config()
        self.capture=self.root/'mail-capture.eml';self.mail_exit=self.root/'mail-exit';self.mail_exit.write_text('0')
        fixture=self.root/'fake-mta.py';fixture.write_text("import os,sys\nfrom pathlib import Path\nPath(os.environ['MTA_CAPTURE']).write_bytes(sys.stdin.buffer.read())\nsys.exit(int(Path(os.environ['MTA_EXIT_FILE']).read_text()))\n")
        self.env=dict(os.environ,MTA_CAPTURE=str(self.capture),MTA_EXIT_FILE=str(self.mail_exit),WEBMODULE_CONFIG=str(self.config_path),WEBMODULE_SECRET='fictional-test-secret-'*3,WEBMODULE_DOCUMENT_ROOT=str(self.site))
        self.stderr=(self.root/'php.log').open('wb');self.addCleanup(self.stderr.close)
        self.process=subprocess.Popen([PHP,'-d','sendmail_path='+shlex.quote(sys.executable)+' '+shlex.quote(str(fixture)),'-S','127.0.0.1:'+str(port),'-t',str(self.site)],env=self.env,stdout=self.stderr,stderr=self.stderr)
        self.addCleanup(self.stop)
        for attempt in range(100):
            try:self.request('/api/contact.php');break
            except OSError:
                if self.process.poll() is not None:self.fail((self.root/'php.log').read_text())
                time.sleep(.03)
        else:self.fail('PHP test server did not start')
    def stop(self):
        self.process.terminate()
        try:self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
    def save_config(self):self.config_path.write_text(json.dumps(self.config))
    def request(self,path,data=None,headers=None,json_body=None):
        headers=dict(headers or {})
        if data is not None:payload=urlencode(data).encode();headers.setdefault('Content-Type','application/x-www-form-urlencoded');headers.setdefault('Origin',self.base)
        elif json_body is not None:payload=json.dumps(json_body).encode();headers.setdefault('Content-Type','application/json');headers.setdefault('Origin',self.base)
        else:payload=None
        try:response=urlopen(Request(self.base+path,data=payload,headers=headers),timeout=5)
        except HTTPError as error:response=error
        with response:return response.status,response.read().decode(),dict(response.headers)
    def token(self,path):
        status,body,headers=self.request(path);self.assertEqual(status,200,body)
        self.assertNotIn('Set-Cookie',headers)
        match=re.search(r'name="csrf" value="([^"]+)"',body);self.assertIsNotNone(match,body);return unescape(match.group(1))
    def contact(self,**changes):
        data={'csrf':self.token('/api/contact.php'),'website':'','name':'Erika Beispiel','email':'visitor@example.invalid','message':'Bitte um eine individuelle Antwort.'};data.update(changes)
        return self.request('/api/contact.php',data=data)
    def test_contact_queues_fixed_recipient_and_never_claims_delivery(self):
        status,body,_=self.contact();self.assertEqual(status,202,body);self.assertIn('entgegengenommen',body);self.assertNotIn('zugestellt',body.lower())
        files=list(self.data.glob('inbound-*.json'));self.assertEqual(len(files),1)
        value=json.loads(files[0].read_text());self.assertEqual(value['to'],'owner@example.invalid');self.assertEqual(value['reply_to'],'visitor@example.invalid');self.assertTrue(value['untrusted_input']);self.assertEqual(value['status'],'queued')
        self.assertNotIn('secret',files[0].read_text());self.assertFalse((self.site/'private').exists())
    def test_header_injection_unknown_fields_and_cross_origin_are_rejected(self):
        self.assertEqual(self.contact(email='x@example.invalid\r\nBcc: bad@example.invalid')[0],422)
        self.assertEqual(self.contact(to='bad@example.invalid')[0],422)
        data={'csrf':self.token('/api/contact.php'),'website':'','name':'X','email':'x@example.invalid','message':'Hi'}
        self.assertEqual(self.request('/api/contact.php',data=data,headers={'Origin':'https://attacker.invalid'})[0],403)
        self.assertEqual(len(list(self.data.glob('inbound-*.json'))),0)
    def test_csrf_replay_missing_token_and_honeypot_are_blocked(self):
        token=self.token('/api/contact.php');data={'csrf':token,'website':'','name':'Erika','email':'x@example.invalid','message':'Bitte antworten'}
        self.assertEqual(self.request('/api/contact.php',data=data)[0],202)
        self.assertEqual(self.request('/api/contact.php',data=data)[0],429)
        self.assertEqual(self.contact(csrf='')[0],403)
        self.assertEqual(self.contact(website='bot.example')[0],400)
        self.assertEqual(len(list(self.data.glob('inbound-*.json'))),1)
    def test_private_config_and_explicit_unexpired_service_mandate_required(self):
        self.config['contact']['authorization']['expires_at']='2020-01-01T00:00:00+00:00';self.save_config()
        self.assertEqual(self.request('/api/contact.php')[0],503)
        self.config['data_dir']=str(self.site);self.save_config()
        status,body,_=self.request('/api/contact.php');self.assertEqual(status,503);self.assertNotIn(str(self.root),body)
    def test_analytics_only_stores_approved_aggregate_page_counts(self):
        status,_,headers=self.request('/api/analytics.php',json_body={'page':'/'});self.assertEqual(status,204)
        self.assertNotIn('Set-Cookie',headers)
        counts=json.loads((self.data/'analytics.json').read_text());self.assertEqual(list(counts.values()),[{'/':1}])
        self.assertEqual(self.request('/api/analytics.php',json_body={'page':'/?email=private'})[0],422)
        self.assertEqual(self.request('/api/analytics.php',json_body={'page':'/'},headers={'DNT':'1'})[0],204)
        self.assertEqual(self.request('/api/analytics.php',json_body={'page':'/'},headers={'Sec-GPC':'1'})[0],204)
        self.assertEqual(json.loads((self.data/'analytics.json').read_text()),counts)
        self.assertNotIn('127.0.0.1',(self.data/'analytics.json').read_text());self.assertFalse((self.data/'rate.json').exists())
        export=subprocess.run([PHP,str(self.site/'api/analytics.php'),'--export'],env=self.env,capture_output=True,text=True)
        self.assertEqual(export.returncode,0,export.stderr);self.assertIn('date,page,pageviews',export.stdout)
    def test_analytics_optional_per_client_cap(self):
        self.config['analytics']['max_hits_per_client_day']=2;self.save_config()
        for _ in range(4):self.assertEqual(self.request('/api/analytics.php',json_body={'page':'/'})[0],204)
        self.assertEqual(json.loads((self.data/'analytics.json').read_text()).popitem()[1],{'/':2})
        self.assertNotIn('127.0.0.1',(self.data/'rate.json').read_text())
    def test_quotas_are_separate_per_form(self):
        for _ in range(3):self.assertEqual(self.contact()[0],202)
        self.assertEqual(self.contact()[0],429)
        token=self.token('/api/newsletter.php')
        status,body,_=self.request('/api/newsletter.php',data={'csrf':token,'website':'','action':'signup','email':'visitor@example.invalid','consent':'yes'})
        self.assertEqual(status,202,body)
    def test_trusted_proxy_uses_forwarded_client_only_from_configured_proxy(self):
        # Without configuration a forged X-Forwarded-For changes nothing: the quota still hits this client.
        for i in range(3):self.assertEqual(self.request('/api/contact.php',data=self.form(),headers={'X-Forwarded-For':'203.0.113.%d'%i})[0],202)
        self.assertEqual(self.request('/api/contact.php',data=self.form(),headers={'X-Forwarded-For':'203.0.113.9'})[0],429)
        self.config['trusted_proxies']=['127.0.0.1'];self.save_config()
        token=self.token_for('/api/contact.php',{'X-Forwarded-For':'198.51.100.7'})
        data=self.form(token);self.assertEqual(self.request('/api/contact.php',data=data,headers={'X-Forwarded-For':'198.51.100.7'})[0],202)
        # The signed form token is bound to the visitor, not to the proxy.
        data=self.form(self.token_for('/api/contact.php',{'X-Forwarded-For':'198.51.100.7'}))
        self.assertEqual(self.request('/api/contact.php',data=data,headers={'X-Forwarded-For':'198.51.100.8'})[0],403)
        self.config['trusted_proxies']=['not-an-ip'];self.save_config()
        self.assertEqual(self.request('/api/contact.php')[0],503)
    def form(self,token=None):
        return {'csrf':token or self.token('/api/contact.php'),'website':'','name':'Erika','email':'v@example.invalid','message':'Hallo'}
    def token_for(self,path,headers):
        status,body,_=self.request(path,headers=headers);self.assertEqual(status,200,body)
        return unescape(re.search(r'name="csrf" value="([^"]+)"',body).group(1))
    def test_newsletter_export_neutralizes_formula_cells(self):
        store={'a'*32:{'email':'=cmd@example.invalid','state':'confirmed','consent_version':'test-v1','confirmed_at':'2026-11-01T00:00:00+00:00'}}
        (self.data/'newsletter.json').write_text(json.dumps(store))
        export=subprocess.run([PHP,str(self.site/'api/newsletter.php'),'--export-confirmed'],env=self.env,capture_output=True,text=True)
        self.assertEqual(export.returncode,0,export.stderr);self.assertIn(",'=cmd@example.invalid,",export.stdout)
    def test_analytics_disabled_and_get_are_non_collecting(self):
        self.assertEqual(self.request('/api/analytics.php')[0],405)
        self.config['analytics']['enabled']=False;self.save_config()
        self.assertEqual(self.request('/api/analytics.php',json_body={'page':'/'})[0],204)
        self.assertFalse((self.data/'analytics.json').exists())
    def test_newsletter_requires_post_confirmation_then_supports_unsubscribe(self):
        token=self.token('/api/newsletter.php')
        status,body,_=self.request('/api/newsletter.php',data={'csrf':token,'website':'','action':'signup','email':'visitor@example.invalid','consent':'yes'});self.assertEqual(status,202,body)
        value=json.loads(next(self.data.glob('inbound-*.json')).read_text());match=re.search(r'http[^\s]+\?confirm=[a-f0-9]+',value['body']);self.assertIsNotNone(match)
        url=urlsplit(match.group());confirm=parse_qs(url.query)['confirm'][0]
        before=(self.data/'newsletter.json').read_bytes()
        token=self.token('/api/newsletter.php?confirm='+confirm)
        self.assertEqual((self.data/'newsletter.json').read_bytes(),before)
        status,body,_=self.request('/api/newsletter.php',data={'csrf':token,'website':'','action':'confirm','token':confirm});self.assertEqual(status,200,body)
        self.assertEqual(next(iter(json.loads((self.data/'newsletter.json').read_text()).values()))['state'],'confirmed')
        unsubscribe=unescape(re.search(r'href="\?unsubscribe=([^"]+)"',body).group(1))
        token=self.token('/api/newsletter.php?unsubscribe='+unsubscribe)
        status,body,_=self.request('/api/newsletter.php',data={'csrf':token,'website':'','action':'unsubscribe','token':unsubscribe});self.assertEqual(status,200,body)
        self.assertEqual(next(iter(json.loads((self.data/'newsletter.json').read_text()).values()))['state'],'unsubscribed')
        export=subprocess.run([PHP,str(self.site/'api/newsletter.php'),'--export-confirmed'],env=self.env,capture_output=True,text=True)
        self.assertEqual(export.returncode,0,export.stderr);self.assertNotIn('visitor@example.invalid',export.stdout)
    def test_newsletter_missing_consent_and_unknown_token_never_subscribe(self):
        token=self.token('/api/newsletter.php')
        status,_,_=self.request('/api/newsletter.php',data={'csrf':token,'website':'','action':'signup','email':'visitor@example.invalid','consent':'no'});self.assertEqual(status,422)
        token=self.token('/api/newsletter.php?confirm=invalid')
        status,_,_=self.request('/api/newsletter.php',data={'csrf':token,'website':'','action':'confirm','token':'invalid'});self.assertEqual(status,422)
        state=json.loads((self.data/'newsletter.json').read_text());self.assertEqual(state,[])

    def test_mail_variant_uses_fixed_headers_and_reports_only_mta_acceptance(self):
        from email import policy
        from email.parser import BytesParser
        self.config['contact']['transport']='mail';self.save_config()
        status,body,_=self.contact();self.assertEqual(status,202,body)
        message=BytesParser(policy=policy.default).parsebytes(self.capture.read_bytes())
        self.assertEqual(str(message['To']),'owner@example.invalid')
        self.assertEqual(str(message['Reply-To']),'visitor@example.invalid')
        self.assertIsNone(message['Bcc'])
        events=[json.loads(line) for line in (self.data/'delivery-events.jsonl').read_text().splitlines()]
        self.assertEqual(events[-1]['status'],'accepted')
        self.mail_exit.write_text('1')
        self.assertEqual(self.contact()[0],503)
        events=[json.loads(line) for line in (self.data/'delivery-events.jsonl').read_text().splitlines()]
        self.assertEqual(events[-1]['status'],'failed')

    def test_cli_retention_and_http_maintenance_boundary(self):
        self.assertEqual(self.request('/api/maintenance.php')[0],405)
        old=self.data/('inbound-'+'a'*32+'.json');old.write_text('{}');os.utime(old,(time.time()-40*86400,)*2)
        fresh=self.data/('inbound-'+'b'*32+'.json');fresh.write_text('{}')
        (self.data/'analytics.json').write_text(json.dumps({'2000-01-01':{'/':9}}))
        (self.data/'newsletter.json').write_text(json.dumps({'pending':{'state':'pending','expires':1,'email':'x@example.invalid'},'confirmed':{'state':'confirmed','email':'y@example.invalid'}}))
        result=subprocess.run([PHP,str(self.site/'api/maintenance.php'),'--purge-expired'],env=self.env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertFalse(old.exists());self.assertTrue(fresh.exists())
        self.assertEqual(json.loads((self.data/'analytics.json').read_text()),[])
        self.assertEqual(set(json.loads((self.data/'newsletter.json').read_text())),{'confirmed'})
