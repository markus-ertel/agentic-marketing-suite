# Google-Berichtsdaten lokal abrufen

`fetch_google.py` ist ein optionaler, nur lesender Standardbibliothek-Adapter. Er führt GA4 `runReport` bzw. Search Console `searchAnalytics.query` aus und schreibt neue private CSV-/Manifestdateien. Keine echten Konten oder Tokens sind enthalten; Konto-/Scope-/Zweckberechtigung im Harness prüfen. Lokal simulierte Tests sind keine reale Kontoabnahme.

Token ausschließlich über eine Umgebungsvariable aus dem tatsächlichen Secret Store bereitstellen, standardmäßig `GOOGLE_OAUTH_ACCESS_TOKEN`. Nur `analytics.readonly` bzw. `webmasters.readonly` verwenden; der Adapter kann die Scopes eines beliebigen Bearer-Tokens nicht selbst authentifizieren. Keine Tokens in Dateien/Logs oder Befehlsargumente schreiben. HTTP-Weiterleitungen werden abgelehnt, um Bearer-Daten nicht an andere Ziele weiterzugeben.

```sh
python3 analytics/.analytics/tools/fetch_google.py ga4 --property 123456789 --time-zone Europe/Vienna --days 30 --out-dir /privat/analytics/inbox
python3 analytics/.analytics/tools/fetch_google.py gsc --site sc-domain:example.org --days 30 --dimension query --out-dir /privat/analytics/inbox
```

IDs und Zeitzone sind Beispiele. GA4 verlangt die tatsächliche IANA-Zeitzone der Property; soweit API-Metadaten sie liefern, muss sie übereinstimmen. GSC-Tage liegen immer in `America/Los_Angeles`, nicht in der Rechnerzeitzone. Stichtage werden in der betreffenden Zone berechnet. GA4 bis gestern und GSC bis vor drei Tagen sind konservative Fenster, keine Vollständigkeitsgarantie.

GA4 exportiert `sessions`, `engagedSessions`, `keyEvents` je Tag und Kanalgruppe. **Keine `totalUsers`-Spalte**: eindeutige Nutzer können über Tage/Kanäle nicht addiert werden. GSC exportiert Klicks, Impressionen und `position_x_impressions`; die gewichtete Position ist deren Summe geteilt durch Impressionen. Der bestehende Evaluator benötigt bei mehreren Zeilen pro Tag `--segment-column channel` bzw. die gewählte GSC-Dimension, gegebenenfalls mit einem konkreten `--segment`. Eine Segmentauswertung ist keine global deduplizierte Nutzerzählung.

CSV und Manifest werden nicht überschrieben. Bei einer abgefangenen Ausgabe-Panne werden nur die gerade neu erzeugten Dateien entfernt; bestehende Dateien bleiben erhalten. Nach hartem Prozessabbruch eventuelle Teildateien vor erneutem Lauf prüfen. Dateinamen identifizieren Quelle, Dimension und Zeitraum; für einen weiteren Abruf desselben Fensters einen neuen Ausgabeordner verwenden. Neue Dateien erhalten private Rechte. Query-/Seitenwerte können Personenbezug oder vertrauliche URLs enthalten und werden als `confidential` eingestuft; private Speicher-/Aufbewahrungsregeln bleiben erforderlich.

Limits: GSC liefert plattformbedingt nicht garantiert alle Long-Tail-Zeilen; Abfragen nach Query/Page sind nicht stets über alle Dimensionen additiv. GA4-Sampling, Thresholding, Consent-Lücken und „(other)“ vor Interpretation prüfen. Dieser Adapter ersetzt keine technische/fachliche Abnahme des konkreten Berichts und ist kein Kausalitätsnachweis.

Primärquellen, geprüft 27.10.2026: [GA4-Metriken](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema), [GA4-Metadaten](https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/ResponseMetaData), [Search-Console-Abfrage und Pacific Time](https://developers.google.com/webmaster-tools/v1/searchanalytics/query).
