# noCMS — STATE.md

**Aktueller Projektzustand, Übergabe und nächster sicherer Schritt**  
**Spezifikationsstand:** v0.1  
**Ablage im Projekt:** `.nocms/STATE.md`  
**Vorlagenstatus:** `NICHT INITIALISIERT — keine konkrete Website inventarisiert`

> **Zweck:** Diese Datei ist die kurze, belastbare Momentaufnahme eines noCMS-Projekts. Ein neues KI-System soll zuerst erkennen, **was tatsächlich existiert**, **was zuletzt geschehen ist**, **was offen oder blockiert ist** und **welcher Schritt als Nächstes erlaubt und sinnvoll ist**. Sie ist weder Änderungsprotokoll noch Ersatz für die Prüfung der realen Dateien.

## 1. Pflege- und Wahrheitsregeln

- Lies zuerst `AGENT.md` und `.nocms/RULES.md`. Nutze dieses Dokument zur Orientierung; prüfe bei konkreten Arbeiten die betreffenden Dateien unter `site/`, `shared/`, `input/` und `archiv/` selbst.
- **Beobachtet**, **bestätigt**, **geplant** und **nicht geprüft** sind unterschiedliche Zustände. Kennzeichne sie ausdrücklich. Erfinde weder Testresultate noch Freigaben, Zeitpunkte, Veröffentlichungen oder Dateibestände.
- `OFFEN`, `NICHT ERMITTELT` und `NICHT GEPRÜFT` bedeuten nicht „nein“, „fehlt“ oder „freigegeben“.
- Halte die Zusammenfassung aktuell und knapp. Details zu Anforderungen gehören in `BRIEFING.md`, Seiten und Komponenten in `STRUCTUR.md`, technische Begründungen in `ARCHITECTURE.md`, verbindliche Regeln in `RULES.md` sowie abgeschlossene Vorgänge in `HISTORY/`.
- Verwende relative Projektpfade, eindeutige Aufgabenkennungen und nachvollziehbare Daten im Format `YYYY-MM-DD HH:MM` mit Zeitzone. Bei unbekannten Angaben nicht den aktuellen Zeitpunkt als Ereignisdatum ausgeben.
- Ändere `STATE.md` nach jedem relevanten Arbeitsabschnitt und insbesondere nach Onboarding, Importen, größeren Änderungen, Prüfungen, Freigaben, Veröffentlichungen, Fehlern und Rollbacks. Entferne abgeschlossene Aufgaben aus der aktiven Liste **erst**, wenn ihr Ergebnis dokumentiert bzw. in `HISTORY/` nachgewiesen ist.
- Notiere **keine** Passwörter, Token, API-Schlüssel, personenbezogenen Rohdaten oder vertraulichen Inhalte. Verweise bei Bedarf nur auf sichere Ablageorte, niemals auf den geheimen Wert selbst.

---

## 2. Projektlage auf einen Blick

*Beim ersten Einsatz anhand des tatsächlichen Projekts ausfüllen. Die folgenden Einträge sind bewusst keine behaupteten Ist-Daten.*

| Feld | Aktueller Wert |
| --- | --- |
| Projektname / Website | `OFFEN` |
| Betriebsart | `OFFEN — standalone / Modul website/ der Agentic Marketing Suite` |
| Projektart | `OFFEN — Neu / Redesign / Adaptierung / Übernahme` |
| Projektphase | `NICHT ERMITTELT` |
| Arbeitsstatus | `NICHT ERMITTELT` |
| Verantwortliche / Freigabestelle | `OFFEN` |
| Basis-URL / Zielumgebung | `OFFEN` |
| Letzte verifizierte Bestandsaufnahme | `NICHT ERFOLGT` |
| Letzte Änderung dieser STATE.md | `OFFEN` |
| Letzte prüfende KI / Werkzeugumgebung | `NICHT ERMITTELT` |
| Aktueller Arbeitsauftrag | `KEIN AUFTRAG ERFASST` |
| Gesamtrisiko / wesentliche Blockade | `NICHT BEURTEILT` |

**Kurzlage (maximal 3–5 Sätze):**  
`Noch keine verifizierte Projektlage dokumentiert. Bei der Initialisierung zuerst reale Dateien, vorhandenes Briefing, Regeln und etwaige Releases inventarisieren.`

