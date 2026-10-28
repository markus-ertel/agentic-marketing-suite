"""Technical weekly-review runs with synthetic data, mocked providers and temporary private outputs."""
import contextlib
from copy import deepcopy
import csv
from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(MODULE/'tools'))
import weekly_review as weekly

AS_OF='2026-10-28T09:00:00+01:00'


class WeeklyReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.profile=Path(weekly.init_demo(self.root/'private')['profile'])
        self.value=json.loads(self.profile.read_text())
        self.output=self.profile.parent/'runs'

    def save(self, value=None):
        if value is not None:self.value=value
        self.profile.write_bytes(weekly.encoded(self.value))

    def run_review(self, **kwargs):
        return weekly.run(self.profile,True,AS_OF,**kwargs)

    def result(self, run):
        return json.loads((Path(run['run_dir'])/'result.json').read_text())

    def test_plan_is_read_only_and_schedule_is_only_intent(self):
        before={p:p.read_bytes() for p in self.profile.parent.rglob('*') if p.is_file()}
        with patch.object(weekly.fetch_google,'http_post',side_effect=AssertionError('no network')):
            plan=weekly.plan(self.profile,AS_OF)
        self.assertFalse(plan['network_called'])
        self.assertFalse(plan['model_called'])
        self.assertEqual(plan['schedule_runtime_status'],'not_checked_or_configured_by_this_tool')
        self.assertEqual(plan['sources'][0]['period_a'],['2026-10-14','2026-10-20'])
        self.assertEqual(plan['sources'][0]['period_b'],['2026-10-21','2026-10-27'])
        self.assertEqual(before,{p:p.read_bytes() for p in self.profile.parent.rglob('*') if p.is_file()})
        self.assertFalse(self.output.exists())

    def test_run_requires_current_harness_authorization(self):
        with self.assertRaises(ValueError):weekly.run(self.profile,as_of=AS_OF)
        self.assertFalse(self.output.exists())

    def test_complete_demo_hashes_private_artifacts_and_no_raw_model_context(self):
        csv_path=self.profile.parent/'weekly-review-demo.csv'
        original=csv_path.read_bytes()
        run=self.run_review();result=self.result(run);folder=Path(run['run_dir'])
        self.assertEqual(run['status'],'complete')
        self.assertEqual(run['review_status'],'pending_harness_review')
        self.assertEqual(result['computed_metrics'],2)
        self.assertEqual(result['profile_sha256'],weekly.digest(self.profile.read_bytes()))
        self.assertEqual((folder/'profile.json').read_bytes(),self.profile.read_bytes())
        self.assertEqual(weekly.digest((folder/'result.json').read_bytes()),run['result_sha256'])
        for name,sha in result['artifacts'].items():self.assertEqual(weekly.digest((folder/name).read_bytes()),sha)
        metric=result['sources'][0]['metrics'][1]['result']
        self.assertEqual(metric['period_b']['value'],metric['period_b']['numerator_sum']/metric['period_b']['denominator_sum'])
        context=(folder/'harness-context.json').read_text()
        self.assertNotIn('FICTIONAL_RAW_NOTE_NOT_MODEL_CONTEXT',context)
        self.assertNotIn('csv_path',context)
        self.assertNotIn('"notes":',context)
        self.assertNotIn('No real customer, account or observed business effect.',context)
        self.assertEqual(csv_path.read_bytes(),original)
        events=[json.loads(line) for line in (folder/'events.jsonl').read_text().splitlines()]
        self.assertEqual(events[0]['type'],'started');self.assertEqual(events[-1]['type'],'finished')
        for p in folder.rglob('*'):
            self.assertEqual(p.stat().st_mode&0o777,0o700 if p.is_dir() else 0o600)

    def test_repeated_runs_get_new_directories_and_never_overwrite(self):
        first=self.run_review();folder=Path(first['run_dir'])
        before={p:p.read_bytes() for p in folder.rglob('*') if p.is_file()}
        second=self.run_review()
        self.assertNotEqual(first['run_dir'],second['run_dir'])
        self.assertEqual(before,{p:p.read_bytes() for p in folder.rglob('*') if p.is_file()})

    def test_missing_source_and_partial_success_do_not_become_all_clear(self):
        extra=deepcopy(self.value['sources'][0]);extra['id']='missing';extra['csv_path']='absent.csv'
        self.value['sources'].append(extra);self.save()
        run=self.run_review();result=self.result(run)
        self.assertEqual(run['status'],'partial')
        self.assertEqual(result['sources'][1]['status'],'blocked')
        self.assertTrue((Path(run['run_dir'])/'report.md').is_file())
        self.value['sources']=[extra];self.save()
        blocked=self.run_review()
        self.assertEqual(blocked['status'],'blocked')
        self.assertEqual(self.result(blocked)['computed_metrics'],0)

    def test_missing_day_in_one_channel_is_not_masked_by_another_channel(self):
        path=self.profile.parent/'weekly-review-demo.csv'
        rows=list(csv.DictReader(io.StringIO(path.read_text())))
        rows=[r for r in rows if not(r['date']=='2026-10-15' and r['channel']=='search')]
        self.write_csv(rows)
        run=self.run_review()
        self.assertEqual(run['status'],'partial')
        self.assertIn('2026-10-15',self.result(run)['sources'][0]['metrics'][0]['missing_dates'])

    def write_csv(self, rows):
        path=self.profile.parent/'weekly-review-demo.csv'
        stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows);path.write_text(stream.getvalue())
        manifest_path=self.profile.parent/'weekly-review-demo.manifest.json'
        manifest=json.loads(manifest_path.read_text());manifest['file_sha256']=weekly.digest(path.read_bytes())
        manifest_path.write_text(json.dumps(manifest))

    def test_manifest_hash_timezone_period_and_nonadditive_metrics_block(self):
        path=self.profile.parent/'weekly-review-demo.manifest.json'
        original=json.loads(path.read_text())
        for edits in ({'file_sha256':'a'*64},{'time_zone':'UTC'},{'period_end':'2026-10-20'},
                      {'metric_definitions':{'sessions':{'unit':'count','aggregation':'distinct'}}}):
            with self.subTest(edits=edits):
                path.write_text(json.dumps(dict(original,**edits)))
                self.assertEqual(self.run_review()['status'],'blocked')
        path.write_text(json.dumps(original))
        self.value['sources'][0]['metrics'][0]['numerator']='not-present';self.save()
        self.assertEqual(self.run_review()['status'],'partial')

    def test_zero_denominator_cannot_be_reported_as_a_valid_rate(self):
        rows=list(csv.DictReader(io.StringIO((self.profile.parent/'weekly-review-demo.csv').read_text())))
        for row in rows:row['sessions']='0'
        self.write_csv(rows)
        self.value['sources'][0]['metrics']=self.value['sources'][0]['metrics'][1:];self.save()
        run=self.run_review();self.assertEqual(run['status'],'blocked')
        self.assertIsNone(self.result(run)['sources'][0]['metrics'][0]['result']['period_b']['value'])

    def test_unreadable_pending_logs_cause_partial_not_no_open_items(self):
        broken=self.root/'approvals.jsonl';broken.write_text('{broken')
        self.value['approvals']={'logs':[{'label':'private','path':str(broken)}]};self.save()
        run=self.run_review()
        self.assertEqual(run['status'],'partial')
        self.assertEqual(self.result(run)['approvals']['status'],'blocked')
        self.assertTrue(self.result(run)['approvals']['errors'])
        self.assertEqual(broken.read_text(),'{broken')

    def test_pending_rows_are_read_only_minimized_and_not_failures(self):
        demo=weekly.ROOT/'.suite/beispiele/approval-demo/approvals-demo.jsonl'
        before=demo.read_bytes()
        self.value['approvals']={'logs':[{'label':'demo','path':str(demo)}]};self.save()
        result=self.result(self.run_review())
        self.assertEqual(result['status'],'complete')
        self.assertTrue(result['approvals']['items'])
        for row in result['approvals']['items']:
            self.assertNotIn('actor',row);self.assertNotIn('path',row);self.assertNotIn('title',row)
        self.assertEqual(before,demo.read_bytes())

    def test_privacy_classes_need_explicit_scope_and_gsc_blocks_before_fetch(self):
        manifest_path=self.profile.parent/'weekly-review-demo.manifest.json'
        manifest=json.loads(manifest_path.read_text());manifest['privacy_class']='confidential'
        manifest_path.write_bytes(weekly.encoded(manifest))
        result=self.result(self.run_review())
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['sources'][0]['error'],'SOURCE_PRIVACY_CLASS_NOT_ALLOWED')
        self.value['sources'][0]['allowed_privacy_classes']=['confidential'];self.save()
        result=self.result(self.run_review())
        self.assertEqual(result['status'],'complete')
        source=self.value['sources'][0]
        source.update(kind='gsc',site='sc-domain:example.org',time_zone='America/Los_Angeles',dimension='query',allowed_privacy_classes=['internal'])
        del source['csv_path'];del source['manifest_path'];self.save()
        with patch.object(weekly.fetch_google,'http_post',side_effect=AssertionError('must not fetch')):
            result=self.result(self.run_review())
        self.assertEqual(result['sources'][0]['error'],'SOURCE_PRIVACY_CLASS_NOT_ALLOWED')

    def test_missing_google_token_and_partial_cli_exit_are_visible(self):
        self.value['approvals']={'logs':[{'label':'missing','path':str(self.root/'missing.jsonl')}]};self.save()
        cli=subprocess.run([sys.executable,str(MODULE/'tools/weekly_review.py'),'run','--profile',str(self.profile),'--as-of',AS_OF,'--harness-authorized'],capture_output=True,text=True)
        self.assertEqual(cli.returncode,1,cli.stderr)
        self.assertEqual(json.loads(cli.stdout)['status'],'partial')
        source=self.value['sources'][0]
        source.update(kind='ga4',property='12345',token_env='WEEKLY_TEST_ABSENT_TOKEN')
        del source['csv_path'];del source['manifest_path'];self.save()
        with patch.dict(weekly.os.environ,{},clear=True):
            result=self.result(self.run_review())
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['sources'][0]['error'],'READ_CREDENTIAL_UNAVAILABLE')

    def test_invalid_profile_and_in_repository_output_never_run(self):
        bad=[]
        item=deepcopy(self.value);item['output_dir']=str(weekly.ROOT/'analytics/results');bad.append(item)
        item=deepcopy(self.value);item['token']='secret';bad.append(item)
        item=deepcopy(self.value);item['model_context']='raw';bad.append(item)
        item=deepcopy(self.value);item['schedule']['local_time']='25:99';bad.append(item)
        item=deepcopy(self.value);item['sources'].append(deepcopy(item['sources'][0]));bad.append(item)
        item=deepcopy(self.value);item['sources'][0]['metrics'][0]['segment']='one';del item['sources'][0]['metrics'][0]['segment_column'];bad.append(item)
        for value in bad:
            with self.subTest(value=value):
                self.profile.write_text(json.dumps(value))
                with self.assertRaises((ValueError,TypeError,KeyError)):weekly.plan(self.profile,AS_OF)
                self.assertFalse(self.output.exists())

    def test_lock_and_interruption_never_publish_a_success_marker(self):
        self.output.mkdir()
        lock=self.output/('.weekly-'+self.value['id']+'.lock');lock.touch()
        with self.assertRaises(FileExistsError):self.run_review()
        lock.unlink()
        with patch.object(weekly,'acquire',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.run_review()
        runs=[p for p in self.output.iterdir() if p.is_dir()]
        self.assertEqual(len(runs),1)
        self.assertFalse((runs[0]/'result.json').exists())
        self.assertTrue((runs[0]/'events.jsonl').is_file())
        self.assertFalse(lock.exists())

    def test_google_adapter_uses_exact_windows_and_never_reuses_an_old_extract(self):
        source=self.value['sources'][0]
        source.update(kind='ga4',property='123',metrics=[{'id':'events','numerator':'keyEvents'}])
        del source['csv_path'];del source['manifest_path'];self.save()
        rows=list(csv.DictReader(io.StringIO((self.profile.parent/'weekly-review-demo.csv').read_text())))
        page={'rowCount':len(rows),'metadata':{'timeZone':'Europe/Vienna'},'rows':[
            {'dimensionValues':[{'value':r['date'].replace('-','')},{'value':r['channel']}],
             'metricValues':[{'value':r['sessions']},{'value':r['sessions']},{'value':r['requests']}]} for r in rows]}
        calls=[]
        def post(url,body,token):calls.append(body);return page
        with patch.dict('os.environ',{'GOOGLE_OAUTH_ACCESS_TOKEN':'fictional-secret'}):
            result=self.result(self.run_review(post=post))
            self.assertEqual(result['status'],'complete')
            self.assertEqual(calls[0]['dateRanges'],[{'startDate':'2026-10-14','endDate':'2026-10-27'}])
            self.assertEqual(result['sources'][0]['metrics'][0]['segment_column'],'channel')
            def failed(*args):raise OSError('fictional-secret must not leak')
            failed_run=self.run_review(post=failed)
        self.assertEqual(failed_run['status'],'blocked')
        folder=Path(failed_run['run_dir'])
        for path in folder.rglob('*'):
            if path.is_file():self.assertNotIn('fictional-secret',path.read_text())
        self.assertEqual(self.result(failed_run)['computed_metrics'],0)
        self.assertEqual(len(list(folder.rglob('*.csv'))),0)

    def test_source_timezone_and_lag_define_different_explicit_windows(self):
        at=weekly.zoned('2026-10-28T23:30:00+00:00')
        source=deepcopy(self.value['sources'][0]);source['time_zone']='Asia/Tokyo'
        self.assertEqual(weekly.windows(self.value,source,at)[1][1].isoformat(),'2026-10-28')
        source.update(kind='gsc',time_zone='America/Los_Angeles',lag_days=3)
        self.assertEqual(weekly.windows(self.value,source,at)[1][1].isoformat(),'2026-10-25')

    def test_cli_demo_plan_run_exit_codes_and_standalone_module(self):
        cli=[sys.executable,str(MODULE/'tools/weekly_review.py')]
        base=['--profile',str(self.profile),'--as-of',AS_OF]
        blocked=subprocess.run(cli+['run',*base],capture_output=True,text=True)
        self.assertEqual(blocked.returncode,2)
        complete=subprocess.run(cli+['run',*base,'--harness-authorized'],capture_output=True,text=True)
        self.assertEqual(complete.returncode,0,complete.stderr)
        self.assertEqual(json.loads(complete.stdout)['status'],'complete')
        isolated=self.root/'standalone';target=isolated/'analytics/.analytics'
        shutil.copytree(MODULE,target,ignore=shutil.ignore_patterns('__pycache__'))
        result=subprocess.run([sys.executable,str(target/'tools/weekly_review.py'),'plan',*base],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        run=subprocess.run([sys.executable,str(target/'tools/weekly_review.py'),'run',*base,'--harness-authorized'],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertFalse((isolated/'.suite').exists())


if __name__=='__main__':unittest.main()
