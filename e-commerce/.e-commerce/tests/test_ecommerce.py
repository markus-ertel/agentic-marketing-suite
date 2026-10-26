"""Offline tests for the e-commerce feed generator and compliance preflight (standard library only)."""
import contextlib
import copy
import csv
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest
import xml.etree.ElementTree as ET

BASE = pathlib.Path(__file__).resolve().parents[1]
TOOLS = BASE / 'tools'
EXAMPLES = BASE / 'beispiele'
FORMATS = BASE / 'formate'
SUITE_VALIDATOR = BASE.parents[1] / '.suite' / 'tools' / 'validate_records.py'


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


feed = _load('generate_gmc_feed', TOOLS / 'generate_gmc_feed.py')
compliance = _load('validate_compliance', TOOLS / 'validate_compliance.py')


def errors(findings):
    return [f[-1] for f in findings if f[0] == 'error']


def warnings(findings):
    return [f[-1] for f in findings if f[0] == 'warning']


def quiet(func, *args):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return func(*args)


VALID_PRODUCT = {
    'sku': 'PROD-100',
    'title': 'Demo-Anzuchtset',
    'description': 'Fiktives Anzuchtset für Tests.',
    'link': 'https://shop.example.com/products/anzuchtset',
    'image_link': 'https://shop.example.com/images/anzuchtset.jpg',
    'availability': 'in_stock',
    'price': '24.90',
    'currency': 'EUR',
    'gtin': '2000000000015',
    'brand': 'Musterhof',
    'mpn': 'MH-ANZ-100',
    'google_product_category': 'Home & Garden > Plants',
}


class TestLoadCatalog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = pathlib.Path(self.tmp.name)

    def test_json_list(self):
        path = self.dir / 'catalog.json'
        path.write_text(json.dumps([VALID_PRODUCT]), encoding='utf-8')
        products, _ = feed.load_catalog(path)
        self.assertEqual(products[0]['sku'], 'PROD-100')

    def test_json_wrapped_with_defaults(self):
        path = self.dir / 'catalog.json'
        path.write_text(json.dumps({'currency': 'CHF', 'products': [VALID_PRODUCT]}), encoding='utf-8')
        products, defaults = feed.load_catalog(path)
        self.assertEqual(len(products), 1)
        self.assertEqual(defaults['currency'], 'CHF')

    def test_csv_with_bom_and_list_field(self):
        path = self.dir / 'catalog.csv'
        row = dict(VALID_PRODUCT, additional_image_link='https://a.example/1.jpg|https://a.example/2.jpg')
        with path.open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
        products, _ = feed.load_catalog(path)
        self.assertEqual(products[0]['sku'], 'PROD-100')
        self.assertEqual(len(products[0]['additional_image_link']), 2)

    def test_id_is_alias_for_sku(self):
        path = self.dir / 'catalog.json'
        row = dict(VALID_PRODUCT)
        row['id'] = row.pop('sku')
        path.write_text(json.dumps([row]), encoding='utf-8')
        self.assertEqual(feed.load_catalog(path)[0][0]['sku'], 'PROD-100')

    def test_not_found(self):
        with self.assertRaises(FileNotFoundError):
            feed.load_catalog(self.dir / 'nicht_existent.json')

    def test_unsupported_format(self):
        path = self.dir / 'catalog.xlsx'
        path.write_bytes(b'')
        with self.assertRaises(feed.CatalogError):
            feed.load_catalog(path)


