# Wiederverwendbare Fähigkeiten – v0.2.3

Die Suite definiert fachliche Verfahren, Ein-/Ausgaben, Konfiguration und Status. Ein Harness stellt generische Werkzeuge bereit und ruft diese Verfahren auf. Er erfindet weder Zustellstatus noch Veröffentlichungsablauf. Einträge sind optional; kein Fachmodul oder veröffentlichter Webauftritt benötigt einen dauerhaften Suite-Dienst.

| ID | Typ / Owner | Implementierung und Vertrag |
|---|---|---|
| `website.sftp` | Adapter · Website | [OpenSSH-Publisher](../../website/.nocms/integrationen/sftp/README.md) – prüfbarer Datei-/Hash-Plan, verifizierte Host-Keys, Upload und Readback |
| `mail.imap-smtp` | Adapter · noCRM; gemeinsam für PR und Website-Eingänge nutzbar | [Mail-Adapter](../../noCRM/.nocrm/integrationen/email/README.md) – getrennte Konten, IMAP-Suche/Read-only-Import, lokale/IMAP-Entwürfe, SMTP, Anhänge |
| `web.contact-form` | Webmodul · Website | [Kontaktformular](../../website/.nocms/module/contact-form/README.md) – PHP, private Outbox oder begrenzter Server-Mailtransport |
| `web.analytics-lite` | Webmodul · Website | [Aggregierte Analyse](../../website/.nocms/module/analytics-lite/README.md) – ohne Cookies, dauerhafte Kennungen oder gespeicherte IP-Adressen im Modul |
| `web.site-search` | Webmodul · Website | [Lokale Suche](../../website/.nocms/module/site-search/README.md) – JavaScript und generierter JSON-Index |
| `web.sitemap` | Build-Werkzeug · Website | [Sitemap](../../website/.nocms/module/sitemap/README.md) – XML aus öffentlichen HTML-Seiten |
| `web.redirects` | Build-Werkzeug · Website | [Weiterleitungen](../../website/.nocms/module/redirects/README.md) – exakte lokale Apache-301/302-Regeln |
| `web.newsletter` | Webmodul · Website | [Newsletter-Anmeldung](../../website/.nocms/module/newsletter/README.md) – ausdrückliches Double-Opt-in, Abmeldung, Export bestätigter Anmeldungen |
| `suite.platform-export` | Build-Werkzeug · Advertising / Social / noCRM | [Lokale Importdateien](../tools/EXPORT_PLATFORM.md) – konkrete Freigabe, keine Plattformausführung |
| `analytics.google-read` | Leseadapter · Analytics | [GA4/Search Console](../../analytics/.analytics/tools/FETCH_GOOGLE.md) – autorisierte Berichte, private CSV/Manifest, keine Schreibaktion |

Jede Implementierung enthält `capability.json` gemäß [capability.schema.json](../contracts/capability.schema.json): Zweck, Owner, Typ, Voraussetzungen, Konfiguration, Ein-/Ausgaben, Prüfverfahren, Status und Außenaktionen. Das Register verweist auf die Quelle; es dupliziert keine Methodenbibliotheken. Zusätzliche Anbieteradapter, insbesondere Gmail/Graph, FTPS und besondere Hostingformate, sind **nicht implementiert**. Es gibt keinen unverschlüsselten FTP-Fallback.

## Universelle Werkzeuge, Adapter und Webmodule

- Datei-/Prozess-/HTTP-Werkzeuge gehören zum Harness. Technische Voraussetzungen nicht als vorhandene Verbindung ausgeben.
- Adapter liefern freigabefähige Pläne und konkrete Implementierungen. `runtime.py` ist ihre lokale gemeinsame Hilfsbibliothek und nutzt die vorhandene Freigabe-/Audit-Fähigkeit. Sie läuft nicht im Dashboard.
- Webmodule werden selektiv mit `website/.nocms/tools/webmodules.py` in einen echten Website-Ordner übernommen. Nur benötigte PHP-/JS-/HTML-Dateien und erzeugte Ausgaben werden veröffentlicht. Python, Suite, Harness und Cognitive Computer werden zum Betrieb dieser Website nicht benötigt. PHP-Module benötigen PHP und private Host-Konfiguration; die Standardsuche/Sitemap funktionieren auf statischem Hosting.

## Externe Aktionen und Protokolle

