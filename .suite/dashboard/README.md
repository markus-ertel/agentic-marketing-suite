# Agentic Marketing Dashboard

Lokaler Browser-Arbeitsraum für die bestehende Suite mit **Codex und Pi**: Dateien ansehen, Änderungen verfolgen und mit einem ausdrücklich gewählten externen Agentensystem kommunizieren. Die Fachbereiche bleiben unverändert und eigenständig nutzbar. Das Dashboard enthält keinen Agentenloop, keine Marketinglogik und keinen Dateieditor.

## Start und Stop

Python **3.9 oder neuer**, ein moderner Browser und für gerendertes Markdown `markdown-it-py`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r .suite/dashboard/requirements.txt
.venv/bin/python .suite/dashboard/server/app.py
```

Danach die ausgegebene Adresse öffnen, standardmäßig `http://127.0.0.1:8765/?token=…`. Das Token wird bei jedem Start neu erzeugt; ohne es antwortet der Server mit 401. Die Adresse nicht weitergeben. Stoppen mit **Strg+C** im Serverterminal. Sind die Abhängigkeiten bereits in Python installiert, genügt `python3 .suite/dashboard/server/app.py`. Ohne Markdownbibliothek bleibt die Dateiansicht verwendbar und zeigt Markdown als Quelltext mit einem Hinweis.

Der Server verwendet Python-Standardbibliothek und natives HTML/CSS/JavaScript. Es gibt keinen Frontend-Build, keinen CDN-Aufruf und keine Inhaltsdatenbank. Die Agentenprogramme sind **optional** und werden erst beim ausdrücklich ausgelösten Verbindungsaufbau gestartet.

## Konfiguration

[config.json](config.json) enthält Host, Port, Suite-Pfad, Vorschaugrenze, Aktualisierungsintervall und Agentenprofile. Änderungen gelten nach einem Serverneustart.

- `server.host`: Standard `127.0.0.1`. Erlaubt sind `127.0.0.1`, `localhost` und `::1`; andere Adressen (z. B. `0.0.0.0`) verweigert der Start, außer `server.allow_non_loopback` ist ausdrücklich `true`.
- `server.port`: `0` bis `65535`; bei `0` wählt das Betriebssystem einen freien Port. Die tatsächliche Adresse wird ausgegeben.
- `suite.root`: relativ zum **Ordner der verwendeten config.json**, nicht zum Terminal-Arbeitsverzeichnis. `../..` bezeichnet bei der mitgelieferten Datei den Suite-Root.
- `suite.show_internal_files`: serverseitige Zugriffserlaubnis für interne Punktdateien und -ordner, Standard `false`. Bei `false` sind z. B. `.marketing/` und `.nocrm/` auch über direkte Datei-URLs und Suche gesperrt; der Browser kann dies nicht freischalten. `.suite/` bleibt als gemeinsamer Einstieg zugänglich. Versionsverwaltung, bekannte Zugangsdatenpfade und Schlüsseldateien bleiben auch bei `true` gesperrt. Virtuelle Umgebungen, Python-Caches und `node_modules` werden aus der Navigation ausgespart.
- `suite.refresh_interval_ms`: Pollingintervall, mindestens `500`, Standard `2000`.
- `viewer.default_mode`: `preview` oder `source`.
- `viewer.max_inline_file_mb`: Standard `25`. Größere Textdateien werden zum Download angeboten. Medien und PDFs können unabhängig davon direkt gestreamt werden.
- `approvals.logs`: ausdrücklich verbundene Freigabeprotokolle mit `id`, `label` und lokalem JSONL-`path`; Standard `[]`. Relative Pfade beziehen sich auf den Ordner der verwendeten Konfigurationsdatei. Es findet keine automatische Suche nach privaten Protokollen statt.
- `agents.profiles`: Programmargumente als JSON-Liste; keine Shellauswertung. Ein absoluter Programmpfad ist möglich, wenn die CLI nicht im `PATH` des Serverterminals liegt.

Eine andere Konfiguration lässt sich mit `--config /absoluter/pfad/config.json` verwenden. Anmeldung und Providerkonfiguration erfolgen im jeweiligen Agentenprogramm. Zugangsdaten gehören nicht in die Dashboardkonfiguration.

## Dateiansicht

Die Navigation lädt echte Unterverzeichnisse bei Bedarf. Zusätzliche Fachmodule wie `e-commerce/` werden über ihre `AGENT.md` erkannt und erscheinen auch in Startansicht und Arbeitsverzeichnisauswahl. Die Suche erfasst Dateinamen und relative Pfade innerhalb der sichtbaren Verzeichnisse. Mit **Interne Ordner** lassen sich Methoden unter `.marketing/`, `.nocms/` usw. einblenden, wenn `suite.show_internal_files` auf dem Server aktiviert wurde. Andernfalls ist der Schalter deaktiviert. `/` fokussiert die Suche. Auf schmalen Bildschirmen öffnen Menü- und Chatknopf die jeweiligen Panels, `Escape` schließt sie.

