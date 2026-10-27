# Installation und Migration

## Erste Installation

```sh
git clone https://github.com/markus-ertel/agentic-marketing-suite.git
cd agentic-marketing-suite
python3 .suite/tools/check_repository.py
```

Alternativ das GitHub-Archiv einschließlich versteckter Ordner entpacken. `.suite/` und die internen Modulordner sind notwendige Projektbestandteile. Es gibt keinen zentralen Paketmanager, Server oder Build-Schritt. Python 3.9 oder neuer wird nur für die lokalen Prüfwerkzeuge und Tests benötigt. Für Beratung ist eine geeignete KI-Laufzeit mit lesendem Zugriff erforderlich; externe Dienste müssen separat eingerichtet und autorisiert werden.

## Bestehende Arbeitsumgebung aktualisieren

1. Vorhandene Arbeitsumgebung einschließlich versteckter Ordner sichern. Personenbezogene Sicherungen geschützt und außerhalb öffentlicher Repositorys aufbewahren.
2. Den neuen Stand in eine getrennte Kopie klonen oder entpacken und dort prüfen.
3. Änderungen an `AGENT.md`, Methoden, Regeln, Schemas und Werkzeugen mit der vorhandenen Installation vergleichen und gezielt übernehmen.
4. Eigene Briefings, Kontaktdaten, Freigaben, Ergebnisse sowie `STATE.md`, `LOG.md` und `HISTORY.md` erhalten. Die mitgelieferten Anfangszustände dürfen aktive Arbeitsstände nicht ersetzen.
5. Bei Vertragsänderungen betroffene Adapter, gespeicherte Datensätze und Freigaben gesondert prüfen. Dieses Repository enthält derzeit keine automatische Datenmigration.
6. Die Repository-Prüfung und betroffene Akzeptanzfälle in der eigenen Laufzeit ausführen. Konten, Berechtigungen und externe Aktionen zunächst in einer Testumgebung prüfen.

Vor einem `git pull` in einer aktiv verwendeten Kopie lokale Änderungen sichern und den geplanten Diff kontrollieren. Produktive Daten möglichst in einer getrennten privaten Arbeitskopie halten; `.gitignore` allein ist keine vollständige Zugriffstrennung.

## Stand der ersten GitHub-Veröffentlichung

Die Suite bleibt bei v0.1, die README bei Dokumentationsstand v0.2. Ergänzt wurden Veröffentlichungsunterlagen, die gemeinsame Repository-Prüfung, GitHub-CI und das bislang fehlende fiktive Advertising-Manifest. Der Advertising-Test verwendet dessen modulrelativen Pfad. Bestehende Datenformate und Freigaben werden dadurch nicht migriert oder erweitert.

## Update Suite v0.1 → v0.2

