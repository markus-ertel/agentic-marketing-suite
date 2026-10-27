# Quellenprofil: Google Analytics 4
**Datenweg:** Google Analytics Data API, only with approved property access.

## Importprinzip
1. Lesezugriff/Scope, Zweck, Berichtszeitraum und relevante Konten ermitteln.
2. Offene Exportrepräsentation CSV/JSON bevorzugen und Datenstand, Zeitzone, Schema, Filter sowie Query festhalten.
3. Grain, Metrikdefinitionen, Quoten/Pagination und eindeutige Schlüssel validieren; keine implizite Quellenfusion.
4. Nur für eine konkrete fachliche Entscheidungsfrage analysieren. Dokumentiere Einschränkungen, bevor du Ergebnisse deutest.

## Kritische Prüfung
Event metrics, identity modeling, consent effects, quotas, thresholding and channel semantics.

## Betrieb
Dieses Quellenprofil wird durch den optionalen [lokalen Leseadapter](../tools/FETCH_GOOGLE.md) ergänzt. Die Implementierung ist mit simulierten Antworten geprüft; eine echte Kontoverbindung ist damit nicht nachgewiesen. Vor echter Anbindung aktuelle Hersteller-Dokumentation, Berechtigungen, Datenschutz und Rate-Limits prüfen. Standardmäßig **read-only**.
