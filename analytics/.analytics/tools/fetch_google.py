#!/usr/bin/env python3
"""Read-only export of aggregated GA4 / Search Console data into CSV plus dataset manifest.

Standard library only. The OAuth access token is read from an environment variable and is
never written anywhere; request it with read-only scopes only (analytics.readonly,
webmasters.readonly). Output feeds evaluate_csv.py; it is not an attribution or causality claim.
"""
import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import sys
from urllib import parse, request
from zoneinfo import ZoneInfo

GA4_URL = 'https://analyticsdata.googleapis.com/v1beta/properties/%s:runReport'
GSC_URL = 'https://www.googleapis.com/webmasters/v3/sites/%s/searchAnalytics/query'
# Distinct users are deliberately absent: daily/channel users cannot be added.
GA4_METRICS = ['sessions', 'engagedSessions', 'keyEvents']
PAGE = 10000


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise OSError('API redirects are refused')


def http_post(url, body, token):
    req = request.Request(url, data=json.dumps(body).encode('utf-8'), method='POST',
                          headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    with request.build_opener(NoRedirect()).open(req, timeout=60) as response:
        return json.loads(response.read().decode('utf-8'))


def fetch_ga4(prop, start, end, token, post=http_post, expected_zone=None):
    rows, offset = [], 0
    while True:
        data = post(GA4_URL % prop, {
            'dateRanges': [{'startDate': start.isoformat(), 'endDate': end.isoformat()}],
            'dimensions': [{'name': 'date'}, {'name': 'sessionDefaultChannelGroup'}],
            'metrics': [{'name': m} for m in GA4_METRICS],
            'orderBys': [{'dimension': {'dimensionName': 'date'}},
                         {'dimension': {'dimensionName': 'sessionDefaultChannelGroup'}}],
            'limit': PAGE, 'offset': offset, 'keepEmptyRows': False}, token)
        actual_zone = data.get('metadata', {}).get('timeZone')
        if actual_zone and expected_zone and actual_zone != expected_zone:
            raise ValueError('Property timezone does not match --time-zone')
        for row in data.get('rows', []):
            day, channel = (v['value'] for v in row['dimensionValues'])
            values = [v['value'] for v in row['metricValues']]
            if len(values) != len(GA4_METRICS):
                raise ValueError('Unexpected GA4 metric columns')
            rows.append({'date': '%s-%s-%s' % (day[:4], day[4:6], day[6:]), 'channel': channel,
                         **dict(zip(GA4_METRICS, values))})
        offset += PAGE
        if offset >= int(data.get('rowCount', 0)):
            break
    metrics = {m: {'unit': 'count', 'aggregation': 'sum'} for m in GA4_METRICS}
    metrics['engagement_rate'] = {'unit': 'ratio', 'aggregation': 'ratio',
                                  'numerator': 'engagedSessions', 'denominator': 'sessions'}
    return ['date', 'channel'] + GA4_METRICS, rows, metrics, 'GA4 Data API runReport, property ' + prop


def fetch_gsc(site, start, end, token, dimension=None, post=http_post):
    dims = ['date'] + ([dimension] if dimension else [])
    rows, start_row = [], 0
    while True:
        data = post(GSC_URL % parse.quote(site, safe=''), {
            'startDate': start.isoformat(), 'endDate': end.isoformat(), 'dimensions': dims,
            'rowLimit': 25000, 'startRow': start_row, 'dataState': 'final'}, token)
        batch = data.get('rows', [])
        for row in batch:
            # Average position is not additive; keep an impression-weighted sum instead.
            rows.append({**dict(zip(dims, row['keys'])), 'clicks': row['clicks'],
                         'impressions': row['impressions'],
                         'position_x_impressions': round(row['position'] * row['impressions'], 2)})
        if len(batch) < 25000:
            break
        start_row += 25000
    metrics = {'clicks': {'unit': 'count', 'aggregation': 'sum'},
               'impressions': {'unit': 'count', 'aggregation': 'sum'},
               'position_x_impressions': {'unit': 'position*impressions', 'aggregation': 'sum'},
               'ctr': {'unit': 'ratio', 'aggregation': 'ratio', 'numerator': 'clicks', 'denominator': 'impressions'},
               'avg_position': {'unit': 'position', 'aggregation': 'ratio',
                                'numerator': 'position_x_impressions', 'denominator': 'impressions'}}
    return dims + ['clicks', 'impressions', 'position_x_impressions'], rows, metrics, 'Search Console searchAnalytics, ' + site


def write_dataset(out_dir, dataset_id, columns, rows, metrics, source, start, end, time_zone, now=None, privacy_class='internal'):
    out_dir = Path(out_dir)
    out_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    manifest = {'dataset_id': dataset_id, 'source_system': source,
                'extracted_at': (now or datetime.now(timezone.utc)).isoformat(timespec='seconds'),
                'time_zone': time_zone, 'grain': 'one row per ' + ' x '.join(c for c in columns if c not in metrics),
                'period_start': start.isoformat(), 'period_end': end.isoformat(),
                'privacy_class': privacy_class, 'metric_definitions': metrics,
                'permissions': 'Read-only API export; query/page values can contain personal or confidential data',
                'notes': '%d rows. Platform-reported values; sampling, thresholds and consent gaps possible.' % len(rows)}
    paths = (out_dir / (dataset_id + '.csv'), out_dir / (dataset_id + '.manifest.json'))
    created = []
    try:
        for path, text in zip(paths, (stream.getvalue(), json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')):
            descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created.append(path)
            with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
    except Exception:
        for path in created:
            path.unlink()
        raise
    return paths


def main(argv=None, post=http_post, today=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', choices=['ga4', 'gsc'])
    parser.add_argument('--property', help='GA4 property ID (numerisch)')
    parser.add_argument('--site', help='Search-Console-Property, z. B. sc-domain:example.com')
    parser.add_argument('--dimension', choices=['query', 'page', 'country', 'device'], help='nur gsc')
    parser.add_argument('--days', type=int, default=30)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--time-zone', help='GA4: tatsächliche IANA-Property-Zeitzone erforderlich; GSC: immer America/Los_Angeles')
    parser.add_argument('--token-env', default='GOOGLE_OAUTH_ACCESS_TOKEN')
    args = parser.parse_args(argv)
    token = os.environ.get(args.token_env)
    if not token:
        parser.error('Umgebungsvariable %s fehlt (read-only OAuth-Token)' % args.token_env)
    if not 1 <= args.days <= 480:
        parser.error('--days muss zwischen 1 und 480 liegen')
    if args.source == 'ga4' and not args.time_zone:
        parser.error('--time-zone der GA4-Property ist erforderlich')
    if args.source == 'gsc' and args.time_zone not in (None, 'America/Los_Angeles'):
        parser.error('Search Console verwendet America/Los_Angeles; keine Umdeklaration möglich')
    effective_zone = args.time_zone if args.source == 'ga4' else 'America/Los_Angeles'
    try:
        zone = ZoneInfo(effective_zone)
    except (ValueError, KeyError):
        parser.error('Ungültige IANA-Zeitzone')
    # Conservative reporting windows, not a guarantee that data is complete.
    end = (today or datetime.now(zone).date()) - timedelta(days=1 if args.source == 'ga4' else 3)
    start = end - timedelta(days=args.days - 1)
    try:
        if args.source == 'ga4':
            if not (args.property or '').isdigit():
                parser.error('--property (numerisch) ist für ga4 erforderlich')
            result = fetch_ga4(args.property, start, end, token, post=post, expected_zone=effective_zone)
            dataset_id = 'ga4-%s-%s-%s' % (args.property, start, end)
        else:
            if not args.site:
                parser.error('--site ist für gsc erforderlich')
            result = fetch_gsc(args.site, start, end, token, args.dimension, post=post)
            slug = ''.join(c if c.isalnum() else '-' for c in args.site).strip('-')
            dataset_id = 'gsc-%s-%s-%s-%s' % (slug, args.dimension or 'date', start, end)
        paths = write_dataset(args.out_dir, dataset_id, *result, start, end, effective_zone,
                              privacy_class='confidential' if args.source == 'gsc' and args.dimension in ('query', 'page') else 'internal')
    except (OSError, ValueError, KeyError) as exc:
        print('FETCH_FAILED:', type(exc).__name__, 'Abruf oder lokale Ausgabe fehlgeschlagen; keine Zugangsdaten ausgeben.', file=sys.stderr)
        return 2
    print(json.dumps({'csv': str(paths[0]), 'manifest': str(paths[1]), 'rows': len(result[1])}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
