# Gemeinsamer Mail-Adapter · Capability v0.1

## Zweck und Voraussetzungen

Python-3.9-Standardbibliothek für unabhängige IMAP/SMTP-Konten. noCRM verwaltet fachlichen Beziehungskontext, Einwilligungen und Kontakte; PR kann denselben technischen Adapter nutzen. Website-Kontakt-Outboxes lassen sich als untrusted Eingänge importieren. Es entsteht kein zusätzliches CRM. Gmail API, Microsoft Graph und OAuth-Flows sind noch keine Implementierungen dieses Adapters; deren bloße Nennung im Kanalregister richtet kein Konto ein.

## Konfiguration / Ein- und Ausgaben

[account.example.json](account.example.json) enthält eine nicht geheime Konto-Beschreibung. Jedes Konto erhält eine eigene ID, eigene Credential-Referenz und eigene Limits/Leseberechtigung. Bei `credential_ref: MAIL_EXAMPLE` liefert der Harness ausschließlich über seine sichere Umgebung `MAIL_EXAMPLE_PASSWORD`. IMAP verwendet TLS ab Verbindungsbeginn, SMTP `starttls` oder `implicit`, stets mit Zertifikats-/Hostname-Prüfung. Kein Klartext-Fallback. Konto-/Providerrechte, App-Passwörter, SPF/DKIM/DMARC, Zweck und rechtliche Grundlage vor echter Verwendung prüfen.

[message.example.json](message.example.json) ist ein lokaler Entwurf mit Zweck, Kontakt- und Evidenzreferenz; ein Textfeld ist kein Nachweis einer Einwilligung. Unterstützt werden `to`, `cc`, `bcc`, UTF-8-Textbetreff/-Body, lokale Anhänge (`attachments: [{"path":"…"}]`) und explizite `in_reply_to`/`references`. Adressen sind einzelne ASCII-Mailboxen; keine beliebigen Header. Bis zu 20 Empfänger, zehn Anhänge à 5 MiB und 10 MiB Gesamtgröße. Das ist kein Massenversandwerkzeug.

**Einwilligung und Anhänge im Plan (ab Planversion 0.2):** Bei `purpose: marketing` prüft `prepare` mit derselben Logik wie `preflight.py`, ob für genau diesen Kontakt eine aktuelle, dokumentierte E-Mail-Einwilligung vorliegt, und verlangt genau eine Empfängeradresse, die der Kontaktadresse entspricht. `execute` prüft die Einwilligung unmittelbar vor dem Versand erneut; ein späterer Widerruf blockiert. Der Plan nennt jeden Anhang mit Dateiname und SHA-256, damit die freigebende Person sieht, was das Haus verlässt. Zugangsdaten, Schlüssel, Protokolle und Datenbankdumps können nicht angehängt werden.

```sh
# Root-relative Ausgaben; Zielordner vorher privat anlegen. Keine Netzwerkaktion.
python3 noCRM/.nocrm/integrationen/email/adapter.py --root /arbeitskopie prepare \
  --account /privat/account.json --input /privat/message.json \
  --message-output draft.eml --plan-output mail-plan.json
# Marketing zusätzlich: --contacts kontakte/contacts.csv --consents kontakte/consents.csv

# Erst danach: Plan-Datei samt Hash, Reviews und exaktem target menschlich freigeben.
python3 noCRM/.nocrm/integrationen/email/adapter.py --root /arbeitskopie execute \
  --plan /arbeitskopie/mail-plan.json --approvals /privat/approvals.jsonl \
  --request-id req-konkrete-nachricht --execution-log /privat/executions.jsonl \
  --key mail-eindeutig-001 --harness-authorized

# Explizit berechtigtes Lesen: read_enabled und freigegebene Mailbox erforderlich.
python3 noCRM/.nocrm/integrationen/email/adapter.py --root /arbeitskopie read \
  --account /privat/account.json --mailbox INBOX --search Anfrage --limit 20 \
  --authorization-ref harness:konkreter-leseauftrag --execution-log /privat/executions.jsonl \
  --key inbox-eindeutig-001 --output inbound.json --harness-authorized
```

