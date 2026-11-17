# Standalone-Webmodule – gemeinsame Einrichtung und Betrieb

## Zweck und Voraussetzungen

PHP **8.3+** für Kontakt, Newsletter und Analytics; Suchoberfläche und generierte Dateien laufen auf statischem Hosting. Die veröffentlichten Dateien benötigen keine Suite, keinen Agenten-Harness, kein PHP-Framework und keine Datenbank. Der Operator muss HTTPS, PHP-Ausführung, Serverrechte, MTA/Outbox-Zustellung, tatsächliche Datenschutzinformation und eine sichere private Ablage einrichten.

## Selektive Installation

```sh
python3 website/.nocms/tools/webmodules.py --site /projekt/site install contact-form
python3 website/.nocms/tools/webmodules.py --site /projekt/site install analytics-lite
python3 website/.nocms/tools/webmodules.py --site /projekt/site install newsletter
python3 website/.nocms/tools/webmodules.py --site /projekt/site install site-search
```

Nur benötigte Module wählen. PHP-Module übernehmen ihre Laufzeitdatei sowie `_runtime.php` und das ausschließlich per CLI nutzbare `maintenance.php` nach `api/`. Der Installer schreibt keine Zugangsdaten, aktiviert keine Dienste und überschreibt keine abweichenden vorhandenen Dateien. Identische Vorlagen sind wiederholbar. Lokale Anpassungen beim Upgrade manuell zusammenführen. Unterverzeichnis-Hosting erfordert passende Asset-, Endpoint- und Seitenpfade; Beispiele gehen vom Webroot aus.

## Private Konfiguration und begrenzter Serviceauftrag

[config.example.json](config.example.json) **außerhalb** des öffentlichen Website-Verzeichnisses speichern und auf den echten Host anpassen. Alle Dienste sind im Beispiel deaktiviert. `WEBMODULE_CONFIG` zeigt auf diese private JSON-Datei; `WEBMODULE_SECRET` liefert mindestens 32 zufällige Bytes als serverseitiges Geheimnis, getrennt von Website/Versionsverwaltung. `data_dir` muss als privates, beschreibbares Verzeichnis außerhalb des Dokument-Roots existieren. PHP weist Konfiguration oder Speicher im Webroot ab; das verhindert nicht, dass ein falsch hochgeladenes JSON vorher vom Webserver ausgeliefert wird. Deshalb solche Dateien nie hochladen.

Für jeden aktivierten Dienst muss der verantwortliche Betreiber zuvor einen begrenzten Serviceauftrag freigeben: Zweck, feste Texte/Absender, Empfängerregeln, Aufbewahrung, Rate-/Kostenlimits und Laufzeit. Die Konfiguration enthält `enabled: true`, `authorization.approval_ref` auf die echte Freigabe und eine künftige ISO-Zeit mit Zeitzone in `authorization.expires_at`. Die Referenz ist kein Identitätsnachweis; ihre Echtheit/Befugnis prüft der Betreiber/Harness beim Einrichten. Das konkrete Deployment einschließlich Laufzeitregeln wird gemäß Suite-Freigaben geprüft. Es findet keine neue KI-Freigabe je Besucher statt und kein dauerhafter Zugriff auf den Suite-Audit-Trail benötigt.

`origin` ist die exakte HTTPS-Adresse ohne Pfad/Slash; unverschlüsseltes HTTP ist nur für localhost-Tests vorgesehen. `privacy_url` führt zu den tatsächlich passenden Datenschutzhinweisen. `transport: outbox` speichert private `inbound-<id>.json` zur Bearbeitung/Weitergabe; das allein versendet nichts. `transport: mail` nutzt ausschließlich den vorab konfigurierten Server-MTA. Feste Absender, Betreiberempfänger und Zwecke in der Konfiguration prüfen; SPF/DKIM/DMARC und Zustellung auf dem echten Host testen. PHP-`mail()`-Annahme ist keine Zustellung.

## Prüfverfahren und Status