- **Modulregeln (additiv):** Am Ende jeder Modul-`RULES.md` bzw. `noCRM/.nocrm/REGELN.md` steht der neue Abschnitt „Gemeinsame Suite-Mindeststandards“. Lokal angepasste Regeldateien nicht ersetzen, sondern den Abschnitt übernehmen.
- **Verträge (Bruch):** Gespeicherte Datensätze prüfen. `action-approval` mit `decision: approved` braucht `review_refs`; Ausführungsstatus außer `not_attempted` nur bei `approved`; `authorizer` darf kein KI-System sein. `review` mit `warning` braucht `risk_accepted_by`, `not_applicable` eine nicht leere Begründung in `notes` und keine `major`/`critical`-Befunde, `pass` darf keine `major`/`critical`-Befunde haben, `blocked` braucht einen. `approved`/`published`-Artefakte brauchen `sha256` und geklärte Rechte. Budgets bevorzugt als `budget_limit` + `currency`; `budget_limit_eur` bleibt gültig.
- **Querprüfung:** Für echte Außenwirkung Artefakt, Reviews und Freigabe gemeinsam mit `python3 .suite/tools/validate_records.py bundle <datei.json>` prüfen (Beispiel: `.suite/beispiele/demo-freigabe-bundle.json`).
- **Mapping:** Lokale Modulstatus und Freigabefelder über die Tabellen in `.suite/INTERFACES.md` in Suite-Verträge übersetzen.
- **website/:** Neue Ordner `.nocms/HISTORY/` (Register `README.md`), `.nocms/KNOWLEDGE/` (Inventar `README.md`), `input/` und `archiv/`. Bei einer laufenden Website vorhandene Ordner nicht ersetzen, nur Fehlendes ergänzen und bisherige Historie ins Register aufnehmen. Geändert: `AGENT.md` (Projektwurzel/Suite-Betrieb, Veröffentlichungsgrenze, Nachbarmodule, Release-Hash), `.nocms/BERATUNG.md`, `.nocms/STATE.md`, `.nocms/ARCHITECTURE.md`, `.nocms/TESTFAELLE.md` (B25–B29). In Suite-Datensätzen beginnen Website-Pfade mit `website/`, in noCMS-Dokumenten ohne Präfix.
- **marketing/:** In `.marketing/BERATUNG.md` wurden nicht existente Modulnamen korrigiert.
- **e-commerce/ (neues Modul, additiv):** Ordner `e-commerce/` vollständig übernehmen (`AGENT.md`, `.e-commerce/`, `input/.gitkeep`, `archiv/.gitkeep`). Vorhandene eigene Shop-Unterlagen nicht in `.e-commerce/` legen, sondern in Ergebnisordner wie `e-commerce/katalog/` oder `e-commerce/feeds/`. Wer bisher Produktfeeds in `advertising/` gepflegt hat, überträgt den Katalog nach `e-commerce/` und lässt `advertising/` darauf verweisen.
- **Verträge (additiv):** `e-commerce` ist neuer zulässiger Wert in `work-order.lead_module`, `work-order.supporting_modules` und `artifact.owner_module`. Bestehende Datensätze bleiben gültig; Adapter oder eigene Validatoren mit fest kodierter Modulliste ergänzen. `action-approval` bleibt unverändert: E-Commerce-Aktionen nutzen `publish`, `modify_external` oder `delete` mit `target` `ecommerce:<aktion>:…` (`.e-commerce/AKTIONEN.md`).
- **Prüfung:** `check_repository.py` und `.suite/tests/test_module_structure.py` kennen neun Module, führen die E-Commerce-Tests und die Demo-Preflights aus und prüfen, dass Schema-Enums, `.suite/MODULES.md` und Prüfskript übereinstimmen. Lokale Forks mit eigenen Modulen müssen diese drei Stellen gemeinsam pflegen.
- **Mapping:** `.suite/INTERFACES.md` enthält eine Spalte für e-commerce sowie Feed-Status (`valid`/`warning`/`rejected`, Übertragung) und ein Bestellstatus-Mapping für `analytics/`.

## Update Suite v0.2 → v0.2.1

- **Installation:** Den Release `v0.2.1` verwenden oder gezielt dessen Tag auschecken. Bestehende Kunden-/Arbeitsdaten und lokale Anpassungen wie oben beschrieben erhalten. Keine automatische Datenmigration; die JSON-Vertragsversionen bleiben unverändert.
- **Dashboard:** Server beenden, die aktualisierten Dashboard-Dateien übernehmen und neu starten. Ein bereits laufender Prozess verwendet weiterhin den alten Code. Nur über eine lokale Loopback-Adresse betreiben.
- **Interne Dateien:** `suite.show_internal_files` ist jetzt eine serverseitige Zugriffserlaubnis und bleibt standardmäßig `false`. Wer interne Methoden im Dashboard benötigt, setzt den Wert in der eigenen Konfiguration ausdrücklich auf `true` und startet den Server neu. `.suite/` bleibt zugänglich; bekannte Zugangsdatenpfade und Schlüsseldateien bleiben immer gesperrt. Reguläre Arbeitsdateien werden nicht allein wegen eines `.gitignore`-Eintrags gesperrt. Geheimnisse weiterhin außerhalb des Suite-Roots speichern.
- **Eigene HTTP-Clients:** Für Dashboard-Anfragen eine erlaubte lokale Adresse mit dem tatsächlichen Port verwenden. POST benötigt zusätzlich den dazu passenden HTTP-Origin. Der mitgelieferte Browserclient funktioniert ohne zusätzliche Einrichtung.
- **Modulstart:** Eine Begrüßung löst auch bei vorhandenem STATE keine Wiederaufnahme aus. Zum Fortsetzen ausdrücklich auf den Vorgang Bezug nehmen. Neue konkrete Aufträge beginnen ohne erneutes Onboarding; vorhandene passende Arbeitsstände werden weiterverwendet.
- **Optionale Quellen:** PR, Social Media, Creative und noCRM können ausdrücklich referenzierte Analytics-Berichte berücksichtigen. Advertising nutzt E-Commerce optional als Feed-Quelle und meldet Findings an dessen Schreib-Owner; Analytics nutzt optionale aggregierte Shop-/Funnel-Daten. Kein Nachbarmodul wird zur Pflicht.
- **Prüfung:** `python3 .suite/tools/check_repository.py`, die Dashboard-Tests laut dessen README und bei eigenem Harness die dokumentierten Start-/Rückkopplungsfälle prüfen. Die neuen Quellen- und `.gitkeep`-Dateien ergänzen, ohne eigene Inhalte zu überschreiben.

