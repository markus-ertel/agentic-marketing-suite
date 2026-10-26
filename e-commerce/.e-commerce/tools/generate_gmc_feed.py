#!/usr/bin/env python3
"""Local Google Merchant Center feed preflight and generator (e-commerce v0.1).

Check only:  generate_gmc_feed.py -i katalog.csv --check-only
Build XML:   generate_gmc_feed.py -i katalog.json -o feeds/gmc.xml
Build TSV:   generate_gmc_feed.py -i katalog.csv -o feeds/gmc.tsv --format tsv

Errors always block the build; --strict also blocks on warnings. Standard library only,
no network access. Building a file is NOT an upload: transferring it to Merchant Center
is an external action that needs an action-approval (.e-commerce/AKTIONEN.md).
This checks a documented subset of the Google product data specification; it is no
compliance certification.
"""
import argparse
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from field_types import load_schema, type_errors

GOOGLE_NS = 'http://base.google.com/ns/1.0'
ET.register_namespace('g', GOOGLE_NS)

MANDATORY_FIELDS = ('sku', 'title', 'description', 'link', 'image_link', 'availability', 'price')
AVAILABILITY = {'in_stock', 'out_of_stock', 'preorder', 'backorder'}
CONDITION = {'new', 'refurbished', 'used'}
GENDER = {'male', 'female', 'unisex'}
AGE_GROUP = {'newborn', 'infant', 'toddler', 'kids', 'adult'}
IDENTIFIER_EXISTS = {'yes', 'no'}
VARIANT_AXES = ('color', 'size', 'material', 'pattern', 'gender', 'age_group')
LIST_FIELDS = ('additional_image_link',)
# Exported in this order; catalog-only fields (lowest_price_30d, stock_quantity, ...) stay internal.
EXPORT_FIELDS = (
    'id', 'title', 'description', 'link', 'image_link', 'additional_image_link',
    'availability', 'availability_date', 'price', 'sale_price', 'sale_price_effective_date',
    'brand', 'gtin', 'mpn', 'identifier_exists', 'condition', 'google_product_category',
    'product_type', 'item_group_id', 'color', 'size', 'material', 'pattern', 'gender',
    'age_group', 'unit_pricing_measure', 'unit_pricing_base_measure', 'shipping_weight',
    'custom_label_0', 'custom_label_1', 'custom_label_2', 'custom_label_3', 'custom_label_4',
)
MAX_LENGTH = {'sku': 50, 'title': 150, 'description': 5000}
CURRENCY = re.compile(r'[A-Z]{3}')
MEASURE = re.compile(r'\d+(\.\d+)?\s?[a-zA-Z]+')


class CatalogError(Exception):
    pass


def _text(value):
    if value is None:
        return ''
    if isinstance(value, list):
        return '|'.join(str(v) for v in value)
    return str(value).strip()


