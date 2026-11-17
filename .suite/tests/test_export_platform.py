"""Temporary local files and fictional people only; no real approval, import or publication."""
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from approval_audit import record_decision, record_request
sys.path.insert(0, str(Path(__file__).resolve().parent))
from approval_key import use_test_key
import export_platform
from export_platform import CapabilityError, export

SUITE = Path(__file__).resolve().parents[1]
T = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=1)

ADS = {
    'schema_version': '0.1', 'campaign_id': 'DEMO-ADS-002', 'platform': 'google-ads', 'action': 'draft',
    'status': 'ready_for_review', 'account_ref': 'NOT_CONNECTED', 'objective': 'Fiktive Suchkampagne',
    'currency': 'EUR', 'budget': {'lifetime_max': '300', 'daily_max': '10',
                                   'period_start': '2026-11-01', 'period_end': '2026-11-30'},
    'creatives': ['Fiktive RSA'], 'landing_url': 'https://example.org/angebot',
    'approval': {'ref': None, 'approved_action': 'none', 'approved_budget': None, 'approved_by': None},
    'search_ads': {'campaign_name': 'Fiktiv – Suche Herbst', 'ad_groups': [{
        'name': 'Beratung', 'final_url': 'https://example.org/angebot', 'path1': 'beratung', 'path2': '',
        'headlines': ['Fiktive Beratung', 'Termin in 24 Stunden', 'Lokal in Wien'],
        'descriptions': ['Fiktiver Beschreibungstext eins.', 'Fiktiver Beschreibungstext zwei.'],
        'keywords': [{'text': 'marketing beratung wien', 'match': 'phrase'}]}]},
}


class ExportTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.key = use_test_key(self)
        self.log = self.root / 'approvals.jsonl'
        self.source = self.root / 'advertising' / 'kampagne.json'
        self.source.parent.mkdir()
        self.source.write_text(json.dumps(ADS, ensure_ascii=False), encoding='utf-8')

    def approve(self, path, action, target, decision='approved', budget=None):
        bundle = json.loads((SUITE / 'beispiele/demo-freigabe-bundle.json').read_text(encoding='utf-8'))
        art = bundle['artifacts'][0]
        art.update(path=path.relative_to(self.root).as_posix(), version=1, status='review',
                   sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        for review in bundle['reviews']:
            review.update(artifact_version=1, reviewed_at=(T - timedelta(minutes=5)).isoformat())
        req = dict(id='req-export-' + action, title='Fiktiver Export', summary='Fiktiver Test.',
                   requested_by='Spezialist', requested_at=T.isoformat(), artifact=art,
                   action=action, target=target, reviews=bundle['reviews'])
        if budget is not None:
            req.update(budget_limit=budget, currency='EUR')
        first = record_request(self.log, req, self.root, now=T)
        record_decision(self.log, req['id'], decision, 'Erika Beispiel', (T + timedelta(minutes=1)).isoformat(),
                        'trusted-harness:fictional', 'Fiktive Entscheidung.', first['id'], self.root,
                        now=T + timedelta(minutes=2), key=self.key)
        return req['id']

    def test_check_only_validates_without_approval_or_output(self):
        result = export('google-ads', self.source, None, self.root, check_only=True)
        self.assertEqual(result, {'check': 'pass', 'written': []})

    def test_limits_are_blocking(self):
        bad = json.loads(json.dumps(ADS))
        bad['search_ads']['ad_groups'][0]['headlines'][0] = 'x' * 31
        self.source.write_text(json.dumps(bad), encoding='utf-8')
        with self.assertRaisesRegex(CapabilityError, 'länger als 30'):
            export('google-ads', self.source, None, self.root, check_only=True)

    def test_export_requires_approval(self):
        with self.assertRaisesRegex(CapabilityError, 'Freigabe'):
            export('google-ads', self.source, self.root / 'out.csv', self.root)

    def test_approved_ads_export_is_paused_editor_csv(self):
        request_id = self.approve(self.source, 'spend', 'google-ads:000-000-0000', budget=300)
        out = self.root / 'editor.csv'
        result = export('google-ads', self.source, out, self.root, self.log, request_id, 'google-ads:000-000-0000')
        with out.open(encoding='utf-8') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows[0]['Campaign Status'], 'Paused')
        self.assertEqual(rows[1]['Ad type'], 'Responsive search ad')
        self.assertEqual(rows[2]['Criterion Type'], 'Phrase')
        self.assertIn('keine Plattformaktion', result['note'])
        with self.assertRaises(FileExistsError):
            export('google-ads', self.source, out, self.root, self.log, request_id, 'google-ads:000-000-0000')

    def test_budget_above_approval_blocks_export(self):
        request_id = self.approve(self.source, 'spend', 'google-ads:000-000-0000', budget=200)
        with self.assertRaisesRegex(CapabilityError, 'über der Freigabe'):
            export('google-ads', self.source, self.root / 'x.csv', self.root, self.log, request_id, 'google-ads:000-000-0000')
        self.assertFalse((self.root / 'x.csv').exists())

    def test_denied_request_blocks_export(self):
        request_id = self.approve(self.source, 'spend', 'google-ads:000-000-0000', 'denied', budget=300)
        with self.assertRaisesRegex(CapabilityError, 'absent, revoked or expired'):
            export('google-ads', self.source, self.root / 'd.csv', self.root, self.log, request_id, 'google-ads:000-000-0000')

    def test_changed_file_wrong_target_or_denial_block_export(self):
        request_id = self.approve(self.source, 'spend', 'google-ads:000-000-0000', budget=300)
        with self.assertRaisesRegex(CapabilityError, 'different plan, action or target'):
            export('google-ads', self.source, self.root / 'a.csv', self.root, self.log, request_id, 'google-ads:other')
        self.source.write_text(self.source.read_text(encoding='utf-8').replace('Lokal', 'Neu'), encoding='utf-8')
        with self.assertRaises(Exception):
            export('google-ads', self.source, self.root / 'b.csv', self.root, self.log, request_id, 'google-ads:000-000-0000')
        self.assertFalse((self.root / 'b.csv').exists())

    def test_email_export_escapes_html(self):
        draft = self.root / 'noCRM' / 'draft.json'
        draft.parent.mkdir()
        draft.write_text(json.dumps({'draft_id': 'D1', 'channel': 'email', 'subject': 'Fiktiv <Test>',
                                     'body': 'Hallo <b>Welt</b>\nZeile 2\n\nAbsatz 2'}), encoding='utf-8')
        request_id = self.approve(draft, 'send', 'email:fictional-list')
        export('email-html', draft, self.root / 'mail', self.root, self.log, request_id, 'email:fictional-list')
        page = (self.root / 'mail' / 'body.html').read_text(encoding='utf-8')
        self.assertIn('&lt;b&gt;Welt&lt;/b&gt;<br>', page)
        self.assertEqual(page.count('<p>'), 2)

    def test_social_csv_from_repository_example(self):
        job = json.loads((SUITE.parent / 'social-media/.social-media/integrationen/BEISPIEL_JOB.json').read_text())
        self.assertEqual(export_platform.check_social(job), [])
        columns, rows = export_platform.rows_social([job, job])
        self.assertEqual(columns, export_platform.SOCIAL_COLUMNS)
        self.assertEqual(len(rows), 2)