## Update Suite v0.2.1 → v0.2.2

Die Human Approval & Audit Trail Capability v0.1 ist eine additive Erweiterung. Bestehende produktive Arbeitsdaten und die vier bisherigen Kernverträge benötigen keine automatische Migration. Den neuen Release übernehmen und einen laufenden Dashboard-Server neu starten.

- Neue Anleitung `.suite/APPROVALS.md`, Verträge `approval-request` / `approval-event` und lokales Werkzeug `.suite/tools/approval_audit.py`. Die bisherigen vier JSON-Verträge und bestehende Daten bleiben unverändert; alte Freigaben werden nicht automatisch importiert oder als neu bestätigte Menschenentscheidungen ausgegeben.
- Optional in den eigenen Harness integrieren: konkrete Anfrage vorlegen, tatsächliche Person und Berechtigung über einen vertrauenswürdigen Kanal erfassen, Entscheidungen samt Evidenzreferenz protokollieren und vor Ausführung immer den neuesten vollständigen Zustand prüfen. Eine frühere `approved`-Zeile oder zwischengespeicherte Statusansicht genügt nicht.
- Private Logdateien im Arbeits-/Vorgangsverzeichnis außerhalb `.suite/` anlegen, Dateirechte und Aufbewahrung festlegen. Die mitgelieferten Demo-Logs sind ausschließlich fiktiv und dürfen nicht als echte Freigaben übernommen werden.
- Alle Module verweisen optional auf diese Fähigkeit. Standalone-Betrieb und strengere lokale Regeln bleiben erhalten. Das Dashboard erhält keine neue Schreib- oder Ausführungsfunktion.

- **Optionale Dashboard-Anzeige:** In der eigenen Dashboard-Konfiguration `approvals.logs` mit eindeutigem `id`, lesbarem `label` und lokalem JSONL-`path` ergänzen und den Server neu starten. Relative Pfade beziehen sich auf die Konfigurationsdatei. Standardmäßig keine Quellen, keine automatische Übernahme der fiktiven Beispiele; Entscheidungs- und Ausführungsrechte bleiben beim Harness.

## Update v0.2.2 → v0.2.3: optionale technische Fähigkeiten