def load_catalog(file_path):
    """Return (products, defaults) from a catalog JSON object/list or CSV file."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f'Katalogdatei nicht gefunden: {path}')
    defaults = {}
    if path.suffix.lower() == '.json':
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            defaults = {k: data[k] for k in ('currency', 'country', 'language') if k in data}
            if any(not isinstance(value, str) for value in defaults.values()):
                raise CatalogError('Katalog-Metadaten currency/country/language müssen Text sein')
            data = data.get('products')
        if not isinstance(data, list) or not all(isinstance(p, dict) for p in data):
            raise CatalogError('JSON-Katalog braucht eine Liste "products" aus Objekten')
        products = [dict(p) for p in data]
    elif path.suffix.lower() == '.csv':
        with path.open(encoding='utf-8-sig', newline='') as handle:
            products = [{k: v for k, v in row.items() if k} for row in csv.DictReader(handle)]
    else:
        raise CatalogError('Nicht unterstütztes Format; JSON oder CSV verwenden')
    for product in products:
        if not _text(product.get('sku')) and _text(product.get('id')):
            product['sku'] = product['id']
        for field in LIST_FIELDS:
            value = product.get(field)
            if isinstance(value, str):
                product[field] = [v.strip() for v in value.split('|') if v.strip()]
    return products, defaults


def parse_price(value, default_currency=None):
    """Return (Decimal amount, currency) from 29.9, '29.90' or '29.90 EUR'; raise ValueError."""
    text = _text(value)
    parts = text.split()
    if len(parts) == 2:
        amount, currency = parts
    elif len(parts) == 1:
        amount, currency = parts[0], default_currency
    else:
        raise ValueError('Preisformat "29.90" oder "29.90 EUR" erwartet')
    try:
        number = Decimal(amount.replace(',', '.'))
    except InvalidOperation:
        raise ValueError(f'kein Betrag: {amount}') from None
    if not number.is_finite() or number <= 0:
        raise ValueError('Betrag muss größer als 0 sein')
    if not currency or not CURRENCY.fullmatch(currency):
        raise ValueError('Währung als ISO-4217-Code angeben (z. B. EUR)')
    return number, currency


def format_price(amount, currency):
    return f'{amount.quantize(Decimal("0.01"))} {currency}'


def gtin_valid(value):
    digits = _text(value)
    if not digits.isdigit() or len(digits) not in (8, 12, 13, 14):
        return False
    body, check = digits[:-1], int(digits[-1])
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - total % 10) % 10 == check


def _datetime(value):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def _url_finding(product, field):
    try:
        parts = urlsplit(_text(product.get(field)))
    except ValueError:
        return 'error', f'{field}: ungültige URL'
    if parts.scheme not in ('http', 'https') or not parts.netloc:
        return 'error', f'{field}: absolute http(s)-URL erwartet'
    if parts.scheme == 'http':
        return 'warning', f'{field}: https empfohlen'
    return None


def validate_product(product, index, default_currency='EUR'):
    """Return a list of findings (severity, sku, message) for one catalog row."""
    invalid = type_errors(product, load_schema('product-catalog.schema.json')['properties']['products']['items'])
    if invalid:
        return [('error', f'Zeile {index + 1}', message) for message in invalid]
    sku = _text(product.get('sku')) or f'Zeile {index + 1}'
    findings = []

    def add(severity, message):
        findings.append((severity, sku, message))

    for field in MANDATORY_FIELDS:
        if not _text(product.get(field)):
            add('error', f"Fehlendes Pflichtfeld: '{field}'")
    for field, limit in MAX_LENGTH.items():
        if len(_text(product.get(field))) > limit:
            add('error', f'{field}: länger als {limit} Zeichen')
    for field in ('link', 'image_link'):
        if _text(product.get(field)):
            finding = _url_finding(product, field)
            if finding:
                add(*finding)
    for url in product.get('additional_image_link') or []:
        try:
            parts = urlsplit(url)
            valid = parts.scheme in ('http', 'https') and bool(parts.netloc)
        except ValueError:
            valid = False
        if not valid:
            add('error', 'additional_image_link: absolute http(s)-URL erwartet')

    availability = _text(product.get('availability'))
    if availability and availability not in AVAILABILITY:
        add('error', f'availability: ungültiger Wert {availability!r}')
    if availability in ('preorder', 'backorder'):
        if not _text(product.get('availability_date')):
            add('error', f'availability_date: bei {availability} erforderlich')
        elif _datetime(_text(product.get('availability_date'))) is None:
            add('error', 'availability_date: ISO-8601-Datum erwartet')
    stock = _text(product.get('stock_quantity'))
    if stock:
        if not stock.isdigit():
            add('error', 'stock_quantity: ganze Zahl ≥ 0 erwartet')
        elif availability == 'in_stock' and int(stock) == 0:
            add('error', 'availability in_stock widerspricht stock_quantity 0')
        elif availability == 'out_of_stock' and int(stock) > 0:
            add('warning', 'availability out_of_stock trotz positivem Bestand')

    currency = _text(product.get('currency')) or default_currency
    price = sale = None
    if _text(product.get('price')):
        try:
            price = parse_price(product['price'], currency)
        except ValueError as exc:
            add('error', f'price: {exc}')
    if _text(product.get('sale_price')):
        try:
            sale = parse_price(product['sale_price'], currency)
        except ValueError as exc:
            add('error', f'sale_price: {exc}')
    if price and sale:
        findings.extend((s, sku, m) for s, m in check_reference_price(
            price, sale, product.get('lowest_price_30d'), product.get('omnibus_exception')))
        if not _text(product.get('sale_price_effective_date')):
            add('warning', 'sale_price_effective_date fehlt; Aktionszeitraum mit Shop synchron halten')
    effective = _text(product.get('sale_price_effective_date'))
    if effective:
        bounds = effective.split('/')
        if len(bounds) != 2 or any(_datetime(b) is None for b in bounds):
            add('error', 'sale_price_effective_date: "Start/Ende" im ISO-8601-Format erwartet')

    identifier_exists = _text(product.get('identifier_exists')).lower()
    if identifier_exists and identifier_exists not in IDENTIFIER_EXISTS:
        add('error', 'identifier_exists: yes oder no erwartet')
    gtin, mpn, brand = (_text(product.get(k)) for k in ('gtin', 'mpn', 'brand'))
    if gtin and not gtin_valid(gtin):
        add('error', 'gtin: ungültige Länge oder Prüfziffer (GTIN nie erfinden)')
    if identifier_exists != 'no':
        if not brand:
            add('error', "Fehlendes Feld: 'brand' (oder identifier_exists = no, falls es keine Marke gibt)")
        if not (gtin or mpn):
            add('error', "Ungültige Identifikatoren: 'gtin' oder 'brand' + 'mpn' erforderlich, sonst identifier_exists = no")
    elif gtin:
        add('warning', 'identifier_exists = no, obwohl eine GTIN angegeben ist')
    if not _text(product.get('google_product_category')):
        add('warning', 'google_product_category fehlt; Google ordnet sonst automatisch zu')

    for field, allowed in (('condition', CONDITION), ('gender', GENDER), ('age_group', AGE_GROUP)):
        value = _text(product.get(field))
        if value and value not in allowed:
            add('error', f'{field}: ungültiger Wert {value!r}')
    for field in ('unit_pricing_measure', 'unit_pricing_base_measure', 'shipping_weight'):
        value = _text(product.get(field))
        if value and not MEASURE.fullmatch(value):
            add('error', f'{field}: Format "<Zahl> <Einheit>" erwartet')
    return findings


def check_reference_price(price, sale, lowest_30d, exception=None):
    """Omnibus rule: the struck-through price must be the lowest price of the prior 30 days."""
    amount, currency = price
    if sale[1] != currency:
        return [('error', 'sale_price und price in unterschiedlicher Währung')]
    if sale[0] >= amount:
        return [('error', 'sale_price muss kleiner als price sein')]
    if not _text(lowest_30d):
        return [('error', 'PANGV/Omnibus: sale_price ohne lowest_price_30d (niedrigster Preis der letzten 30 Tage)')]
    try:
        lowest, lowest_currency = parse_price(lowest_30d, currency)
        if lowest_currency != currency:
            return [('error', 'lowest_price_30d und price in unterschiedlicher Währung')]
    except ValueError as exc:
        return [('error', f'lowest_price_30d: {exc}')]
    if lowest != amount:
        severity = 'warning' if _text(exception) else 'error'
        return [(severity, f'PANGV/Omnibus: Streichpreis {format_price(amount, currency)} ist nicht der '
                           f'niedrigste 30-Tage-Preis {format_price(lowest, currency)}'
                           + (f' (Ausnahme dokumentiert: {_text(exception)})' if severity == 'warning' else ''))]
    return []


def validate_catalog(products, default_currency='EUR'):
    findings = []
    seen = {}
    groups = {}
    if not isinstance(products, list):
        return [('error', 'catalog', 'Produktliste erwartet')]
    for index, product in enumerate(products):
        findings.extend(validate_product(product, index, default_currency))
        if not isinstance(product, dict):
            continue
        sku = _text(product.get('sku'))
        if sku:
            if sku in seen:
                findings.append(('error', sku, f'sku doppelt (Zeilen {seen[sku] + 1} und {index + 1})'))
            seen.setdefault(sku, index)
        group = _text(product.get('item_group_id'))
        if group:
            groups.setdefault(group, []).append(product)
    for group, members in sorted(groups.items()):
        axes = [tuple(_text(p.get(a)) for a in VARIANT_AXES) for p in members]
        if not any(any(a) for a in axes):
            findings.append(('warning', group, 'item_group_id ohne Variantenattribut (color, size, ...)'))
        elif len(set(axes)) < len(axes):
            findings.append(('error', group, 'Varianten einer item_group_id unterscheiden sich nicht in color/size/material/pattern/gender/age_group'))
    return findings


def _export_values(product, default_currency):
    currency = _text(product.get('currency')) or default_currency
    values = {}
    for field in EXPORT_FIELDS:
        source = 'sku' if field == 'id' else field
        value = product.get(source)
        if field in ('price', 'sale_price') and _text(value):
            value = format_price(*parse_price(value, currency))
        if field in LIST_FIELDS:
            value = [v for v in (value or []) if v]
            if value:
                values[field] = value
        elif _text(value):
            values[field] = _text(value)
    return values


def build_gmc_xml(products, title='Produktfeed', link='', description='', default_currency='EUR'):
    """Return an RSS 2.0 ElementTree with Google namespace attributes."""
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = title
    ET.SubElement(channel, 'link').text = link
    ET.SubElement(channel, 'description').text = description or 'Lokal erzeugter Merchant-Center-Feed'
    for product in products:
        item = ET.SubElement(channel, 'item')
        for field, value in _export_values(product, default_currency).items():
            for single in (value if isinstance(value, list) else [value]):
                ET.SubElement(item, f'{{{GOOGLE_NS}}}{field}').text = single
    return ET.ElementTree(rss)


def build_gmc_tsv(products, default_currency='EUR'):
    rows = [_export_values(p, default_currency) for p in products]
    columns = [f for f in EXPORT_FIELDS if any(f in r for r in rows)]
    lines = ['\t'.join(columns)]
    for row in rows:
        cells = []
        for column in columns:
            value = row.get(column, '')
            value = ','.join(value) if isinstance(value, list) else value
            cells.append(re.sub(r'[\t\r\n]+', ' ', value))
        lines.append('\t'.join(cells))
    return '\n'.join(lines) + '\n'


def write_feed(products, out, fmt, title='Produktfeed', link='', default_currency='EUR'):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if fmt == 'xml':
        tree = build_gmc_xml(products, title=title, link=link, default_currency=default_currency)
        if hasattr(ET, 'indent'):
            ET.indent(tree)
        tree.write(out, encoding='utf-8', xml_declaration=True)
    else:
        out.write_text(build_gmc_tsv(products, default_currency), encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Merchant-Center-Feed lokal prüfen und erzeugen (kein Upload).')
    parser.add_argument('--input', '-i', required=True, type=Path, help='Katalog (.csv oder .json)')
    parser.add_argument('--output', '-o', type=Path, help='Zieldatei des Feeds')
    parser.add_argument('--format', choices=('xml', 'tsv'), help='Standard: aus Dateiendung, sonst xml')
    parser.add_argument('--check-only', action='store_true', help='nur prüfen, keine Datei schreiben')
    parser.add_argument('--strict', action='store_true', help='auch Warnungen blockieren')
    parser.add_argument('--force', action='store_true', help='vorhandene Zieldatei überschreiben')
    parser.add_argument('--title', default='Produktfeed')
    parser.add_argument('--link', default='', help='Shop-URL für den RSS-Kanal')
    args = parser.parse_args(argv)
    if not args.check_only and not args.output:
        parser.error('--output oder --check-only angeben')
    try:
        products, defaults = load_catalog(args.input)
    except (OSError, ValueError, CatalogError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    currency = defaults.get('currency', 'EUR')
    findings = validate_catalog(products, currency)
    for severity, sku, message in findings:
        print(f'{severity.upper()}: [{sku}] {message}')
    errors = sum(1 for f in findings if f[0] == 'error')
    warnings = len(findings) - errors
    print(f'{len(products)} Artikel, {errors} Fehler, {warnings} Warnungen')
    if errors or (args.strict and warnings):
        print('FEED_BLOCKED: kein Feed erzeugt', file=sys.stderr)
        return 1
    if args.check_only:
        print('FEED_PREFLIGHT_OK (no upload, no compliance certification)')
        return 0
    if args.output.exists() and not args.force:
        print(f'FAIL: {args.output} existiert; neue Version anlegen oder --force', file=sys.stderr)
        return 1
    fmt = args.format or ('tsv' if args.output.suffix.lower() in ('.tsv', '.txt') else 'xml')
    write_feed(products, args.output, fmt, title=args.title, link=args.link, default_currency=currency)
    print(f'FEED_WRITTEN {args.output} ({fmt}, {len(products)} Artikel; no upload, no compliance certification)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