**Nächster sinnvoller und autorisierter Schritt:**  
`Projektinventur durchführen und bestehende Vorgaben lesen; vor Veröffentlichung oder irreversiblen Änderungen Berechtigung und Freigabe prüfen.`

## 3. Projektbasis und Dokumentationsstand

| Bereich | Zustand | Letzter Abgleich / Hinweis |
| --- | --- | --- |
| `AGENT.md` | `NICHT GEPRÜFT` | — |
| `.nocms/ONBOARDING.md` | `NICHT GEPRÜFT` | — |
| `.nocms/BRIEFING.md` | `NICHT GEPRÜFT` | Bestätigungsstatus offen |
| `.nocms/STRUCTUR.md` | `NICHT GEPRÜFT` | Seiten-/Komponentenabgleich offen |
| `.nocms/ARCHITECTURE.md` | `NICHT GEPRÜFT` | Technischer Ist-Abgleich offen |
| `.nocms/RULES.md` | `NICHT GEPRÜFT` | Projektspezifische Bestätigungen offen |
| `.nocms/KNOWLEDGE/` | `NICHT ERMITTELT` | Inventar in `KNOWLEDGE/README.md`; Quellen offen |
| `.nocms/HISTORY/` | `NICHT ERMITTELT` | Register in `HISTORY/README.md`; bisherige Einträge offen |
| `input/`, `archiv/` (`inputs/`, `releases/`) | `NICHT ERMITTELT` | `input/` und `archiv/` vorhanden; Unterordner entstehen beim ersten Import bzw. Release |
| `site/` | `NICHT INVENTARISIERT` | Bestand und lokale Prüfbarkeit offen |
| `shared/` | `NICHT ERMITTELT` | Optionale Komponentenquellen |

**Onboarding:** `NICHT ERMITTELT`  
**Briefingstatus:** `NICHT ERMITTELT — Entwurf / Zur Prüfung / Bestätigt`  
**Wesentliche noch ungeklärte Anforderungen:** `OFFEN`

> Eine vorhandene Datei ist nicht automatisch aktuell oder bestätigt. Bei Abweichungen zwischen Projektdokumentation, Nutzerauftrag und realem Website-Code den Konflikt unten festhalten; nichts stillschweigend umdeuten.

## 4. Website- und Versionsstand

### 4.1 Tatsächlicher lokaler Websitezustand

| Merkmal | Wert / Nachweis |
| --- | --- |
| Öffentliche Dateien innerhalb des Projekts | `site/` |
| Inventarisierte HTML-Dateien | `NICHT ERMITTELT` |
| Erkannte Layoutvarianten | `NICHT ERMITTELT` |
| Gemeinsame Komponenten / Marker | `NICHT ERMITTELT` |
| Besondere Seiten / Sprachvarianten | `NICHT ERMITTELT` |
| Letzte Prüfung von Seiten und Komponenten gegen `STRUCTUR.md` | `NICHT GEPRÜFT` |
| Aktueller lokaler Arbeitsstand (z. B. Commit/Hash, falls vorhanden) | `NICHT ERMITTELT` |
| Nicht abgeschlossene lokale Änderungen | `NICHT ERMITTELT` |

Der **lokale Websitezustand** in `site/` ist nicht automatisch derselbe wie die aktuell live veröffentlichte Website. Die Versionsnummer eines Releases ist ebenfalls nicht die Versionsnummer dieser noCMS-Vorlage.

### 4.2 Veröffentlichung und Release-Archiv

| Merkmal | Wert / Nachweis |
| --- | --- |
| Letzte **nachweislich veröffentlichte** Version | `NICHT ERMITTELT` |
| Zeitpunkt der bestätigten Veröffentlichung | `NICHT ERMITTELT` |
| Live-URL / Zielumgebung | `OFFEN` |
| Nachweis der tatsächlichen Live-Prüfung | `NICHT VORHANDEN / NICHT ERMITTELT` |
| Zugehöriges vollständiges ZIP unter `archiv/releases/` | `NICHT ERMITTELT` |
| Archivprüfung / Prüfsumme (falls erstellt) | `NICHT GEPRÜFT` |
| Zuletzt vorbereitetes, noch nicht bestätigtes Release | `KEINES ERFASST` |
| Veröffentlichungsstatus dieses vorbereiteten Releases | `NICHT ZUTREFFEND` |
| Zuletzt bekannter funktionierender Rollback-Punkt | `NICHT ERMITTELT` |
| Letzter Release-/Rollback-Eintrag in `HISTORY/` | `NICHT ERMITTELT` |