class ExportRegressionTests(unittest.TestCase):
    setUp = ExportTests.setUp
    approve = ExportTests.approve

    def test_multi_image_and_video_are_blocked_without_output(self):
        for extra in ({'assets': ['https://example.org/1.png', 'https://example.org/2.png']},
                      {'format': 'reel', 'assets': ['https://example.org/video.mp4']}):
            with self.subTest(extra=extra):
                job = dict(copy='Fictional post', channel='linkedin', **extra)
                self.assertTrue(export_platform.check_social(job))
                with self.assertRaises(CapabilityError):
                    export_platform.rows_social(job)

    def test_scheduler_converts_time_and_rejects_ambiguous_or_rounded_times(self):
        job = dict(copy='Fictional post', channel='linkedin', scheduled_at='2026-11-01T10:15:00Z')
        self.assertTrue(export_platform.check_social(job))
        columns, rows = export_platform.rows_social(job, 'Europe/Vienna')
        self.assertEqual(rows[0]['Posting Time'], '2026-11-01 11:15')
        self.assertEqual(rows[0]['Tags'], '')
        for stamp in ('2026-11-01T10:15:01Z', '2026-11-01T10:15:00', '2026-10-25T01:30:00Z'):
            with self.subTest(stamp=stamp), self.assertRaises(CapabilityError):
                export_platform.rows_social(dict(job, scheduled_at=stamp), 'Europe/Vienna')

    def test_mixed_accounts_and_empty_batch_are_rejected(self):
        a = dict(copy='Post A', channel='linkedin', account_id='one')
        b = dict(copy='Post B', channel='linkedin', account_id='two')
        self.assertTrue(export_platform.check_social([a,b]))
        self.assertTrue(export_platform.check_social([]))

    def test_ads_preserves_dates_and_rejects_invalid_budgets(self):
        columns, rows = export_platform.rows_google_ads(ADS)
        self.assertEqual(rows[0]['Start date'], ADS['budget']['period_start'])
        self.assertEqual(rows[0]['End date'], ADS['budget']['period_end'])
        for value in ('NaN', '-1', 'Infinity'):
            manifest = json.loads(json.dumps(ADS))
            manifest['budget']['daily_max'] = value
            self.assertTrue(export_platform.check_google_ads(manifest))

    def test_ads_daily_budget_over_the_run_must_fit_the_approved_total(self):
        # The CSV carries only the daily budget: 300 per day for 30 days would allow 9,000 against 300 approved.
        manifest = json.loads(json.dumps(ADS))
        manifest['budget'].update(daily_max='300', lifetime_max='300')
        self.assertTrue(any('Gesamtbudget' in e for e in export_platform.check_google_ads(manifest)))
        manifest['budget'].update(daily_max='10', lifetime_max='300')
        self.assertEqual(export_platform.check_google_ads(manifest), [])
        manifest['budget'].update(daily_max='10.01')
        self.assertTrue(export_platform.check_google_ads(manifest))

    def test_revocation_blocks_export_of_the_original_bytes(self):
        request_id = self.approve(self.source, 'spend', 'google-ads:000-000-0000', budget=300)
        events = [json.loads(line) for line in self.log.read_text().splitlines()]
        record_decision(self.log, request_id, 'revoked', 'Erika Beispiel',
                        (T + timedelta(minutes=3)).isoformat(), 'trusted-harness:fictional',
                        'Fiktiver Widerruf', events[-1]['id'], self.root, now=T+timedelta(minutes=4), key=self.key)
        out = self.root / 'revoked.csv'
        with self.assertRaises(CapabilityError):
            export('google-ads', self.source, out, self.root, self.log, request_id, 'google-ads:000-000-0000')
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