class TestValidateProduct(unittest.TestCase):
    def setUp(self):
        self.product = copy.deepcopy(VALID_PRODUCT)

    def test_valid(self):
        self.assertEqual(feed.validate_product(self.product, 0), [])

    def test_missing_mandatory(self):
        self.product['price'] = ''
        self.assertIn("Fehlendes Pflichtfeld: 'price'", errors(feed.validate_product(self.product, 0)))

    def test_missing_identifiers(self):
        del self.product['gtin'], self.product['mpn']
        self.assertTrue(any('Ungültige Identifikatoren' in e for e in errors(feed.validate_product(self.product, 0))))

    def test_brand_and_mpn_without_gtin(self):
        del self.product['gtin']
        self.assertEqual(errors(feed.validate_product(self.product, 0)), [])

    def test_identifier_exists_no(self):
        for key in ('gtin', 'mpn', 'brand'):
            del self.product[key]
        self.product['identifier_exists'] = 'no'
        self.assertEqual(errors(feed.validate_product(self.product, 0)), [])

    def test_gtin_check_digit(self):
        self.product['gtin'] = '2000000000016'
        self.assertTrue(any('Prüfziffer' in e for e in errors(feed.validate_product(self.product, 0))))

    def test_invalid_availability_and_url(self):
        self.product['availability'] = 'available'
        self.product['link'] = '/relative'
        found = errors(feed.validate_product(self.product, 0))
        self.assertTrue(any(e.startswith('availability') for e in found))
        self.assertTrue(any(e.startswith('link') for e in found))

    def test_preorder_needs_date(self):
        self.product['availability'] = 'preorder'
        self.assertTrue(any('availability_date' in e for e in errors(feed.validate_product(self.product, 0))))
        self.product['availability_date'] = '2026-12-01T00:00:00+01:00'
        self.assertEqual(errors(feed.validate_product(self.product, 0)), [])

    def test_stock_contradiction(self):
        self.product['stock_quantity'] = '0'
        self.assertTrue(any('stock_quantity 0' in e for e in errors(feed.validate_product(self.product, 0))))

    def test_title_too_long(self):
        self.product['title'] = 'x' * 151
        self.assertTrue(any('title' in e for e in errors(feed.validate_product(self.product, 0))))

    def test_price_format(self):
        for bad in ('0', '-1', 'gratis', '10 euro'):
            self.product['price'] = bad
            with self.subTest(price=bad):
                self.assertTrue(any(e.startswith('price') for e in errors(feed.validate_product(self.product, 0))))


class TestReferencePrice(unittest.TestCase):
    """Omnibus/PAngV: the struck-through price must be the lowest price of the prior 30 days."""

    def setUp(self):
        self.product = dict(VALID_PRODUCT, sale_price='19.90',
                            sale_price_effective_date='2026-11-01T00:00:00+01:00/2026-11-15T23:59:59+01:00')

    def test_sale_without_lowest_price(self):
        self.assertTrue(any('lowest_price_30d' in e for e in errors(feed.validate_product(self.product, 0))))

    def test_reference_equals_lowest(self):
        self.product['lowest_price_30d'] = '24.90'
        self.assertEqual(feed.validate_product(self.product, 0), [])

    def test_reference_above_lowest_is_blocked(self):
        # 24.90 struck through while the item sold for 22.90 within 30 days
        self.product['lowest_price_30d'] = '22.90'
        self.assertTrue(any('niedrigste 30-Tage-Preis' in e for e in errors(feed.validate_product(self.product, 0))))

    def test_documented_exception_downgrades_to_warning(self):
        self.product['lowest_price_30d'] = '22.90'
        self.product['omnibus_exception'] = 'schrittweise Ermäßigung, Rechtsprüfung R-12'
        findings = feed.validate_product(self.product, 0)
        self.assertEqual(errors(findings), [])
        self.assertTrue(warnings(findings))

    def test_sale_not_lower(self):
        self.product['sale_price'] = '24.90'
        self.assertIn('sale_price muss kleiner als price sein', errors(feed.validate_product(self.product, 0)))

    def test_missing_effective_date_warns(self):
        del self.product['sale_price_effective_date']
        self.product['lowest_price_30d'] = '24.90'
        self.assertTrue(warnings(feed.validate_product(self.product, 0)))