**Verbindliche Unterscheidung:**

- `Veröffentlichung vorbereitet`: geprüftes Paket liegt vor, ist aber noch nicht nachweislich live.
- `Veröffentlicht`: der entsprechende Deploymentzustand wurde tatsächlich bestätigt; das vollständige ZIP gehört unverändert ins Releasearchiv.
- `Fehlgeschlagen / Blockiert`: Deployment, Prüfung oder Nachweis ist gescheitert; eine vorbereitete Version darf **nicht** als veröffentlicht gelten.
- Ein bestehendes ZIP allein beweist keine erfolgreiche Veröffentlichung; eine vorhandene Website allein beweist nicht, dass ein korrektes Archiv existiert.
- Vor Rollback den aktuellen Zustand sichern und Berechtigungen prüfen. Ein Rollback der Website setzt Briefing, Regeln oder Projektwissen nicht automatisch zurück.

## 5. Aktueller Arbeitsauftrag und Übergabe

*Dieser Abschnitt beschreibt nur die gerade aktive oder unmittelbar nächste Arbeit, nicht die gesamte Projektgeschichte.*

| Feld | Eintrag |
| --- | --- |
| Auftrag-ID | `KEINE` |
| Auftrag / gewünschtes Ergebnis | `OFFEN` |
| Auslöser / bestätigende Quelle | `OFFEN` |
| Verantwortliches ausführendes System (falls bekannt) | `OFFEN` |
| Betroffene Seiten, Komponenten und Dokumente | `NOCH NICHT ERMITTELT` |
| Arbeitsstatus | `NICHT ERMITTELT` |
| Bereits fertiggestellte Teilschritte | `KEINE VERIFIZIERT` |
| Noch ausstehende Teilschritte | `OFFEN` |
| Abhängigkeiten und Risiken | `OFFEN` |
| Erforderliche Prüfung / Freigabe | `OFFEN` |
| Sicherer Wiedereinstieg | `Ist-Zustand kontrollieren, Auftrag und Freigaben verifizieren` |

**Übergabenotiz für eine andere KI:**  
`Keine Implementierung, Änderung oder Veröffentlichung als abgeschlossen annehmen, solange sie nicht anhand von Dateien und dokumentierten Prüfungen nachvollzogen werden kann. Vor der Fortsetzung ungesicherte Änderungen und mögliche Konflikte prüfen.`

Für mehrere parallele Aufgaben verwende die Aufgabenübersicht in Abschnitt 6 und kennzeichne Konflikte bei denselben Dateien. Ein Eintrag in `STATE.md` ist **keine Dateisperre** und ersetzt keine Koordination gleichzeitiger Bearbeitungen.

## 6. Offene Aufgaben und Entscheidungen

### 6.1 Aufgabenliste

| ID | Aufgabe / erwartetes Ergebnis | Priorität | Status | Abhängigkeit / nächster Schritt |
| --- | --- | --- | --- | --- |
| `TASK-001` | Projekt initial inventarisieren und Vorlagen projektspezifisch ausfüllen | `OFFEN` | `Nicht begonnen` | Ist-Dateien und vorhandene Freigaben prüfen |

**Vorgeschlagene Prioritäten:** `Kritisch`, `Hoch`, `Normal`, `Niedrig`.  
**Aufgabenstatus:** `Nicht begonnen`, `In Bearbeitung`, `Zur Prüfung`, `Blockiert`, `Abgeschlossen`.  
Ein Abschluss setzt überprüfbare Ergebnisse voraus. Aufgaben dürfen ohne neue Version veröffentlicht werden, solange kein Deployment behauptet wird.

### 6.2 Offene Entscheidungen und Freigaben

| ID | Thema / Entscheidung | Erforderliche Person oder Evidenz | Konsequenz bei Nichtklärung | Status |
| --- | --- | --- | --- | --- |
| *Noch keine konkrete Entscheidung erfasst* | — | — | — | — |

