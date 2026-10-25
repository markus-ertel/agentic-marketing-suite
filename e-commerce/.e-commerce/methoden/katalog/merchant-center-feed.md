# Google-Merchant-Center-Feed und Attribut-Mapping

**Methoden-ID:** `katalog/merchant-center-feed` · **Typ:** fachliche Arbeitsanleitung · **Version:** 0.1

## Zweck
Aus dem führenden Katalog einen regelkonformen Merchant-Center-Feed (XML oder TSV) erzeugen und das Mapping zwischen Shop-Feldern und Google-Attributen dokumentieren, bevor Artikel abgelehnt oder Konten gesperrt werden.

## Eingaben und Umgang mit Lücken
Ziel/Auftrag, Sortiment, Zielmärkte, Shop-System, vorhandene Daten und Ressourcen soweit für diese Methode nötig heranziehen. Bestehende, berechtigt zugängliche Projektartefakte vor neuen Fragen nutzen. Fehlende Angaben markieren; reversible Hypothesen formulieren. Nur nachfragen, wenn das Ergebnis sonst riskant oder eine verbindliche Entscheidung unmöglich wäre.

## Vorgehen
1. Mapping-Tabelle Shop-Feld → Google-Attribut anlegen (Pflicht: `id`, `title`, `description`, `link`, `image_link`, `availability`, `price`; je nach Produkt `brand`, `gtin`/`mpn`, `condition`, `item_group_id` und Variantenattribute, `availability_date`, `sale_price`, `unit_pricing_measure`).
2. Google-Produktkategorie und eigene `product_type` festlegen; `custom_label_0–4` mit `../advertising/` für Kampagnensteuerung abstimmen (Marge, Saison, Bestseller), ohne personenbezogene Daten.
3. Lokal prüfen: `python3 .e-commerce/tools/generate_gmc_feed.py -i <katalog> --check-only`; Fehler blockieren, Warnungen dokumentieren.
4. Feed erzeugen: `python3 .e-commerce/tools/generate_gmc_feed.py -i <katalog> -o feeds/<datei>.xml`; SHA-256 der Datei festhalten.
5. Übertragung (Upload, geplanter Abruf, Merchant API) ist eine externe Aktion nach `.e-commerce/AKTIONEN.md` (Ziel `ecommerce:feed_publish`).
6. Nach Übertragung Artikelstatus und Diagnosen aus dem Merchant Center auswerten und als Feed-Status nach `../.suite/INTERFACES.md` zurückmelden.

## Ergebnis für den Menschen
**Feed-Datei, Mapping-Tabelle und Prüfprotokoll** (inkl. SHA-256). Beginne mit einer klaren Empfehlung bzw. einem verwendbaren Entwurf. Kennzeichne Tatsachen, Hypothesen und ausstehende Freigaben.

## Grenzen
Das Werkzeug prüft eine Auswahl dokumentierter Attributregeln, nicht die vollständige und sich ändernde Google-Spezifikation, keine Richtlinien zu Produktinhalten und keine Website-Prüfung durch Google. Vor Umsetzung die aktuelle Produktdatenspezifikation lesen (`.e-commerce/QUELLEN.md`).

## Anwendungsfälle
- **Positiv:** Ein Shop mit 800 Varianten liefert regelmäßig Ablehnungen wegen fehlender GTIN: Mapping korrigieren, Werkzeug-Check vor jeder Übertragung, Diagnosen nach Abruf auswerten.
- **Negativ:** „Lade den Feed hoch, die Warnungen sind egal“, während das Werkzeug Fehler meldet: kein Build und keine Übertragung; Fehler beheben oder Artikel ausschließen.

## Qualitätssicherung / Red Flags
- Merchant API und Google Ads API nicht verwechseln; Kampagnen gehören zu `../advertising/`.
- Feedpreis = Preis auf der Produktseite = Preis im Checkout.
- Keine erfundenen Preise, Bestände, Kennzahlen, Benchmarks oder Plattformfähigkeiten.
- Externe Änderungen nur gemäß `.e-commerce/AKTIONEN.md`; Rechtsfragen nach `.e-commerce/RECHT.md`.

## Übergaben und Ablage
Ergebnis außerhalb `.e-commerce/` als Markdown-/CSV-/JSON-Artefakt speichern. Weiterführende Methoden selektiv aus `.e-commerce/METHODEN.md` wählen. Bei tatsächlichen Änderungen STATE/LOG/HISTORY sachgerecht aktualisieren.