Unterstützt werden Markdown mit Tabellen und Codeblöcken, UTF-8-Text und Quellcode, JSON, JSONL, CSV/TSV, Bilder einschließlich SVG, HTML, PDF sowie Audio/Video entsprechend den Browserfähigkeiten. CSV ist auf 500 Zeilen und 100 Spalten begrenzt. Unbekannte oder zu große Formate behalten einen Downloadlink. HTML läuft in einem getrennten, eingeschränkten Frame ohne Skriptausführung; relative lokale CSS- und Bilddateien werden über `/view/` geladen. Interaktive HTML-Anwendungen benötigen einen eigenen Entwicklungsserver.

Offene Dateien und aufgeklappte Verzeichnisse werden regelmäßig geprüft. Externe Änderungen erscheinen automatisch, neue Dateien erhalten einen Hinweis, verschwundene Dateien einen verständlichen Zustand. Eine während des Schreibens vorübergehend unlesbare Datei wird weiter geprüft. Dateipfade lassen sich kopieren. Angeheftete und zuletzt geöffnete Dokumente werden ausschließlich als Browser-Anzeigezustand gespeichert.

## Freigaben anzeigen

Links in der Navigation **Freigaben** wählen oder `/?view=approvals` öffnen. Die Übersicht zeigt Anforderungstitel, Fachbereich, Version, gegebenenfalls Budget sowie den aktuellen Status: Ausstehend, Freigegeben, Abgelehnt, Änderung verlangt, Widerrufen oder Abgelaufen. Bei einer Entscheidung stehen Person, gegebenenfalls Rolle und Zeitpunkt mit lokaler Zeitzone dabei; bei einer ausstehenden Anfrage steht ausdrücklich „Angefragt am“. Über „Begründung und Dokument“ sind Begründung und das referenzierte Dokument erreichbar.

Die Konfiguration kann beispielsweise diesen Abschnitt enthalten:

```json
{
  "approvals": {
    "logs": [
      {"id": "herbstkampagne", "label": "Herbstkampagne", "path": "/privater/pfad/approvals.jsonl"}
    ]
  }
}
```

Konfigurationsänderungen benötigen einen Serverneustart. Dateien außerhalb des Suite-Roots werden nur als ausdrücklich konfigurierte Audit-Quelle gelesen; dadurch entsteht kein allgemeiner Dateizugriff außerhalb der Suite. Absolute Quellpfade und vollständige Aktionsfreigabekandidaten werden nicht an den Browser ausgeliefert. Standardmäßig sind keine Protokolle verbunden; fiktive Beispiele werden nie automatisch als echte Entscheidungen angezeigt. Für eine Testansicht kann gezielt `.suite/beispiele/approval-demo/approvals-demo.jsonl` verbunden werden, mit einer klaren Bezeichnung wie „Fiktive Beispielansicht“ und einem zum Konfigurationsordner passenden Pfad.

Die Ansicht aktualisiert sich beim Öffnen, über **Aktualisieren** und während sie sichtbar ist mit dem bestehenden Pollingintervall. Ein angehängter Widerruf ersetzt den angezeigten Status, ohne die Historie zu ändern. Fehlende, gesperrte, beschädigte oder nicht lesbare Protokolle liefern einen Hinweis und keine alten positiven Status. Gültige andere Quellen bleiben getrennt sichtbar. Leere und noch nicht konfigurierte Quellen haben eigene Zustände. Das Lesen ist auf 10 MiB je Protokoll begrenzt; größere Protokolle werden als derzeit nicht verlässlich anzeigbar behandelt und niemals still gekürzt.

Das Dashboard liest und prüft die Ereigniskette für die Anzeige, schreibt aber keine Entscheidungen oder Sperren. Es gibt keine Freigabe-, Ablehnungs- oder Widerrufsbuttons. Die tatsächliche Erfassung und Ausführungsprüfung verbleibt beim Harness bzw. Adapter, wie in [APPROVALS.md](../APPROVALS.md) beschrieben. Eine angezeigte Freigabe ist kein Nachweis einer erfolgten Veröffentlichung oder Buchung.

## Agenten verwenden