Kontakt/Newsletter prüfen serverseitig Origin, zweckgebundene signierte Tokens, einmalige Formularnutzung, Honeypot, Felder, Adressen und Quoten. Sicherheits-Tokens sind cookie-frei, an die temporäre Netzwerkadresse gebunden und 15 Minuten gültig. Private Rate-Daten enthalten kurzlebige HMAC-Pseudonyme, keine Klartext-IP; auch pseudonyme Daten organisatorisch berücksichtigen. Nicht ungeprüft `X-Forwarded-For` übernehmen. Bei Reverse Proxies muss der Hoster den echten vertrauenswürdigen `REMOTE_ADDR` setzen, sonst können sich Besucher ein Limit teilen.

Quoten gelten **je Formular** (Kontakt, Newsletter-Anmeldung, -Bestätigung) getrennt: maximal drei Aktionen pro Minute und zehn pro Stunde je Netzwerkadresse sowie 100 insgesamt pro Stunde. Hinter einem Reverse Proxy oder CDN sieht PHP sonst nur die Proxyadresse, dann teilen sich alle Besucher eine Quote. In diesem Fall `trusted_proxies` mit den exakten Proxy-IP-Adressen setzen; nur für Anfragen von diesen Adressen wird der letzte nicht vertrauenswürdige Eintrag aus `X-Forwarded-For` verwendet. Ohne Eintrag wird `X-Forwarded-For` ignoriert. Eine gültige Newsletter-Abmeldung wird nicht durch die Anmeldequote blockiert. Diese Schranken sind kein vollständiger Bot-/DDoS-Schutz; Webhost-Limits und Missbrauchskontrolle bleiben erforderlich.

`queued` bedeutet privater Outbox-Eintrag; `accepted` nur MTA-Annahme; `uncertain` verlangt Betreiberprüfung. Ereignisse werden privat in `delivery-events.jsonl` mit Servicefreigabe-Referenz und Policy-Hash angehängt. Es werden keine Nachrichteninhalte in diesem Transportlog gespeichert. Eingangs-/Newsletter-Daten enthalten personenbezogene Angaben und bleiben privat. Diese Logs sind keine menschen-authentifizierenden Suite-Freigaben.

## Aufbewahrung und Wartung

Mit einem normalen Host-Job täglich ausführen, nicht über HTTP:

```sh
WEBMODULE_DOCUMENT_ROOT=/projekt/site php /projekt/site/api/maintenance.php --purge-expired
```

Die Umgebung muss weiterhin `WEBMODULE_CONFIG` und bei Bedarf das Servergeheimnis liefern. Die Wartung entfernt abgelaufene DOI-Anforderungen, alte abgemeldete Newsletter-Daten und alte Outbox-Dateien nach `retention_days` (Standard 30; 1–365). Sie bereinigt Analytics nach dessen eigener Frist und abgelaufene Rate-Informationen auch bei ausbleibenden Besucheraufrufen. Aktive Newsletter-Einwilligungen werden nicht still gelöscht. Transport-Audit-Aufbewahrung, Sicherungen und konkrete Betroffenenrechte separat festlegen; die CLI ist keine vollständige Lösch-/Rechtsplattform.

`maintenance.php` verweigert HTTP. Neue private Dateien erhalten restriktive Rechte; bestehende Verzeichnisrechte und Backups verantwortet der Host. Eine Veröffentlichung muss im echten Browser und auf dem konkreten PHP-/MTA-Host geprüft werden. Echte lokale PHP-HTTP-Tests in `website/.nocms/tests/test_php_modules.py` ersetzen diese Host-/Rechtsabnahme nicht.

Ein Widerruf des Serviceauftrags muss vom Betreiber/Harness auch am Host wirksam gemacht werden: den betroffenen Dienst in der privaten Konfiguration deaktivieren bzw. Providerrechte sperren und den tatsächlichen Stopp prüfen. Die Datei wird je Anfrage neu gelesen. Ein neuer zentraler Suite-Audit-Eintrag allein erreicht eine eigenständig laufende Website nicht automatisch; es wird keine solche Synchronisierung behauptet.