class TestCatalog(unittest.TestCase):
    def variant(self, sku, color, size):
        return dict(VALID_PRODUCT, sku=sku, item_group_id='G1', color=color, size=size)

    def test_duplicate_sku(self):
        found = errors(feed.validate_catalog([dict(VALID_PRODUCT), dict(VALID_PRODUCT)]))
        self.assertTrue(any('doppelt' in e for e in found))

    def test_variants_must_differ(self):
        rows = [self.variant('A', 'rot', 'M'), self.variant('B', 'rot', 'M')]
        self.assertTrue(any('unterscheiden sich nicht' in e for e in errors(feed.validate_catalog(rows))))
        rows[1]['size'] = 'L'
        self.assertEqual(errors(feed.validate_catalog(rows)), [])

    def test_demo_catalogs_are_clean(self):
        for name in ('katalog-demo.csv', 'katalog-demo.json'):
            with self.subTest(name=name):
                products, defaults = feed.load_catalog(EXAMPLES / name)
                self.assertEqual(feed.validate_catalog(products, defaults.get('currency', 'EUR')), [])


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = pathlib.Path(self.tmp.name)
        self.product = dict(VALID_PRODUCT, sale_price='19.9', lowest_price_30d='24.90', stock_quantity='3',
                            additional_image_link=['https://shop.example.com/a.jpg', 'https://shop.example.com/b.jpg'])

    def test_xml_structure(self):
        root = feed.build_gmc_xml([self.product], title='Test Shop Feed').getroot()
        self.assertEqual(root.tag, 'rss')
        self.assertEqual(root.attrib.get('version'), '2.0')
        channel = root.find('channel')
        self.assertEqual(channel.find('title').text, 'Test Shop Feed')
        item = channel.findall('item')[0]
        g = '{%s}' % feed.GOOGLE_NS
        self.assertEqual(item.find(g + 'id').text, 'PROD-100')
        self.assertEqual(item.find(g + 'gtin').text, '2000000000015')
        self.assertEqual(item.find(g + 'price').text, '24.90 EUR')
        self.assertEqual(item.find(g + 'sale_price').text, '19.90 EUR')
        self.assertEqual(len(item.findall(g + 'additional_image_link')), 2)
        # catalog-only fields are never exported
        for internal in ('lowest_price_30d', 'stock_quantity', 'sku', 'currency'):
            self.assertIsNone(item.find(g + internal), internal)

    def test_written_xml_parses_with_single_namespace(self):
        out = self.dir / 'feed.xml'
        feed.write_feed([self.product], out, 'xml')
        text = out.read_text(encoding='utf-8')
        self.assertEqual(text.count('xmlns:g='), 1)
        ET.parse(out)

    def test_tsv(self):
        lines = feed.build_gmc_tsv([dict(self.product, description='Zeile 1\nZeile\t2')]).splitlines()
        header = lines[0].split('\t')
        self.assertEqual(header[0], 'id')
        self.assertNotIn('lowest_price_30d', header)
        cells = dict(zip(header, lines[1].split('\t')))
        self.assertEqual(cells['description'], 'Zeile 1 Zeile 2')
        self.assertEqual(cells['additional_image_link'], 'https://shop.example.com/a.jpg,https://shop.example.com/b.jpg')

    def test_cli_blocks_on_errors(self):
        catalog = self.dir / 'k.json'
        catalog.write_text(json.dumps([dict(VALID_PRODUCT, price='')]), encoding='utf-8')
        out = self.dir / 'feed.xml'
        self.assertEqual(quiet(feed.main, ['-i', str(catalog), '-o', str(out)]), 1)
        self.assertFalse(out.exists())

    def test_cli_strict_blocks_on_warnings(self):
        catalog = self.dir / 'k.json'
        catalog.write_text(json.dumps([dict(VALID_PRODUCT, google_product_category='')]), encoding='utf-8')
        self.assertEqual(quiet(feed.main, ['-i', str(catalog), '--check-only']), 0)
        self.assertEqual(quiet(feed.main, ['-i', str(catalog), '--check-only', '--strict']), 1)

    def test_cli_does_not_overwrite(self):
        out = self.dir / 'feed.tsv'
        args = ['-i', str(EXAMPLES / 'katalog-demo.csv'), '-o', str(out)]
        self.assertEqual(quiet(feed.main, args), 0)
        self.assertTrue(out.read_text(encoding='utf-8').startswith('id\t'))
        self.assertEqual(quiet(feed.main, args), 1)
        self.assertEqual(quiet(feed.main, args + ['--force']), 0)


