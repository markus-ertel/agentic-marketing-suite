# Newsletter-Anmeldung · Capability v0.1

## Zweck / Voraussetzungen

Einzelne Anmeldungen entgegennehmen, ausdrücklich bestätigen lassen und abmelden. Kein Kampagnenmailer, keine automatische Kontakteanreicherung und kein allgemeiner Opt-in für andere Zwecke. PHP 8.3+ und [gemeinsame private Einrichtung](../common/README.md).

## Konfiguration / Ein- und Ausgaben

`webmodules.py --site /projekt/site install newsletter` übernehmen. In `newsletter` sind Aktivierung, echte Servicefreigabe mit Ablauf, fixer Absender, Transport, konkreter Einwilligungstext, dessen `consent_version` und der lokale `endpoint_path` einzurichten. Mustereinwilligungen ersetzen keine tatsächliche fachliche/rechtliche Prüfung.

1. GET `/api/newsletter.php` zeigt Formular mit Pflicht-Checkbox und Datenschutzlink. POST mit gültigem Token nimmt die individuelle Adresse entgegen.
2. Privater `pending`-Eintrag erhält einen zufälligen Einmal-Token mit 24 Stunden Frist; gespeichert wird dessen Hash. Eine feste transaktionale Bestätigungsnachricht geht in private Outbox oder den freigegebenen MTA. Bereits ausstehende/bestätigte Adressen werden nicht erneut angeschrieben; die Antwort verrät diesen Zustand nicht.
3. GET des Bestätigungslinks zeigt nur eine Bestätigungsseite. **Erst ein ausdrückliches POST** bestätigt die eigene Anmeldung; Linkscanner können über GET kein Opt-in erzeugen. Textversion und Bestätigungszeit werden gespeichert; der Bestätigungstoken ist danach verbraucht.
4. Nach Bestätigung kann die Person eine signierte Abmeldeadresse verwenden. Auch hier bestätigt POST die Abmeldung; Abmeldung funktioniert unabhängig von einer abgelaufenen Versandfreigabe und wird nicht von Anmeldequoten blockiert.

```sh
WEBMODULE_DOCUMENT_ROOT=/projekt/site php /projekt/site/api/newsletter.php --export-confirmed > /privat/newsletter-consents.csv
```

Der private CSV-Export enthält nur aktuell bestätigte Anmeldungen mit ID, E-Mail, Textversion, Zeitpunkt und Abmelde-URL. noCRM kann diese Datei zweckgebunden nutzen; eine spätere Aussendung benötigt eigene konkrete Versandfreigaben/Prüfungen und muss den aktuellen Abmeldestand beachten. Export ist keine pauschale Autorisierung. Bestehende Newsletter-/Consent-Daten werden nicht automatisch importiert.

## Prüfung / Status und Recovery

`pending` ist keine Einwilligung. `confirmed` ist ein technisch erfasster individueller Bestätigungsvorgang, kein allgemeines Rechtsgutachten. `unsubscribed` schließt die Person aus neuen Exporten aus. CSRF/Origin, Honeypot, Limits, kurze Tokenlaufzeit und private Ablage sind vorhanden. Consent-Ereignisse und Transportversuche bleiben nachvollziehbar; keine IP wird im Newsletter-Datensatz gespeichert. Private Rate-Pseudonyme und Host-Logs sind separat zu berücksichtigen.

MTA-Annahme ist nicht Zustellung. Ein unklarer Bestätigungsversand wird nicht blind wiederholt; Betreiber/Transportlog prüfen. Bei Outbox muss ein tatsächlich betriebener, freigegebener Zustellprozess die Nachricht weitergeben. Ohne diesen Prozess erreicht niemand eine E-Mail. Abgelaufene Anmeldungen und alte Abmeldedaten über die tägliche Wartung bereinigen; Aufbewahrung und Betroffenenrechte organisatorisch festlegen. Tests spielen den vollständigen GET/POST-/Abmeldeablauf mit einer privaten Outbox durch.

Bestätigungs-/Abmelde-URLs enthalten Zugriffstoken und gehören nicht in öffentliche Protokolle oder Analytics. Referrer werden von den Formularseiten unterdrückt; Query-Redaktion und Aufbewahrung der Hosting-Accesslogs muss der Betreiber einrichten, zum Beispiel:

```apache
# Apache: Aufrufe mit Token nicht protokollieren
SetEnvIf Request_URI "newsletter\.php" nl_token
SetEnvIf Query_String "(^|&)(confirm|unsubscribe)=" nl_token
CustomLog ${APACHE_LOG_DIR}/access.log combined env=!nl_token
```

```nginx
# nginx: Newsletter-Endpunkt ohne Accesslog
location = /api/newsletter.php { access_log off; include fastcgi_params; fastcgi_pass php; }
```

Bestätigungslinks sind einmalig und 24 Stunden gültig. Abmeldelinks bleiben bewusst dauerhaft gültig, damit Abmelden immer möglich ist; ein abgegriffener Link erlaubt nur die Abmeldung. Der CSV-Export stellt Zellen, die wie eine Tabellenformel beginnen, ein `'` voran. Der Analytics-Lite-Client sendet nur den Pfad, niemals solche Query-Token.
