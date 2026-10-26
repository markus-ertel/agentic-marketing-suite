# FORMATE — offene Datenformate und lokale Werkzeuge

## Produktkatalog (`catalog-product`)
- Schema: `.e-commerce/formate/product-catalog.schema.json` (JSON); CSV verwendet **dieselben Spaltennamen**, UTF-8, Kopfzeile, Listen (z. B. `additional_image_link`) mit `|` getrennt.
- **Eine Zeile je kaufbarer Variante.** `sku` ist stabil und eindeutig und wird als `g:id` exportiert (`id` wird als Alias akzeptiert); `item_group_id` verbindet Varianten.
- Preise als Text `"29.90"` oder `"29.90 EUR"`; Währung sonst aus `currency` der Zeile bzw. des Katalogs.
- Interne Felder werden **nie exportiert**: `lowest_price_30d`, `omnibus_exception`, `stock_quantity`, `currency`, `source_ref`, `notes`.
- Beispiele (fiktiv): `.e-commerce/beispiele/katalog-demo.csv`, `.e-commerce/beispiele/katalog-demo.json`. Die Demo-GTINs stammen aus dem GS1-Bereich 20–29 für internen Gebrauch und bezeichnen keine echten Artikel.

## Funnel- und Angebotsdefinition (`funnel-offer`)
- Schema: `.e-commerce/formate/funnel-offer.schema.json`. Schritte (`product`, `checkout`, `order_bump`, `upsell`, `downsell`, `thank_you`, …), Angebote, optional ein Experiment.
- Schutzschalter: `preselected: false`, `requires_explicit_consent: true`, `decline_label`, `button_label`, `payment_mode` mit `payment_agreement_ref`, `urgency.truthful_basis_ref`.
- Spezifikation für ein externes Shop-System, **keine** ausführbare Konfiguration. Beispiel: `.e-commerce/beispiele/funnel-demo.json`.

## Feed-Protokoll (`shopping-listing`)
- Schema: `.e-commerce/formate/gmc-feed.schema.json`: Katalogreferenz, Feed-Datei mit SHA-256, Preflight-Status `valid | warning | rejected`, Übertragung und Merchant-Center-Rückmeldung. Beispiel: `.e-commerce/beispiele/feed-lauf-demo.json`.

## Werkzeuge (nur Standardbibliothek, Python 3.9+, keine Netzwerkzugriffe)
Aufruf vom Modulordner `e-commerce/` aus:

```sh
python3 .e-commerce/tools/generate_gmc_feed.py -i katalog/katalog.csv --check-only
python3 .e-commerce/tools/generate_gmc_feed.py -i katalog/katalog.csv -o feeds/gmc-AT-2026-11-01.xml
python3 .e-commerce/tools/generate_gmc_feed.py -i katalog/katalog.json -o feeds/gmc-AT-2026-11-01.tsv --strict
python3 .e-commerce/tools/validate_compliance.py --offers funnels/herbst/funnel.json --catalog katalog/katalog.csv
python3 -m unittest discover -s .e-commerce/tests -v
```

- `generate_gmc_feed.py` prüft Pflichtattribute, URLs, Verfügbarkeit, Preisformat, GTIN-Prüfziffer, Marke/Identifikatoren, Varianten, Bestand und die 30-Tage-Regel; **Fehler blockieren immer**, `--strict` blockiert auch Warnungen. Vorhandene Dateien werden nur mit `--force` überschrieben.
- `validate_compliance.py` prüft Funnel-Schutzschalter und Streichpreise im Katalog.
- Beide Werkzeuge weisen ungültige verschachtelte Eingabetypen verständlich ab. Referenzpreise werden nur innerhalb derselben Währung verglichen.
- Beide Werkzeuge prüfen eine dokumentierte Auswahl von Regeln. Ein erfolgreicher Lauf ist **kein** Upload, keine Google-Annahme und keine Rechtsfreigabe.
- Erzeugte Feeds liegen in `e-commerce/feeds/` (Schreib-Owner `e-commerce/`); `../advertising/` referenziert sie, statt sie zu kopieren oder zu ändern.