class TestFunnel(unittest.TestCase):
    def setUp(self):
        self.funnel = json.loads((EXAMPLES / 'funnel-demo.json').read_text(encoding='utf-8'))

    def step(self, sid):
        return next(s for s in self.funnel['steps'] if s['id'] == sid)

    def test_demo_is_clean(self):
        self.assertEqual(compliance.validate_funnel(self.funnel), [])

    def test_preselected_bump_blocked(self):
        self.step('bump-beutel')['preselected'] = True
        self.assertTrue(any('preselected' in e for e in errors(compliance.validate_funnel(self.funnel))))

    def test_missing_consent_and_decline(self):
        bump = self.step('bump-beutel')
        del bump['requires_explicit_consent'], bump['decline_label']
        found = errors(compliance.validate_funnel(self.funnel))
        self.assertTrue(any('requires_explicit_consent' in e for e in found))
        self.assertTrue(any('decline_label' in e for e in found))

    def test_stored_credential_needs_agreement(self):
        upsell = self.step('upsell-zweites-shirt')
        upsell['payment_mode'] = 'mit_agreed'
        self.assertTrue(any('payment_agreement_ref' in e for e in errors(compliance.validate_funnel(self.funnel))))
        upsell['payment_agreement_ref'] = 'vereinbarung-v1.md'
        findings = compliance.validate_funnel(self.funnel)
        self.assertEqual(errors(findings), [])
        self.assertTrue(any('Zahlungsdienst' in w for w in warnings(findings)))

    def test_upsell_needs_payment_mode_and_button(self):
        upsell = self.step('upsell-zweites-shirt')
        del upsell['payment_mode'], upsell['button_label']
        found = errors(compliance.validate_funnel(self.funnel))
        self.assertTrue(any('payment_mode' in e for e in found))
        self.assertTrue(any('button_label' in e for e in found))

    def test_auto_accept_blocked(self):
        self.step('upsell-zweites-shirt')['auto_accept_after_seconds'] = 600
        self.assertTrue(any('automatische Annahme' in e for e in errors(compliance.validate_funnel(self.funnel))))

    def test_compare_at_price_omnibus(self):
        self.funnel['offers'][0]['lowest_price_30d'] = '8.90 EUR'
        self.assertTrue(any('30-Tage' in e for e in errors(compliance.validate_funnel(self.funnel))))

    def test_urgency_needs_truthful_basis(self):
        self.funnel['offers'][0]['urgency'] = {'type': 'countdown', 'resets_on_reload': True}
        found = errors(compliance.validate_funnel(self.funnel))
        self.assertTrue(any('truthful_basis_ref' in e for e in found))
        self.assertTrue(any('Neuladen' in e for e in found))

    def test_live_needs_approval_and_legal_review(self):
        self.funnel['status'] = 'live'
        found = errors(compliance.validate_funnel(self.funnel))
        self.assertTrue(any('approval_ref' in e for e in found))
        self.assertTrue(any('legal_review_ref' in e for e in found))

    def test_unknown_step_reference(self):
        self.step('kasse')['next'] = 'gibt-es-nicht'
        self.assertTrue(any('unbekannten Schritt' in e for e in errors(compliance.validate_funnel(self.funnel))))

    def test_experiment_design(self):
        self.funnel['experiment']['variants'] = ['A']
        del self.funnel['experiment']['stopping_rule']
        self.funnel['experiment']['varies_price'] = True
        found = errors(compliance.validate_funnel(self.funnel))
        self.assertEqual(len([e for e in found if 'Varianten' in e or 'stopping_rule' in e or 'Preistest' in e]), 3)

    def test_cli_catalog_and_offers(self):
        args = ['--offers', str(EXAMPLES / 'funnel-demo.json'), '--catalog', str(EXAMPLES / 'katalog-demo.csv')]
        self.assertEqual(quiet(compliance.main, args), 0)