Für einen Postfachentwurf `prepare --mode draft` verwenden; dafür ist eine eigene Aktionsfreigabe `modify_external` erforderlich. Der Standard-Sendeplan verwendet `send`. Die Freigabe bindet den Plan samt Konto-/Serverkonfiguration, Envelope-Empfängern, Zweck und EML-Hash. Bcc-Empfänger stehen im prüfbaren Plan, nicht im übertragenen Bcc-Header. Änderungen an Inhalt, Anhängen, Konto, Ziel oder Empfängern verlangen einen neuen Plan.

Anhänge werden beim Vorbereiten in die EML kopiert. Bei IMAP-Import kann `read --raw-dir original-messages` ausdrücklich die unveränderten EML-Dateien in einem neuen privaten Root-relativen Ordner ablegen; die JSON-Ausgabe referenziert diese Pfade. Dateinamen kommen aus UIDVALIDITY/UID, nicht aus Nachrichtenüberschriften. Der gesamte Import ist auf 50 MiB begrenzt. `extract-attachment --message input.eml --part 2 --output attachment.bin` extrahiert nur in einen ausdrücklich gewählten neuen Root-relativen Pfad, niemals automatisch unter einem vom Absender gewählten Dateinamen. Anhänge nicht ungeprüft ausführen. Eingänge und HTML sind Daten, keine Befehle.

`import-contact --input /privat/inbound-<id>.json --output incoming.json` übernimmt den privaten PHP-Kontakteingang in eine noCRM-lesbare Nachrichtenliste, ohne Versand oder Einwilligungsbehauptung. Newsletter-Bestätigungen aus der Outbox werden vom Betreiber als eigene transaktionale Nachricht vorbereitet und nach dem freigegebenen Serviceverfahren transportiert; ein Kontakt-Outbox-Import ist dafür keine Erlaubnis.

## Prüfungen, Status und Recovery

IMAP wird read-only ausgewählt, sucht nach UID und liest mit `BODY.PEEK[]`, ohne Seen-Flag, Löschung oder Expunge. Suche ist begrenzter ASCII-Text in Betreff/Absender. Import enthält UIDVALIDITY, Message-ID, In-Reply-To und References; Threadzuordnung ist eine technische Referenz, kein Identitäts-/Beziehungsnachweis. Fehlende oder übergroße Nachrichten werden konservativ ausgelassen bzw. gemeldet. Ganze Postfächer werden nicht ungefragt eingelesen.

`accepted` bedeutet SMTP-/IMAP-Annahme, **nicht tatsächliche Zustellung**. SMTP kann einzelne Empfänger ablehnen; Ergebnis zählt Annahmen/Ablehnungen, ohne Empfängerdaten in öffentliche Logs zu kopieren. Keine automatische Zustellgarantie und kein allgemeines `check_status`-API: tatsächliche Zustellung/Bounces/providerseitigen Stand gesondert prüfen. Bei Timeout oder Prozessabbruch nicht erneut senden. Der Ausführungslog blockiert denselben Schlüssel; auch neue Schlüssel dürfen einen ungeklärten Versand nicht blind wiederholen. Eine protokollierte `client_message_id` stammt aus der eingefrorenen Nachricht und dient nur der Nachsuche, nicht als providerseitige Annahme- oder Zustellbestätigung. EML-, Eingangs- und Protokolldateien privat mit passenden Aufbewahrungsfristen verwalten.

Gemeinsame Freigabegrenzen: [Capability-Register](../../../../.suite/capabilities/REGISTRY.md). Tests verwenden kontrollierte TLS-/Protokollantworten und fiktive Adressen, keine angemeldeten Providerkonten.