Eine Briefingbestätigung ist **keine pauschale Veröffentlichungsfreigabe**. Fehlt die nötige Autorisierung für Hostingzugriffe, Domains, Löschen von Daten oder andere folgenreiche Schritte, bearbeite nur sicher erlaubte Teile und halte die Grenze fest.

### 6.3 Bekannte Probleme, Risiken und Widersprüche

| ID | Problem / betroffene Stelle | Auswirkung | Beleg / Entdeckung | Maßnahme / Status |
| --- | --- | --- | --- | --- |
| *Noch nicht untersucht* | — | — | `NICHT GEPRÜFT` | — |

Erfasse hier insbesondere widersprüchliche Angaben zwischen Dokumentation und Website, unvollständige Komponentenänderungen, fehlende Quellen, Sicherheitsprobleme, nicht nachvollziehbare Veröffentlichungen und gefährdete Originaldateien.

## 7. Eingang und Archivierung

| Bereich | Aktueller Status | Letzte Prüfung / Hinweis |
| --- | --- | --- |
| `input/` — neue Artefakte | `NICHT GEPRÜFT` | Inhalt und Anzahl unbekannt |
| `archiv/inputs/` — unveränderte Originale | `NICHT GEPRÜFT` | Archivabgleich offen |
| `archiv/releases/` — veröffentlichte Pakete | `NICHT GEPRÜFT` | Vollständigkeit und Zuordnung offen |

**Offene Importvorgänge:**

| Import-ID | Quelle / Dateien | Verarbeitung | Originalarchiv / Integritätsprüfung | Nächster Schritt |
| --- | --- | --- | --- | --- |
| *Keine erfasst; Eingang noch nicht inventarisiert* | — | — | — | `input/` prüfen |

- `input/` soll **nach erfolgreich abgeschlossener Verarbeitung leer** sein, nicht während eines noch offenen Imports.
- Alle Originale unverändert unter `archiv/inputs/` archivieren, Integrität prüfen und erst dann aus `input/` entfernen. Nicht verarbeitbare oder ungeklärte Dateien bleiben erhalten und werden hier gemeldet.
- Verweise bei größeren Importen auf den konkreten Eintrag in `.nocms/HISTORY/` oder eine Quellenübersicht in `.nocms/KNOWLEDGE/`, statt Dateilisten mehrfach abzuschreiben.
- Archive liegen außerhalb des öffentlichen `site/`. Sie ersetzen kein unabhängiges Backup.

## 8. Prüfstand und Freigabehindernisse

*Hier stehen die **zuletzt wirklich ausgeführten** Prüfungen für den aktuellen relevanten Websitezustand. Testergebnisse früherer Stände gelten nicht automatisch für neue Änderungen.*

| Prüfung | Status | Geprüfter Stand / Datum | Ergebnis / Nachweis oder Grund |
| --- | --- | --- | --- |
| HTML-Struktur, Links, Ressourcen | `NICHT GEPRÜFT` | — | — |
| CSS, Responsive-Verhalten, visuelle Kontrolle | `NICHT GEPRÜFT` | — | — |
| JavaScript und interaktive Funktionen | `NICHT GEPRÜFT` | — | — |
| Tastatur, Semantik, Zugänglichkeit | `NICHT GEPRÜFT` | — | — |
| Gemeinsame Bausteine, alle Fundstellen und Layoutausnahmen | `NICHT GEPRÜFT` | — | — |
| Inhalte, Quellen, Briefing und Markenregeln | `NICHT GEPRÜFT` | — | — |
| Sicherheitsprüfung und Ausschluss privater Dateien | `NICHT GEPRÜFT` | — | — |
| Archivpaket: Vollständigkeit, Lesbarkeit, Prüfsumme | `NICHT GEPRÜFT` | — | — |
| Deployment / tatsächlicher Live-Stand | `NICHT GEPRÜFT` | — | — |

**Prüfstatus:** `NICHT GEPRÜFT`, `BESTANDEN`, `FEHLGESCHLAGEN`, `EINGESCHRÄNKT / NICHT AUSFÜHRBAR`, jeweils mit nachvollziehbarem Bezug zum geprüften Stand. „Von KI für gut befunden“ ist kein Ersatz für eine nicht ausgeführte technische Prüfung.

