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