@unittest.skipUnless(SUITE_VALIDATOR.is_file(), 'Suite-Validator nicht vorhanden (Standalone-Betrieb)')
class TestSchemas(unittest.TestCase):
    """Demo data conforms to the module schemas, checked with the bounded suite checker."""

    @classmethod
    def setUpClass(cls):
        cls.records = _load('validate_records', SUITE_VALIDATOR)

    def conform(self, schema_name, record):
        schema = json.loads((FORMATS / schema_name).read_text(encoding='utf-8'))
        found = []
        self.records._field('record', record, schema, found)
        return found

    def test_demo_records(self):
        for schema_name, example in (('product-catalog.schema.json', 'katalog-demo.json'),
                                     ('funnel-offer.schema.json', 'funnel-demo.json'),
                                     ('gmc-feed.schema.json', 'feed-lauf-demo.json')):
            with self.subTest(example=example):
                record = json.loads((EXAMPLES / example).read_text(encoding='utf-8'))
                self.assertEqual(self.conform(schema_name, record), [])

    def test_csv_columns_are_schema_fields(self):
        schema = json.loads((FORMATS / 'product-catalog.schema.json').read_text(encoding='utf-8'))
        fields = set(schema['properties']['products']['items']['properties'])
        with (EXAMPLES / 'katalog-demo.csv').open(encoding='utf-8') as handle:
            self.assertLessEqual(set(next(csv.reader(handle))), fields)

    def test_schema_rejects_unknown_field(self):
        record = json.loads((EXAMPLES / 'katalog-demo.json').read_text(encoding='utf-8'))
        record['products'][0]['card_number'] = '4111'
        self.assertTrue(self.conform('product-catalog.schema.json', record))


class TestMalformedInput(unittest.TestCase):
    def test_funnel_rejects_invalid_nested_types(self):
        template = json.loads((EXAMPLES / 'funnel-demo.json').read_text(encoding='utf-8'))
        for changes in ({'steps': {}}, {'offers': 'invalid'}, {'status': []}, {'experiment': []}, {'version': True}, {'version': 0}, {'currency': 'euro'}):
            with self.subTest(changes=changes):
                self.assertTrue(errors(compliance.validate_funnel(dict(template, **changes))))
        for key in ('steps', 'offers'):
            invalid = copy.deepcopy(template)
            invalid[key][0]['id'] = []
            self.assertTrue(errors(compliance.validate_funnel(invalid)))

    def test_catalog_rejects_invalid_image_types_and_rows(self):
        for images in ([42], {'url': 'https://example.com/image.jpg'}, ['https://[invalid'], ['https:relative']):
            self.assertTrue(errors(feed.validate_product(dict(VALID_PRODUCT, additional_image_link=images), 0)))
        self.assertTrue(errors(feed.validate_catalog([None])))
        self.assertTrue(errors(feed.validate_product(dict(VALID_PRODUCT, link='https://[invalid'), 0)))

    def test_reference_price_requires_same_currency(self):
        product = dict(VALID_PRODUCT, sale_price='19.90 EUR', lowest_price_30d='24.90 USD')
        self.assertTrue(any('Währung' in e for e in errors(feed.validate_product(product, 0))))


class TestOffline(unittest.TestCase):
    def test_tools_have_no_network_imports(self):
        for path in TOOLS.glob('*.py'):
            text = path.read_text(encoding='utf-8')
            for banned in ('urllib.request', 'http.client', 'import socket', 'requests', 'subprocess'):
                with self.subTest(tool=path.name, banned=banned):
                    self.assertNotIn(banned, text)


if __name__ == '__main__':
    unittest.main()
