# Dashboard – Umsetzung und Abnahmenachweis

Stand: **26. Oktober 2026**. Veröffentlichungsumfang: **Codex und Pi**, entsprechend der aktuellen Festlegung des Nutzers. Die ursprüngliche Roadmap enthielt einen weiteren Anbieteradapter; dieser gehört nicht zu dieser Veröffentlichung. Die lokalen Planungsdateien werden nicht ins Repository übernommen. Dieses Protokoll unterscheidet implementierte Funktionen, automatisierte Tests und reale Providerabnahmen.

## Ergebnis nach Roadmap

| Meilenstein | Umsetzung / Nachweis |
|---|---|
| P0 | Additive Komponente unter `.suite/dashboard/`; vorhandene acht Fachmodule und `.suite` festgestellt; keine Fachdateien geändert |
| M1.1 | Python-HTTP-Server; JSON-Konfiguration; relative Root-Auflösung; Port `0`; ausgegebene Adresse; Start-/Stop-Anleitung |
| M1.2 | Reale, sortierte Navigation; lazy Unterverzeichnisse; interne Ordner per Schalter; Pfadsuche; Pfad kopieren |
| M1.3 | Markdown einschließlich Tabellen/Code; Text/JSON/JSONL/CSV; Bilder/SVG, HTML, PDF und Browsermedien; Quelltextansicht; Downloadfallback |
| M1.4 | Reload, gezieltes Metadatenpolling, externe Änderungen/Löschungen; responsive Panels und verständliche Dateipfade |
| M1.5 | Tests mit echtem Suite-Baum und temporären Format-/Änderungsfixtures; lokaler HTTP-Test auf Port `0` ohne Agenten; Browser-Markdownprüfung |
| M2.1 | Dünner Adaptervertrag; neutrale Status-/Text-/Interaktions-/Fehler-/Abschlussereignisse; Fähigkeitsanzeige |
| M2.2 | Pi-RPC implementiert; `get_state`, Prompt, Textdeltas, Dialoge, `agent_settled`, Session-/Modellinformationen. Reale Verbindung, inkrementelle Antwort und bestätigter Modellturn nach Start des lokalen Modellservers bestanden |
| M2.3 | Einblendbarer Chat; unabhängige Auswahl von Agent und Arbeitsverzeichnis; sichtbare Dateireferenz und AGENT.md-Einstieg nur als Benutzerentwurf |
| M2.4 | Codex App Server mit Initialisierung, Threadstart/-resume, Turns, Streaming und Rückfragen. Reale Text- und Dateitests bestanden |
| M2.6 | Nicht verbunden, bereit, arbeitet, wartet auf Eingabe, abgeschlossen, Fehler und unbekannt; fehlende Programme und Prozessabbrüche; keine erfundenen Fortschritte |
| M3.1 | Periodisches Prüfen sichtbarer Ordner und offener Datei; unveränderte Verzeichnisansichten bleiben erhalten; neue Dateien gekennzeichnet |
| M3.2 | Mehrere getrennte beobachtbare Sitzungen mit Fachkontext, Modell, externen Referenzen und letztem Ereignis; SSE-Replay nach Browserreload |
| M3.3 | Explizite Dateireferenz, Fachbereichübernahme für neue Verbindungen, anklickbare im Chat genannte Suite-Pfade |
| M3.4 | Suche, zuletzt geöffnet, angeheftete Dokumente ausschließlich im Browser; lazy Navigation, Vorschaugrenzen, Streaming, Tastaturbedienung |
| M3.5 | Automatisierte HTTP-/Protokolltests und reale Codex-Tests mit zwei Sitzungen, getrennten Verzeichnissen, extern geschriebener Datei und Wiederaufnahme |

Nicht benötigt und entsprechend nicht eingebaut: optionale Volltextsuche, Versionsvergleich, zusätzliche Themes und Dokumentexport. Keine Inhaltsdatenbank, keine fachliche Workflow-Engine, kein Agentengedächtnis, keine Web-Dateibearbeitung.

## Automatisierte Prüfung

**16 Dashboardtests bestanden**, mit Python 3.9.6:

- Navigation des realen Suite-Baums und aller neun Einstiegspunkte;
- verborgene Verzeichnisse, Suche, dynamisch neue Dateien;
- Markdown-Tabellen, Codeblöcke, relative Verweise und HTML-Escaping;
- JSON/JSONL/CSV/HTML/SVG/PDF/Text beziehungsweise klarer Formatfallback;
- Vorschaugrenzen, Dateiveränderung und Löschung, unveränderte gelesene Inhalte;
- relative Konfiguration, abweichender Port und ungültige Konfigurationswerte;
- HTTP-Routen, Bytebereiche für Medien und getrennte HTML-Ressourcen;
- fehlende CLI, Protokollstatus, Fehler gegenüber tatsächlichem Abschluss;
- zwei getrennte Sitzungen, begrenzter Ereignispuffer und Wiederverbindung ohne erfundene Erfolgsmeldung.