1. **Agenten-Chat** öffnen; Agent und Arbeitsverzeichnis separat auswählen.
2. Optional eine vom Anbieter unterstützte externe Sitzungsreferenz eintragen und **Neue Verbindung** wählen.
3. Eine Nachricht senden. **AGENT.md-Einstieg** fügt eine sichtbare Anleitung in den Entwurf ein; sie wird erst mit **Senden** übermittelt.
4. **Datei referenzieren** ergänzt den sichtbaren Suite-Pfad im Entwurf. Dateiauswahl allein übermittelt keinen Kontext und wechselt keine Sitzung.
5. Zwischen **Beobachtbaren Sitzungen** wechseln. **Strg+Enter** bzw. **Cmd+Enter** sendet die Nachricht.

Der Status folgt externen Ereignissen. Erfolgreiche Promptannahme zählt nicht als Abschluss. Bei SSE-Unterbrechung erscheint `unbekannt`. Der Browser verbindet den Ereignisstrom erneut; ein Reload übernimmt die aktive Verbindung des noch laufenden Servers.

| Adapter | Transport | Wiederaufnahme | Interaktionen |
|---|---|---|---|
| Pi | `pi --mode rpc`, langfristiger JSONL-Prozess | Pi-Sessiondatei im optionalen Referenzfeld; `session_file` wird in der API angezeigt | Pi-Dialoge für Bestätigung, Auswahl und Text |
| Codex | `codex app-server`, JSONL mit Initialisierung | Externe Thread-ID über `thread/resume` | Freigabeanfragen, Benutzerrückfragen; weitere Anfragen mit Originaldaten und strukturierter Antwort |

Es werden keine Permission-Bypass-Flags ergänzt. Externe Einstellungen und Berechtigungen bleiben beim Anbieter. Für Pi mit einem lokalen Modell muss zusätzlich dessen Modellserver erreichbar sein; der Start der Pi-CLI allein startet diesen Server nicht.

**Trennen** schließt ausschließlich den vom Dashboard gestarteten Transportprozess, gegebenenfalls auch dessen laufenden Turn. Extern gespeicherte Sitzungen werden weder gelöscht noch archiviert. Frei in anderen Terminals gestartete Sitzungen werden nicht automatisch beobachtet. Nach Serverneustart müssen Verbindungen ausdrücklich neu geöffnet und gegebenenfalls über die externe Referenz fortgesetzt werden.

Der Server hält maximal 2.000 Ereignisse je Verbindung als flüchtigen Transportpuffer. Der Browser kann daraus nach einem Reload die Anzeige rekonstruieren; bei Überlauf erscheint ein Hinweis. Das ist kein dauerhaftes Chatarchiv. Vollständige Historie, Kontextverwaltung und Wiederaufnahme bleiben beim externen Agentensystem. Der Puffer wird nicht auf Festplatte geschrieben.

## HTTP-Vertrag

| Methode | Pfad | Funktion |
|---|---|---|
| GET | `/api/config` | Öffentliche Anzeigeeinstellungen |
| GET | `/api/approvals` | Read-only Statusprojektion der ausdrücklich konfigurierten Protokolle; keine frei wählbaren Quellpfade |
| GET | `/api/modules` | Vorhandene Fachbereiche und `.suite` |
| GET | `/api/tree?path=…&hidden=true&q=…` | Verzeichnisebene; bei Suchbegriff rekursive Pfadsuche |
| GET | `/api/file?path=…` | Metadaten und begrenzte Vorschau; `meta=true` nur Metadaten |
| GET | `/api/raw?path=…` | Originaldatei, Bytebereiche; `download=true` als Download |
| GET | `/view/<relativer-pfad>` | Getrennte Dokumentansicht mit relativen Ressourcen |
| GET | `/api/agents` | Programme, Verfügbarkeit und Fähigkeiten |
| GET | `/api/sessions` | Nur tatsächlich beobachtbare Verbindungen |
| POST | `/api/sessions` | `{profile, cwd, external_id?}` verbinden |
| POST | `/api/chat` | `{session, message}` weiterreichen |
| GET | `/api/events?session=…&after=…` | SSE mit Event-ID; unterstützt `Last-Event-ID` |
| POST | `/api/interaction` | `{session, request_id, response}` an eine offene externe Rückfrage |
| POST | `/api/disconnect` | `{session}` Transport schließen |

Alle HTTP-Anfragen benötigen einen einzelnen erlaubten `Host`: `127.0.0.1:<port>`, `localhost:<port>` oder `[::1]:<port>` mit dem tatsächlich gebundenen Port. POST benötigt zusätzlich einen einzelnen `Origin`, der exakt der HTTP-Adresse dieses Hosts entspricht. Fremde Hostnamen sowie fehlende, doppelte oder abweichende Origin-Header werden vor dem Zugriff auf Daten oder Agententransporte abgelehnt. Eigene HTTP-Clients müssen für POST den passenden Origin mitsenden.