- Neue Quelle `.suite/capabilities/REGISTRY.md`, maschinenlesbare Capability-/Ausführungsverträge und fachlich zugeordnete Adapter/Minimodule. Vorhandene vier Kernverträge, Approval-Audit-Daten und Kundenartefakte werden nicht automatisch migriert. Keine Konten, Live-Hostings oder Serverdienste werden bei einem Suite-Update aktiviert.
- **SFTP:** OpenSSH installieren/bereitstellen, separaten Host-Key unabhängig prüfen, Schlüssel über externe Credential-Referenzen bereitstellen. Erst ein passendes unveränderliches Website-ZIP und den freizugebenden Datei-/Hash-Plan erzeugen; Root, Source, konkretes Ziel und ZIP-Referenz beachten. Keine Remote-Löschung, kein Klartext-FTP-Fallback, kein automatischer Retry nach unklarem Transfer.
- **Mail:** Konto-Beschreibung ohne Passwort übernehmen, Credentials im Harness speichern, Leserechte/Mailboxen ausdrücklich aktivieren. Lokale EML und Pläne in privaten Arbeitsordnern erzeugen. Erst nach fachlichem/rechtlichem Review und konkreter Freigabe ausführen. Gmail/Graph/OAuth sind noch keine Implementierungen. SMTP-Annahme nicht als Zustellung ausgeben.
- **Website:** Nur ausgewählte Dateien mit `website/.nocms/tools/webmodules.py` übernehmen; bestehende lokale Anpassungen manuell vergleichen. PHP 8.3+ nur bei gewähltem PHP-Modul. Private Konfiguration, Secret und `data_dir` außerhalb des öffentlichen Webroots einrichten. Musterdienste bleiben deaktiviert, bis ein begrenzter echter Serviceauftrag mit Ablauf und Datenschutzinformation freigegeben ist.
- **Newsletter/Analytics:** Konkreten Zweck, Textversion, DOI-/Abmeldeablauf bzw. feste Messrouten und Aufbewahrung prüfen. Bestehende personenbezogene Daten nicht ungefragt importieren. Tägliche Host-Wartung für abgelaufene/alte Daten einrichten; Webserver-Logs und organisatorische Löschrechte separat behandeln.
- **Statische Module:** Suchindex/Sitemap nach öffentlichen HTML-Änderungen neu erzeugen. Kein automatisches Verständnis von Server-Zugriffsschutz. Apache-Regeln vor Deployment am tatsächlichen Hosting prüfen; vorhandene `.htaccess` wird nicht ersetzt.
- **Prüfung:** Gemeinsame Repository-Prüfung, `node --test website/.nocms/tests/test_browser_modules.cjs`, tatsächliche PHP-HTTP-Tests und autorisierte Hoster-/Providerabnahme durchführen. Offline-Tests und Test-Outboxes ersetzen keine Produktionsabnahme. Private `executions.jsonl` werden wie Freigabeprotokolle von Git ausgeschlossen.

## Update v0.2.3 → v0.2.4: Branding

- `branding/` einschließlich verstecktem `.branding/` übernehmen, eigene Arbeitsdaten und bestehende freigegebene Markenversionen erhalten. Die beigelegten Beispiele sind fiktiv; keine eigenen Markenentscheidungen daraus ableiten.
- Modulregister, gemeinsame Anweisungen und die additiven Enums `branding` in `work-order` und `artifact` übernehmen. Eigene Validatoren mit fest kodierten Modullisten entsprechend ergänzen; bestehende Datensätze bleiben gültig.
- Nachbarmodule erhalten optionale Übergaben. Markenentscheidungen, Unternehmensfakten und gemessene Wahrnehmung getrennt halten; keine Business-DNA-Installation voraussetzen. Regeln und Mapping: [Branding in der Suite](branding/.branding/SUITE.md).
- Dashboard für aktualisierte Modulnamen neu starten. Interne Dateien bleiben abhängig von `suite.show_internal_files` gesperrt; die Integration erweitert keine Zugriffsrechte.
- Repository-Prüfung und Branding-Vertragstests ausführen. Fachliche Beratung und echte Markenreviews nach den lokalen Akzeptanzfällen gesondert prüfen; formale Tests belegen keine Markenqualität oder Rechtsfreiheit.

## Update v0.2.3 → v0.2.4: Business-DNA

- `business-dna/` einschließlich `.business-dna/` übernehmen. Eigene Wissensbestände und Entscheidungen erhalten; fiktive Beispiele nicht als neue geprüfte Unternehmensfakten verwenden.
- `business-dna` additiv in Modulregister und Suite-Enums `work-order`/`artifact` übernehmen. Eigene Validatoren mit fest kodierten Modullisten aktualisieren. Vorhandene Daten bleiben gültig; kein automatischer Import.
- Operative `wissen/`, `unternehmen/`, `angebote/`, `kontext/`, Eingänge und Archive standardmäßig aus Git ausschließen. Schon eingecheckte Daten werden durch `.gitignore` nicht aus der Historie entfernt; vorhandene Bestände bewusst prüfen.
- Context Packs nach Zweck und tatsächlicher Empfängerberechtigung nutzen. Claim-/Quellenstatus und Produktreife getrennt halten; Branding nutzt Fakten als Ausgangslage. `as_of` ist keine historische Rekonstruktion. [Übergaben, CLI und Statusmapping](business-dna/.business-dna/SUITE.md).
- Die bestehenden CLI-Einzelparameter bleiben gültig; alternativ `--request` mit einem lokalen Context-Request verwenden. Dashboard für die aktualisierten Bezeichnungen neu starten. Keine neue Wissens-, Freigabe- oder Zugriffskontrollinstanz.
- Repository- und Dashboard-Prüfungen sowie Modul-Vertragstests ausführen. Fachliche Quellenprüfung und dialogische Harness-Akzeptanz bleiben bei konkreter Nutzung erforderlich.