Zusätzlich: JavaScript-Syntaxprüfung bestanden; bestehender Repositorycheck mit sämtlichen vorhandenen Modulprüfungen, lokalen Markdown-Linkzielen, JSON-Dateien und Demo-Preflights bestanden. Der neue CI-Job ist für Python 3.9 und 3.13 eingerichtet; ein GitHub-Lauf wurde lokal nicht behauptet.

Die automatisierten Medienfixtures prüfen Transport, Typauswahl und Fallback, keine plattformübergreifende Codec- oder PDF-Renderer-Zertifizierung.

## Reale Integrationstests

Geprüfte Programme: **Pi 1.4.0** und **Codex CLI 0.164.0-alpha.11.1**.

| Test | Beobachtung | Ergebnis |
|---|---|---|
| Pi verbinden | `get_state` bestätigt Sitzung/Modell, Status `bereit`; bei Prompt `arbeitet` | Verbindung bestanden |
| Pi vollständiger Turn | Nach Start des lokalen Modellservers: `bereit`, `arbeitet`, inkrementelle Antwort `DASHBOARD_OK`, bestätigter Abschluss `abgeschlossen`, keine Fehler. Zuvor war der konfigurierte Endpunkt `http://127.0.0.1:1234/v1` für Modell `lfm2.5-8b-a1b-mlx` nicht erreichbar | Bestanden |
| Codex Textturn | `arbeitet`, inkrementeller Text `DASHBOARD_OK`, bestätigter Turnabschluss | Bestanden |
| Codex zwei Sitzungen | Unterschiedliche externe Thread-IDs, `marketing` und `creative` als getrennte temporäre Arbeitsverzeichnisse | Bestanden |
| Codex externe Dateiveränderung | Codex schreibt `marketing/probe.txt`; Files-API liest `DASHBOARD_FILE_OK`; zweites Verzeichnis bleibt leer | Bestanden |
| Codex externe Wiederaufnahme | Verbindung geschlossen; gleicher externer Thread über `thread/resume`; Folgeturn abgeschlossen | Bestanden |
| Codex Browser-Chat | Nachricht im Browser gesendet; `arbeitet`; Antwort `DASHBOARD_BROWSER_OK`; Status `abgeschlossen` | Bestanden |
| Browseransicht neu laden | Bestehende serverseitige Verbindung wird wieder ausgewählt; Ereignisse werden rekonstruiert | Bestanden |

Alle Testdateien lagen in automatisch angelegten temporären Verzeichnissen. Im realen Codex-Dateitest wurde ausschließlich der geprüfte lokale Befehl zum Schreiben von `probe.txt` beziehungsweise die entsprechende externe Dateifreigabe bestätigt. Der normale Dashboardadapter trifft selbst keine Freigabeentscheidung und ändert keine Anbieterberechtigungen.

## Abnahmegates

- **Gate P0: bestanden.** Additive Implementierung, Suite-Baum unverändert.
- **Gate 1: bestanden.** Dateidashboard unabhängig von Agenten nutzbar; Formate und Fallbacks, konfigurierbarer Port und externe Aktualisierungen geprüft.
- **Gate 2 im Veröffentlichungsumfang Codex/Pi: bestanden.** Echte bidirektionale Kommunikation mit Streaming und bestätigtem Abschluss für beide Anbieter geprüft. Der ursprünglich zusätzlich vorgesehene Anbieteradapter ist aus dem Veröffentlichungsumfang entfernt.
- **Gate 3 im Veröffentlichungsumfang Codex/Pi: bestanden.** Gemeinsame Datei-/Chatansicht, Live-Aktualisierung und Browser-Wiederverbindung geprüft; mehrere echte Sitzungen, getrennte Arbeitsverzeichnisse, externe Dateierstellung und Wiederaufnahme mit Codex geprüft. Eine vollständige Prüfung sämtlicher optionaler Dialog- und Wiederaufnahmeszenarien mit Pi ist damit nicht behauptet.

Für weitere Pi-Turns muss der konfigurierte Modellserver erreichbar bleiben. Bei Änderungen an CLI-Versionen oder Providerkonfiguration die opt-in Live-Tests aus der [Startanleitung](README.md) wiederholen. Es sind dafür keine Änderungen an den Fachmodulen erforderlich.