Zusätzlich verlangt jede Anfrage das Zugangstoken dieses Starts, als Cookie `ams_dashboard` oder Header `X-Dashboard-Token`. Der Aufruf von `/?token=…` setzt das Cookie (`HttpOnly`, `SameSite=Strict`) und entfernt das Token aus der Adresszeile. Host- und Origin-Prüfung schützen gegen fremde Websites; das Token schützt auch gegen andere lokale Prozesse, die die Startausgabe nicht sehen. Dashboard-Seiten senden `Content-Security-Policy` mit `frame-ancestors 'none'` sowie `X-Frame-Options: DENY`; externe Bilder in Markdown-Vorschauen werden nicht geladen.

Vom Dashboard gestartete Agenten erhalten die Umgebung ohne Zugangsdaten der Suite-Adapter (Variablen auf `_PASSWORD`, `_KEY_FILE`, `_KNOWN_HOSTS_FILE` sowie `GOOGLE_OAUTH_ACCESS_TOKEN`). Zugangsdaten des Agentenanbieters selbst bleiben erhalten.

Es gibt keine API zum Bearbeiten von Suite-Dateien. Die Dateiauslieferung bleibt innerhalb von `suite.root`; sowohl angefragte Pfade als auch aufgelöste Symlink-Ziele unterliegen den Zugriffsregeln. `.git`, `.env*`, bekannte Zugangsdatenverzeichnisse (u. a. `.aws`, `.ssh`, `.codex`), Zugangsdaten-Dateinamen und Schlüssel-/Zertifikatscontainer werden auch bei aktivierter interner Ansicht nicht ausgeliefert. Die Regeln gelten für Baum, Suche, Vorschau, Metadaten, Downloads und Medien. Eine `.gitignore` ist keine Dashboard-Zugriffsliste: reguläre Arbeitsdokumente können angezeigt werden, auch wenn Git sie ignoriert. Unbekannt benannte Geheimnisse werden nicht anhand ihres Inhalts erkannt und gehören weiterhin außerhalb des Suite-Roots.

Dies ist ein lokales Werkzeug ohne eigenes Konto- oder Rechtesystem; nur an Loopback binden und nicht über Netzwerkfreigaben oder einen Reverse Proxy veröffentlichen. Die Dateiansicht beschränkt nicht die Dateisystemrechte eines ausdrücklich gestarteten externen Agenten.

## Tests und Abnahme

```sh
python3 -m unittest discover -s .suite/dashboard/tests -v
python3 .suite/tools/check_repository.py
node --check .suite/dashboard/web/app.js
```

Die HTTP-Tests öffnen kurz einen lokalen Port. Automatische Tests verwenden temporäre Dateien und kontrollierte Protokollereignisse; sie benötigen keine angemeldeten Agenten. Node ist nur für die optionale JavaScript-Syntaxprüfung erforderlich. Ein eigener GitHub-Actions-Job prüft das Dashboard mit Python 3.9 und 3.13.

Echte Providerprüfungen sind ausdrücklich getrennt und können die vorhandene Anmeldung verwenden und Providerkosten verursachen:

```sh
python3 .suite/dashboard/tests/live_smoke.py --profile all
python3 .suite/dashboard/tests/live_codex_e2e.py
```

Der erste Test fordert nur eine kurze Antwort ohne Werkzeuge an. Der zweite prüft zwei Codex-Sitzungen, das Schreiben einer **temporären** Testdatei durch Codex und externe Wiederaufnahme. Beide verändern keine Fachdateien der Suite. Die bestandenen Codex- und Pi-Prüfungen sowie die Grenzen der Abnahme stehen in [ABNAHME.md](ABNAHME.md).

## Schnittstellenquellen

Implementiert anhand der lokal installierten CLIs und ihrer offiziellen Protokolle:

- [Pi RPC](https://pi.dev/docs/latest/rpc)
- [Codex App Server](https://learn.chatgpt.com/docs/app-server)

Versionen und Testergebnisse sind im Abnahmeprotokoll dokumentiert. Bei Protokolländerungen wird nur der betreffende Adapter angepasst. Neue Adapter implementieren `connect`, `send`, `handle`, optional `respond`, und werden im Adapterregister ergänzt; Fachverzeichnisse benötigen keine Änderungen.

## Dieselbe Freigabeübersicht ohne Server

[Terminal-Werkzeug pending.py](../tools/pending.py) liest die konfigurierten Freigabeprotokolle ohne Dashboard-Start. `--config` wählt dieselbe Dashboard-Konfiguration; `--json` liefert strukturierte Ausgabe, `--strict` signalisiert offene Vorgänge mit Exit 1. Bei unklaren/gesperrten Protokollen oder Konfigurationsfehlern gilt Exit 2. Es werden weder Entscheidungen noch Dateien verändert. [Details](../APPROVALS.md).