1. Spezialist erzeugt einen lokalen, lesbaren Plan und die exakten Artefakte. `planned` bedeutet keine Netzwerkaktion.
2. Qualitäts-/Rechtsprüfungen und Mensch entscheiden nach [APPROVALS.md](../APPROVALS.md). Die Freigabe bindet sich an die **Plan-Datei**, deren Version/Hash und exakten Aktionstyp/Zielstring. Der Plan enthält Inhalts-Hashes und nicht geheime Konto-/Zielkonfiguration. Alle Dateien relativ zum selben Arbeits-/Suite-Root referenzieren.
3. Der Harness authentifiziert die Person, prüft konkrete Handlungsbefugnis, rechtliche Grundlage, Kontorechte und Limits. Der CLI-Schalter `--harness-authorized` bestätigt diese bereits erfolgte Prüfung; er ist **kein Identitätsnachweis und keine automatisch erteilte Befugnis**.
4. Der Adapter prüft aktuelle Freigabe/Widerruf/Ablauf, den tatsächlich geladenen Plan-Hash, Dateien, Ziel und Eingaben. Eine Änderung verlangt einen neuen Plan und eine neue Freigabe. Unmittelbar vor Schreiben/Senden wird die Freigabe erneut geprüft. Widerruf während bereits laufender Provideraktionen kann technisch zu spät kommen; der Harness muss laufende Vorgänge koordinieren und gegebenenfalls stoppen/eskalieren.
5. Jeder Versuch wird gemäß [capability-execution.schema.json](../contracts/capability-execution.schema.json) in privater `executions.jsonl` erst als `started`, anschließend mit beobachtetem Ergebnis angehängt. Exklusive Sperre und persistente Schlüssel verhindern unbemerkte Wiederholung. `started` nach Prozessabbruch oder `uncertain` wird nicht automatisch erneut ausgeführt. Frühere Ereignisse bleiben erhalten; ein neuer Schlüssel ist kein Ersatz für Status-/Providerprüfung.

`accepted` bedeutet technische Annahme, **nicht zugestellt**. SFTP-`confirmed` bedeutet verifizierte Dateiübertragung per Readback, **nicht fachlich abgenommene oder im Browser geprüfte Website**. SMTP/IMAP-Timeouts und teilweise übernommene Deployments bleiben unklar, bis der tatsächliche Providerstand geprüft wurde. Keine Erfolgsbehauptung aus Exitcode oder syntaktischer Konfiguration allein.

Freigabe- und Ausführungsprotokolle bleiben getrennt, privat und außerhalb der Anweisungsbibliothek. Auch diese Dateien sind keine manipulationssicheren Identitätsspeicher. Keine Zugangsdaten, Mailtexte oder Anhänge in Ergebnis-/Fehlerprotokolle kopieren. Der Harness verantwortet Dateirechte, Backup, Aufbewahrung und Statusabgleich. Credentials sind ausschließlich externe Referenzen/Umgebungsvariablen.

## Autonome Web-Laufzeit

Kontakt-/Newsletter-Transport und Analytics laufen nach Veröffentlichung als vorab freigegebener, **begrenzter Serviceauftrag**: feste Zwecke, Vorlagen/Empfängerregeln, Quoten, Datenschutzinformation und Ablaufdatum werden mit dem Deployment geprüft. Die private Konfiguration muss `enabled`, eine echte `authorization.approval_ref` und eine künftige zonierte `expires_at` enthalten. Diese Referenz authentifiziert niemanden; sie wird vom Betreiber/Harness beim Einrichten geprüft. Laufzeitdateien führen keine neue KI-Freigabe durch und brauchen keinen dauerhaften Harness. Einen Widerruf muss der Betreiber/Harness durch Deaktivierung der privaten Host-Policy bzw. Sperren der Providerrechte tatsächlich umsetzen; ein zentraler Audit-Eintrag wird nicht automatisch zum eigenständigen Webhost synchronisiert.

Websitebesucher bestätigen nur eigene Anfragen bzw. eine eigene Newsletter-Einwilligung. Ein Kontaktformular ist keine Marketingeinwilligung. Ein Newsletter-Opt-in gilt nur für den angegebenen Zweck; keine allgemeine Werbe- oder Versandfreigabe ableiten. [Betrieb, Datenspeicherung und Wartung](../../website/.nocms/module/common/README.md) sind Teil jeder konkreten Bereitstellung.

## Prüfstand und Grenzen

Offline-Tests prüfen Freigabebindung, Dateigrenzen, Idempotenz, kontrollierte SFTP-/SMTP-/IMAP-Protokollantworten, Installation und statische Generatoren. Echte lokale PHP-HTTP-Tests prüfen Kontakt, Analytics, Double-Opt-in und Abmeldung. Eine erfolgreiche Prüfung ist keine Abnahme eines fremden Hosters, Kontos, MTA, SSH-Servers oder konkreten Rechtsfalls. Vor produktiver Verwendung eine autorisierte Testbereitstellung und tatsächliche Empfangs-/Browserkontrolle ausführen.

Quellen und Abrufstand: [QUELLEN.md](QUELLEN.md).