## Update v0.2.3 → v0.2.4: Help & Learning

- `help/` einschließlich `.help/` übernehmen; bestehende Arbeitsdaten, Logs und Module erhalten. Die ursprünglichen Paketunterlagen bleiben separat unter `help/`; keine Root-Dateien durch Paketkopien ersetzen.
- `help` additiv in Modulregister und Suite-Enums `work-order`/`artifact` ergänzen; lokale Help-Schemas bleiben optional. Alle Fachbereiche funktionieren ohne Help weiter.
- Dashboard für die neue Bezeichnung neu starten. Den bestehenden Harness-Chat und die bewusste Dateireferenz nutzen; es gibt keine automatische Sitzung oder neue Help-API. Interne Dateien behalten ihre bestehenden Zugriffssperren.
- Help vor Funktionsauskünften auf die tatsächliche Installation, passende Quellen und überprüften Testumfang verweisen. Historische Angaben aus dem Paket sind keine aktuelle Versionsgarantie. [Konkrete Integration](help/.help/SUITE.md).
- Individuelle Anleitungen/Lernnotizen geschützt außerhalb der Bibliothek ablegen. Paket-/Integrationstests ausführen; die dialogischen Akzeptanzfälle und echte Verständlichkeit zusätzlich im Harness prüfen.

## Unveröffentlicht: Harness-Einstieg

`CLAUDE.md`, `AGENTS.md` und `.cursor/rules/suite.mdc` verweisen auf die bestehenden Regeln. Entwicklung und Marketingaufträge bleiben getrennt. Die Claude-Code-Befehle unter `.claude/commands/` bereiten Arbeit vor, erteilen keine menschliche Freigabe und führen keine Außenaktionen aus. Nach Installation im tatsächlichen Harness prüfen: Einstieg ohne Auftrag, direkter Fachauftrag, Entwicklungsauftrag und Zugriff auf die ausgewählte Kontextquelle. Ein bestandener Repository-Test belegt die automatische Übernahme dieser Dateien nicht.

## Unveröffentlicht: Plattform-Importdateien

Advertising-Manifeste erlauben additiv `search_ads`; bestehende Manifeste bleiben gültig. Eigene Validatoren bei Nutzung dieses Blocks aktualisieren. [Exportwerkzeug](.suite/tools/EXPORT_PLATFORM.md) erzeugt nur lokale freigabegebundene Importdateien. Scheduler-CSV unterstützt nur Text/Einzelbild, benötigt bei Planzeiten die tatsächliche Zielzeitzone und verwirft keine zusätzlichen Assets. Google-Ads-Kampagnen bleiben pausiert; Laufzeit-/Kontoeinstellungen und tatsächliche Ausgabengrenzen vor Aktivierung prüfen. Eine echte Importabnahme steht aus.

## Unveröffentlicht: Google-Leseadapter

Der optionale GA4-/Search-Console-Adapter benötigt ein berechtigtes Konto und extern bereitgestellte read-only OAuth-Credentials. Für GA4 die tatsächliche `--time-zone` angeben; GSC verwendet fest `America/Los_Angeles`. Der additive Tagesexport enthält keine eindeutigen `totalUsers`. CSV/Manifest bleiben privat und werden nicht überschrieben. Details und Grenzen: [FETCH_GOOGLE.md](analytics/.analytics/tools/FETCH_GOOGLE.md). Eine echte Kontoabnahme steht separat aus.
