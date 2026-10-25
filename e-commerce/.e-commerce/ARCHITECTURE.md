# ARCHITECTURE — E-Commerce-Beratung und Ausführungsgrenzen
## Grenzen
`e-commerce/AGENT.md` = Einstieg; `.e-commerce/` = Methoden, Rechtsleitfäden, Datenformate, lokales Werkzeug, Quellen und Laufzeitmetadaten STATE/LOG/HISTORY. Ergebnisse (Kataloge, Feeds, Spezifikationen, Testpläne) außerhalb der versteckten Systemstruktur.

**Kein Laufzeitsystem:** Das Modul betreibt weder Shop noch Checkout, Warenkorb, Bestellverwaltung oder Zahlungsabwicklung. Shop-Systeme (Shopify, WooCommerce, Shopware, Eigenbau), Funnel-Plugins und Zahlungsdienste sind **externe Systeme**, die über Adapter mit Freigabe angesprochen werden.

## Entscheidungslaufzeit
`Intent → Kontext & Daten → Diagnose → Methodenwahl → Empfehlung/Spezifikation → Katalog/Funnel-Definition → lokaler Preflight (Feed-Werkzeug) → Rechts- und Qualitätsprüfung → Freigabe → ggf. Adapteraktion im Zielsystem → Rückmeldung/Read-back → Messung mit analytics → Optimierung`.

## Teilprozesse
- **Beratung:** Shop-System, Sortiment, Preislogik, Checkout, Funnel; ohne Systemzugang möglich.
- **Datenpflege:** Katalog als CSV/JSON (`.e-commerce/FORMATE.md`); eine führende Quelle, stabile IDs, Varianten über `item_group_id`.
- **Feed-Erzeugung:** lokal mit `.e-commerce/tools/generate_gmc_feed.py` (XML/TSV); Erzeugen ist keine Übertragung.
- **Funnel-Spezifikation:** Angebotsschritte, Order Bumps, Upsells und Tests als JSON nach `.e-commerce/formate/funnel-offer.schema.json`; Umsetzung erfolgt im Shop-System.
- **Ausführung:** ausschließlich über Adapter nach `.e-commerce/AKTIONEN.md` mit Freigabe, Idempotenz, Read-back und Protokoll.

## Kooperation ohne Zwang
- `../marketing/`: Positionierung, Preisstrategie im Markenkontext, Zielgruppen
- `../advertising/`: Shopping-/Performance-Max-Kampagnen, Gebote und Budget; nutzt den hier gepflegten Feed, ändert ihn aber nicht
- `../website/`: Landingpages und Inhalte; Shop-Templates nur mit Umsetzungsauftrag
- `../creative/`: Produktbilder, Video, Rechte an Bildmaterial
- `../analytics/`: Messkonzept, A/B-Test-Auswertung, Kausalitätsgrenzen
- `../noCRM/`: individuelle Kundenkommunikation zu Bestellungen, keine Massenmails aus Bestelldaten
Fehlen diese Verzeichnisse, arbeitet E-Commerce vollständig eigenständig. Keine Übertragung personenbezogener Bestelldaten ohne Erlaubnis.

## Zuständigkeit gegenüber advertising
`advertising/` beschreibt Shopping-Kanäle und Merchant-Center-Kampagnenbezug. **Schreib-Owner des Produktkatalogs und des daraus erzeugten Feeds ist `e-commerce/`.** Advertising meldet Feed-Befunde als Findings zurück, statt den Katalog zu ändern.

## Persistenz
`.e-commerce/STATE.md` = aktueller Stand und Artefaktpfade; `.e-commerce/LOG.md` = überprüfbare Aktionen und Fehler mit IDs; `.e-commerce/HISTORY.md` = bestätigte Entscheidungen (Shop-System, Preislogik, Funnel-Versionen). Keine erfundenen Einträge.

## Wiederaufnahme
Zuerst STATE lesen; Referenzen auf konkrete Artefakte prüfen; nur benötigtes Wissen laden; offene Freigaben bleiben offen, niemals ungefragt Preise oder Feeds ändern.