**Aktuelle Freigabe für nächsten Schritt:** `NICHT ERMITTELT`  
**Veröffentlichungssperren / zwingend zu klärende Punkte:** `NICHT BEURTEILT`  
**Zuletzt bestätigte Freigabe (Umfang, Stelle, Datum, Nachweis):** `NICHT ERMITTELT`

Bei sicherheitskritischen Fehlern, fehlenden nötigen Freigaben, nicht überprüfbaren Releasepaketen oder unklarer Veröffentlichungslage keine erfolgreiche Veröffentlichung behaupten; nach `RULES.md` und `AGENT.md` handeln.

## 9. Letzte abgeschlossene Vorgänge (Kurzverweise)

*Maximal die letzten drei bis fünf relevanten Vorgänge. Vollständige Chronologie unter `.nocms/HISTORY/`.*

| Datum / Zeitzone | Vorgang | Ergebnis | Detailverweis |
| --- | --- | --- | --- |
| *Noch kein bestätigter Vorgang erfasst* | — | — | — |

Die Historie enthält das **Warum** und die konkrete Nachvollziehbarkeit; hier stehen nur die letzten Ergebnisse, soweit sie für eine Übernahme relevant sind.

## 10. Ablauf zur Aktualisierung von STATE.md

1. **Vor Beginn:** Aktuelle Datei lesen, betroffene Regeln und zuletzt dokumentierten Stand prüfen. Reale Dateien sichten; vorhandene lokale, möglicherweise ungesicherte Änderungen erkennen.
2. **Während der Arbeit:** Auftrag, Betroffenheit, Blockaden und sicher fortsetzbaren nächsten Schritt aktualisieren, wenn sie sich relevant ändern.
3. **Nach Änderungen:** Betroffene Website-Dateien und gemeinsame Komponenten erneut prüfen. `STRUCTUR.md` und `ARCHITECTURE.md` nur dann anpassen, wenn Struktur beziehungsweise technische Entscheidungen verändert wurden.
4. **Nach Import:** Erst erfolgreich und unverändert archivierte Originale aus `input/` entfernen; verbleibende Dateien und Fehler festhalten.
5. **Nach Tests:** Nur tatsächlich durchgeführte Prüfungen als bestanden oder fehlgeschlagen markieren; Teststand, Werkzeug, Zeitpunkt und Grenzen erfassen. Veraltete Resultate bei neuen Änderungen nicht fortschreiben.
6. **Nach Freigabe oder Veröffentlichung:** Freigabeumfang und Nachweis dokumentieren. Für jede nachweislich veröffentlichte Version Release-ZIP und Historieneintrag zuordnen; fehlgeschlagenes oder nicht bestätigtes Deployment klar abgrenzen.
7. **Beim Abschluss:** Abgeschlossene Vorgänge in `HISTORY/` nachhalten, offene Aufgaben bereinigen, nächste sichere Handlung konkret formulieren. Kurze, widerspruchsfreie Übersicht herstellen.

### Minimaler Abschluss-Check

- [ ] Stimmt die Kurzlage mit dem tatsächlichen Projektstand überein?
- [ ] Sind Arbeitsstand, Release und Live-Status eindeutig voneinander getrennt?
- [ ] Sind alle offenen Aufgaben, Fehler, Freigaben und blockierenden Punkte auffindbar?
- [ ] Wurden Prüfungen nur mit wirklichen Ergebnissen und zum richtigen Dateistand erfasst?
- [ ] Ist der Status von `input/` und der Originalarchivierung korrekt?
- [ ] Sind die letzten relevanten Vorgänge in `HISTORY/` auffindbar?
- [ ] Ist der nächste sichere Schritt für eine neue KI ohne frühere Unterhaltung verständlich?
- [ ] Enthält die Datei keine vertraulichen Rohdaten oder Zugangsdaten?

---

**noCMS-Leitsatz:** `AGENT.md` erklärt die Arbeitsweise. `BRIEFING.md` erklärt den Auftrag. `STRUCTUR.md` zeigt den Aufbau. `ARCHITECTURE.md` erklärt die Technik. `RULES.md` setzt Grenzen. `HISTORY/` bewahrt den Verlauf. **`STATE.md` zeigt, wo das Projekt jetzt wirklich steht.**
