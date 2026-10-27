"""Mocked HTTP only; no Google account, token or network is used."""
from datetime import date
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fetch_google
from evaluate_csv import main as evaluate

GA4_PAGE = {'rowCount': 2, 'rows': [
    {'dimensionValues': [{'value': '20261001'}, {'value': 'Organic Search'}],
     'metricValues': [{'value': '120'}, {'value': '80'}, {'value': '4'}]},
    {'dimensionValues': [{'value': '20261020'}, {'value': 'Organic Search'}],
     'metricValues': [{'value': '150'}, {'value': '90'}, {'value': '6'}]}]}
GSC_PAGE = {'rows': [{'keys': ['2026-10-01'], 'clicks': 10, 'impressions': 200, 'ctr': 0.05, 'position': 7.5}]}


class FetchTests(unittest.TestCase):
    def run_fetch(self, argv, response):
        calls = []

        def post(url, body, token):
            calls.append((url, body, token))
            return response
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        with mock.patch.dict('os.environ', {'GOOGLE_OAUTH_ACCESS_TOKEN': 'fictional-token'}):
            code = fetch_google.main(argv + (['--time-zone', 'Europe/Vienna'] if argv[0] == 'ga4' else []) + ['--out-dir', temp.name], post=post, today=date(2026, 10, 27))
        self.assertEqual(code, 0)
        return Path(temp.name), calls

    def test_ga4_writes_csv_and_manifest_without_token(self):
        out, calls = self.run_fetch(['ga4', '--property', '123'], GA4_PAGE)
        self.assertEqual(calls[0][1]['dateRanges'], [{'startDate': '2026-09-27', 'endDate': '2026-10-26'}])
        csv_path = out / 'ga4-123-2026-09-27-2026-10-26.csv'
        rows = list(csv.DictReader(csv_path.read_text(encoding='utf-8').splitlines()))
        self.assertEqual(rows[0]['date'], '2026-10-01')
        self.assertNotIn('totalUsers', rows[0])
        self.assertEqual(rows[0]['keyEvents'], '4')
        manifest_text = (out / 'ga4-123-2026-09-27-2026-10-26.manifest.json').read_text(encoding='utf-8')
        self.assertNotIn('fictional-token', manifest_text + csv_path.read_text(encoding='utf-8'))
        self.assertEqual(json.loads(manifest_text)['metric_definitions']['sessions']['aggregation'], 'sum')
        # Output is directly usable by the existing evaluator.
        self.assertEqual(evaluate(['--input', str(csv_path), '--metric', 'sessions',
                                   '--period-a', '2026-10-01:2026-10-10', '--period-b', '2026-10-11:2026-10-26']), 0)

    def test_gsc_keeps_position_additive_and_lags(self):
        out, calls = self.run_fetch(['gsc', '--site', 'sc-domain:example.org'], GSC_PAGE)
        self.assertIn('sc-domain%3Aexample.org', calls[0][0])
        self.assertEqual(calls[0][1]['endDate'], '2026-10-24')
        rows = list(csv.DictReader(next(out.glob('*.csv')).read_text(encoding='utf-8').splitlines()))
        self.assertEqual(rows[0]['position_x_impressions'], '1500.0')
        manifest = json.loads(next(out.glob('*.manifest.json')).read_text())
        self.assertEqual(manifest['time_zone'], 'America/Los_Angeles')

    def test_missing_token_is_refused(self):
        with mock.patch.dict('os.environ', {}, clear=True), self.assertRaises(SystemExit):
            fetch_google.main(['ga4', '--property', '1', '--out-dir', '.'])

class FetchRegressionTests(unittest.TestCase):
    def test_ga4_pagination_and_timezone_confirmation(self):
        from copy import deepcopy
        first = deepcopy(GA4_PAGE)
        first['rows'] = first['rows'][:1]
        first['metadata'] = {'timeZone': 'Europe/Vienna'}
        second = deepcopy(first)
        second['rows'] = GA4_PAGE['rows'][1:]
        calls = []
        def post(url, body, token):
            calls.append(body)
            return first if body['offset'] == 0 else second
        with mock.patch.object(fetch_google, 'PAGE', 1):
            columns, rows, metrics, _ = fetch_google.fetch_ga4('123', date(2026, 10, 1), date(2026, 10, 26), 'fake', post, 'Europe/Vienna')
        self.assertEqual([c['offset'] for c in calls], [0, 1])
        self.assertEqual(len(rows), 2)
        self.assertNotIn('totalUsers', columns)
        self.assertNotIn('totalUsers', metrics)
        with self.assertRaises(ValueError):
            fetch_google.fetch_ga4('123', date(2026, 10, 1), date(2026, 10, 26), 'fake', post, 'UTC')

    def test_gsc_second_page_and_private_query_manifest(self):
        page = {'rows': GSC_PAGE['rows'] * 25000}
        starts = []
        def post(url, body, token):
            starts.append(body['startRow'])
            return page if body['startRow'] == 0 else {'rows': []}
        _, rows, _, _ = fetch_google.fetch_gsc('sc-domain:example.org', date(2026, 10, 1), date(2026, 10, 24), 'fake', post=post)
        self.assertEqual(starts, [0, 25000])
        self.assertEqual(len(rows), 25000)
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict('os.environ', {'GOOGLE_OAUTH_ACCESS_TOKEN': 'secret'}):
            response = {'rows': [dict(GSC_PAGE['rows'][0], keys=['2026-10-01', 'fictional query'])]}
            code = fetch_google.main(['gsc', '--site', 'sc-domain:example.org', '--dimension', 'query', '--out-dir', temp], post=lambda *a: response, today=date(2026, 10, 27))
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(next(Path(temp).glob('*.manifest.json')).read_text())['privacy_class'], 'confidential')

    def test_timezone_overrides_cannot_mislabel_source_and_errors_redact_tokens(self):
        import contextlib, io
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict('os.environ', {'GOOGLE_OAUTH_ACCESS_TOKEN': 'secret'}):
            with self.assertRaises(SystemExit):
                fetch_google.main(['gsc', '--site', 'x', '--time-zone', 'Europe/Vienna', '--out-dir', temp])
            with self.assertRaises(SystemExit):
                fetch_google.main(['ga4', '--property', '123', '--out-dir', temp])
            errors = io.StringIO()
            def post(*args): raise OSError('secret provider details')
            with contextlib.redirect_stderr(errors):
                self.assertEqual(fetch_google.main(['gsc', '--site', 'x', '--out-dir', temp], post=post), 2)
            self.assertNotIn('secret', errors.getvalue())
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_output_collision_preserves_existing_manifest_and_removes_own_csv(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / 'demo.manifest.json'
            manifest.write_text('existing')
            with self.assertRaises(FileExistsError):
                fetch_google.write_dataset(temp, 'demo', ['date'], [], {}, 'demo', date(2026, 1, 1), date(2026, 1, 2), 'UTC')
            self.assertEqual(manifest.read_text(), 'existing')
            self.assertFalse((Path(temp) / 'demo.csv').exists())


if __name__ == '__main__':
    unittest.main()
