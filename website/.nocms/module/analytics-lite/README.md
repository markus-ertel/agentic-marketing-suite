# Analytics Lite · Capability v0.1

## Zweck / Voraussetzungen

Aggregierte **Seitenaufrufe**, keine eindeutigen Besucher, Sessions, Conversion-Zuordnung oder Kausalwirkung. PHP 8.3+, privater Speicher und explizit geprüfte Erhebungs-/Rechtsgrundlage gemäß [gemeinsamer Einrichtung](../common/README.md). Keine automatische Rechtskonformitätsbehauptung durch Cookie-Freiheit.

## Konfiguration / Ein- und Ausgaben

`webmodules.py --site /projekt/site install analytics-lite` kopiert PHP und optionales JS. `analytics` ist standardmäßig deaktiviert. Betreiber setzt eine begrenzte Servicefreigabe, die tatsächlichen öffentlichen Routen in `pages` und `retention_days` (1–365, Standard 30). Nur explizit zugelassene Pfade werden gezählt. Keine automatische Aktivierung im HTML.

Optional einmal einbinden:

```html
<script src="/js/analytics-lite.js" data-endpoint="/api/analytics.php" defer></script>
```

JS sendet nur `location.pathname`, ohne Query, Cookies, Kennungen oder Referrer-Feld an denselben Origin. DNT/GPC werden im Client und Server respektiert. Der PHP-Zähler speichert nur UTC-Tag, zugelassenen Seitenpfad und Anzahl. Keine IP, User-Agent, Referrer oder dauerhafte Nutzerkennung im Modul. Der Webserver selbst sieht Netzwerkadressen und kann eigene Zugriffslogs führen: Hosting-Logs, Aufbewahrung und tatsächliche Datenschutzhinweise gesondert prüfen.

```sh
WEBMODULE_DOCUMENT_ROOT=/projekt/site php /projekt/site/api/analytics.php --export > /privat/pageviews.csv
```

CSV `date,page,pageviews` ist eine geeignete aggregierte Dateiquelle für `analytics/`. Export läuft nur per Host-CLI, nicht über einen öffentlichen HTTP-Endpunkt. Für serverseitige PHP-Seiten kann der Host denselben zugelassenen Pfad per serverseitiger POST-Schnittstelle innerhalb des freigegebenen Serviceverfahrens melden; nicht zusätzlich zum JS doppelt zählen.

## Prüfung / Status

GET zählt nichts; POST verlangt passenden Origin, kleine JSON-Eingabe und eine bekannte Route. Deaktiviert, abgelaufen, DNT/GPC oder gezählt führen zu 204 ohne Identifier oder personenbezogenes Echo. **204 allein beweist keinen Zählerzuwachs**; dafür den privaten Aggregatexport prüfen. Unbekannte Routen 422, falscher Origin 403. Maximal 100.000 Zählungen pro Tag begrenzen Missbrauch, aber Bots/Reloads bleiben Aufrufe, keine Menschen. Optional begrenzt `analytics.max_hits_per_client_day` (1–10.000) die Zählungen je Besucher und Tag; dafür wird ein HMAC-Pseudonym der Netzwerkadresse höchstens 24 Stunden in den privaten Rate-Daten gehalten. Ohne diese Einstellung speichert Analytics nichts je Besucher. Der Export stellt formelartigen Seitenpfaden ein `'` voran. Aktive Requests und tägliche Wartung bereinigen die Aufbewahrungsfrist. Echte PHP-Tests prüfen Zähler, Deaktivierung, DNT/GPC, nicht gespeicherte Query/IP und Export.
