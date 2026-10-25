# METHODEN — Verzeichnis der E-Commerce-Fachbibliothek

**Version:** 0.1 · **8 Methodenanleitungen in 5 Bereichen.** Jede Methode enthält Zweck, Vorgehen, Grenzen sowie einen positiven und einen negativen Anwendungsfall.

## Auswahlregel
Aus dem echten Auftrag 1–4 passende Methoden wählen. Nach `AGENT.md` niemals die ganze Bibliothek lesen. Rechtsfragen zusätzlich über `RECHT.md`, externe Änderungen über `AKTIONEN.md`.

## strategie/ (1)
- [`shop-system-auswahl`](methoden/strategie/shop-system-auswahl.md) — **Shop-System-Auswahl**: Shopify, WooCommerce, Shopware oder Eigenbau passend zu Sortiment, Betrieb und Kosten.

## katalog/ (2)
- [`produktdaten-varianten`](methoden/katalog/produktdaten-varianten.md) — **Produktdaten und Varianten**: führender Katalog, stabile IDs, Variantenachsen, Identifikatoren.
- [`merchant-center-feed`](methoden/katalog/merchant-center-feed.md) — **Google-Merchant-Center-Feed und Attribut-Mapping**: lokaler Preflight, XML/TSV, freigegebene Übertragung.

## conversion/ (3)
- [`checkout-optimierung`](methoden/conversion/checkout-optimierung.md) — **Checkout-Optimierung**: Abbruchursachen, Pflichtinformationen, Zahlarten.
- [`order-bumps`](methoden/conversion/order-bumps.md) — **Order Bumps**: Zusatzangebot vor der Bestellung, nie vorausgewählt.
- [`post-purchase-upsells`](methoden/conversion/post-purchase-upsells.md) — **Post-Purchase-Upsells (1-Klick)**: Folgekauf mit geklärtem Zahlungsmodus (SCA/CIT/MIT).

## angebot/ (1)
- [`preis-aktionsgestaltung`](methoden/angebot/preis-aktionsgestaltung.md) — **Preis- und Aktionsgestaltung**: Marge, Mechanik, Streichpreise nach der 30-Tage-Regel.

## messung/ (1)
- [`funnel-ab-tests`](methoden/messung/funnel-ab-tests.md) — **Funnel-A/B-Tests**: Hypothese, Geschäftsmetrik, Stoppregel, Auswertung mit `../analytics/`.

## Geplante Erweiterungen (nicht enthalten)
Versand- und Retourenlogik, Marktplätze (Amazon, eBay), Abo-Commerce, B2B-Preislisten, Internationalisierung/OSS, Shop-Migration mit Weiterleitungen (mit `../website/`).
