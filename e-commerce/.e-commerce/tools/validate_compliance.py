#!/usr/bin/env python3
"""Local compliance preflight for a funnel/offer definition (e-commerce v0.1).

Usage: validate_compliance.py funnel.json
       validate_compliance.py --offers funnel.json --catalog katalog.csv

Checks a bounded set of rules from .e-commerce/RECHT.md: order bumps never preselected,
explicit consent for add-ons, struck-through prices against the lowest 30-day price,
urgency claims with a truthful basis, stored-credential/MIT upsells with a documented
payment agreement, experiment design and approval before going live.
Standard library only, no network access. Not a legal review and no compliance certification.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from field_types import load_schema, type_errors
from generate_gmc_feed import CatalogError, check_reference_price, load_catalog, parse_price  # noqa: E402

STEP_TYPES = {'landing', 'product', 'checkout', 'order_bump', 'upsell', 'downsell', 'thank_you'}
STATUSES = {'draft', 'review', 'approved', 'live', 'paused', 'archived'}
PAYMENT_MODES = {'none', 'same_checkout', 'new_payment_sca', 'stored_credential_cit', 'mit_agreed'}
NEEDS_AGREEMENT = {'stored_credential_cit', 'mit_agreed'}
ADD_ON_STEPS = {'order_bump', 'upsell', 'downsell'}


def _missing(value):
    return value is None or (isinstance(value, str) and not value.strip())


def validate_funnel(funnel):
    """Return a list of findings (severity, location, message)."""
    findings = []

    def add(severity, where, message):
        findings.append((severity, where, message))

    if not isinstance(funnel, dict):
        return [('error', 'funnel', 'JSON-Objekt erwartet')]
    invalid = type_errors(funnel, load_schema('funnel-offer.schema.json'))
    if invalid:
        return [('error', 'funnel', message) for message in invalid]
    for key in ('id', 'version', 'status', 'currency', 'steps', 'offers'):
        if key not in funnel:
            add('error', 'funnel', f'Pflichtfeld fehlt: {key}')
    if isinstance(funnel.get('version'), int) and funnel['version'] < 1:
        add('error', 'funnel', 'version muss mindestens 1 sein')
    if 'currency' in funnel and not re.fullmatch(r'[A-Z]{3}', funnel['currency']):
        add('error', 'funnel', 'currency als dreistelligen Währungscode angeben')
    status = funnel.get('status')
    if status is not None and status not in STATUSES:
        add('error', 'funnel', f'status ungültig: {status!r}')
    if status in ('approved', 'live') and _missing(funnel.get('approval_ref')):
        add('error', 'funnel', f'status {status} ohne approval_ref (action-approval)')
    if status in ('review', 'approved', 'live') and _missing(funnel.get('legal_review_ref')):
        add('warning' if status == 'review' else 'error', 'funnel', 'legal_review_ref fehlt')
    currency = funnel.get('currency', 'EUR')

    offers = {}
    for offer in funnel.get('offers') or []:
        oid = offer.get('id') if isinstance(offer, dict) else None
        if _missing(oid):
            add('error', 'offers', 'Angebot ohne id')
            continue
        if oid in offers:
            add('error', oid, 'Angebots-id doppelt')
        offers[oid] = offer
        price = None
        try:
            price = parse_price(offer.get('price'), currency)
        except ValueError as exc:
            add('error', oid, f'price: {exc}')
        if not _missing(offer.get('compare_at_price')) and price:
            try:
                reference = parse_price(offer['compare_at_price'], currency)
            except ValueError as exc:
                add('error', oid, f'compare_at_price: {exc}')
            else:
                for severity, message in check_reference_price(
                        reference, price, offer.get('lowest_price_30d'), offer.get('omnibus_exception')):
                    add(severity, oid, message.replace('sale_price', 'price').replace('price muss', 'Angebotspreis muss'))
        urgency = offer.get('urgency')
        if urgency:
            if not isinstance(urgency, dict) or _missing(urgency.get('truthful_basis_ref')):
                add('error', oid, 'Dringlichkeit/Knappheit ohne truthful_basis_ref (Dark Pattern)')
            if isinstance(urgency, dict) and urgency.get('resets_on_reload'):
                add('error', oid, 'Countdown, der bei Neuladen neu startet, ist irreführend')

    step_ids = set()
    steps = funnel.get('steps') or []
    for step in steps:
        sid = step.get('id') if isinstance(step, dict) else None
        if _missing(sid):
            add('error', 'steps', 'Schritt ohne id')
            continue
        if sid in step_ids:
            add('error', sid, 'Schritt-id doppelt')
        step_ids.add(sid)
    for step in steps:
        if not isinstance(step, dict) or _missing(step.get('id')):
            continue
        sid, kind = step['id'], step.get('type')
        if kind not in STEP_TYPES:
            add('error', sid, f'type ungültig: {kind!r}')
        for key in ('next_on_accept', 'next_on_decline', 'next'):
            target = step.get(key)
            if target is not None and target not in step_ids:
                add('error', sid, f'{key} verweist auf unbekannten Schritt {target!r}')
        if kind in ADD_ON_STEPS:
            offer_ref = step.get('offer_ref')
            if offer_ref not in offers:
                add('error', sid, f'offer_ref {offer_ref!r} nicht in offers')
            if step.get('preselected') is not False:
                add('error', sid, 'preselected muss false sein (keine vorausgewählten Zusatzleistungen)')
            if step.get('requires_explicit_consent') is not True:
                add('error', sid, 'requires_explicit_consent muss true sein')
            if _missing(step.get('decline_label')):
                add('error', sid, 'decline_label fehlt; Ablehnung muss gleichwertig möglich sein')
            if step.get('confirmshaming'):
                add('error', sid, 'Confirmshaming im Ablehnungstext')
        if kind in ('upsell', 'downsell'):
            mode = step.get('payment_mode')
            if mode not in PAYMENT_MODES - {'none', 'same_checkout'}:
                add('error', sid, 'payment_mode für Folgekauf erforderlich: new_payment_sca, stored_credential_cit oder mit_agreed')
            if mode in NEEDS_AGREEMENT and _missing(step.get('payment_agreement_ref')):
                add('error', sid, f'payment_mode {mode} ohne payment_agreement_ref (Vereinbarung/Mandat, PSD2)')
            if mode in NEEDS_AGREEMENT and _missing(step.get('psp_confirmation_ref')):
                add('warning', sid, 'Einstufung (CIT/MIT, SCA) nicht vom Zahlungsdienst bestätigt')
            if _missing(step.get('button_label')):
                add('error', sid, 'button_label fehlt; eindeutige Zahlungspflicht-Beschriftung erforderlich')
            if step.get('auto_accept_after_seconds'):
                add('error', sid, 'automatische Annahme ohne Klick ist unzulässig')
        if kind == 'order_bump' and step.get('payment_mode') not in (None, 'same_checkout'):
            add('error', sid, 'order_bump wird mit der Hauptbestellung bezahlt (payment_mode same_checkout)')

    experiment = funnel.get('experiment')
    if experiment:
        for key in ('hypothesis', 'primary_metric', 'stopping_rule'):
            if _missing(experiment.get(key)):
                add('error', 'experiment', f'{key} fehlt')
        if len(experiment.get('variants') or []) < 2:
            add('error', 'experiment', 'mindestens zwei Varianten erforderlich')
        if _missing(experiment.get('analytics_ref')):
            add('warning', 'experiment', 'analytics_ref fehlt; Auswertung mit analytics/ abstimmen')
        if experiment.get('varies_price') and _missing(experiment.get('legal_review_ref')):
            add('error', 'experiment', 'Preistest ohne legal_review_ref')
    return findings


def check_catalog_prices(products, currency='EUR'):
    """Struck-through price check for every catalog row with a sale_price."""
    findings = []
    for index, product in enumerate(products):
        if _missing(product.get('sale_price')):
            continue
        where = str(product.get('sku') or f'Zeile {index + 1}')
        row_currency = product.get('currency') or currency
        try:
            price = parse_price(product.get('price'), row_currency)
            sale = parse_price(product.get('sale_price'), row_currency)
        except ValueError as exc:
            findings.append(('error', where, str(exc)))
            continue
        findings.extend((s, where, m) for s, m in check_reference_price(
            price, sale, product.get('lowest_price_30d'), product.get('omnibus_exception')))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description='Funnel- und Preis-Compliance lokal vorprüfen (keine Rechtsprüfung).')
    parser.add_argument('funnel', nargs='?', type=Path, help='Funnel-Definition (.json)')
    parser.add_argument('--offers', type=Path, help='Funnel-Definition (alternativ zum Positionsargument)')
    parser.add_argument('--catalog', type=Path, help='Katalog (.csv/.json) für die Streichpreisprüfung')
    args = parser.parse_args(argv)
    funnel_path = args.offers or args.funnel
    if not funnel_path and not args.catalog:
        parser.error('Funnel-Definition und/oder --catalog angeben')
    findings = []
    try:
        if funnel_path:
            findings.extend(validate_funnel(json.loads(funnel_path.read_text(encoding='utf-8'))))
        if args.catalog:
            products, defaults = load_catalog(args.catalog)
            findings.extend(check_catalog_prices(products, defaults.get('currency', 'EUR')))
    except (OSError, ValueError, CatalogError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    for severity, where, message in findings:
        print(f'{severity.upper()}: [{where}] {message}')
    if any(f[0] == 'error' for f in findings):
        print('COMPLIANCE_BLOCKED', file=sys.stderr)
        return 1
    print('COMPLIANCE_PREFLIGHT_OK (no legal review, no compliance certification)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
