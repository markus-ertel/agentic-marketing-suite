# Human Approval & Audit Trail Capability v0.1

Eine gemeinsame, optionale Fähigkeit für konkrete Freigabeanforderungen, menschliche Entscheidungen und dauerhaft gespeicherte Ereignisse. Die Fachmodule bleiben eigenständig. Es gibt keinen Freigabeserver, keine neue Benutzerverwaltung und keine automatische Aktion. Die bestehenden Verträge für Artefakte, Reviews und Aktionsfreigaben bleiben gültig.

## Ablauf und Verantwortungen

1. **Fachspezialist:** Auftrag, prüfbaren Entwurf, Datei-/Artefaktversion, exakten SHA-256, konkrete Aktion und Ziel zusammenstellen. Eine kurze Zusammenfassung benennt die Entscheidung und Folgen, nicht nur „bitte prüfen“. Vorhandene Qualitäts-/Rechtsprüfungen als datierte Review-Snapshots referenzieren; Risiken und offene Fragen kenntlich machen. Bei Kosten Betrag und Währung, bei zeitlicher Begrenzung Ablaufzeit angeben. Nur die tatsächlich benötigte Aktion anfordern.
2. **Anforderung erfassen:** `approval-request` mit Titel, Zusammenfassung, anforderndem Modul/Agenten, Zeitpunkt, Artefakt-Snapshot, Review-Snapshots, Aktion/Ziel und optional Budget/Ablaufzeit erstellen. Das lokale Werkzeug prüft den Datei-Hash und schreibt ein eigenes `requested`-Ereignis. Ein solcher Eintrag ist ausstehend und keine menschliche Entscheidung.
3. **Vertrauenswürdiger Harness:** Der berechtigten Person genau diese Anforderung einschließlich Dateiinhalt, Version, Ziel, Budget und Prüfgrenzen vorlegen. Explizite Entscheidung über einen authentifizierten bzw. anderweitig vertrauenswürdigen Kanal erfassen: **freigeben**, **ablehnen** oder **Änderung verlangen**. Personenkennung/Name, optional Rolle, Zeitpunkt mit Zeitzone, Begründung und Referenz auf die echte Bestätigung übergeben. Eine KI darf Entscheidungen nicht selbst treffen, aus einer allgemeinen Aufgabenbeschreibung ableiten oder eine Person/Bestätigung erfinden.
4. **Entscheidung protokollieren:** Ein neues `approval-event` anhängen. Es enthält Person, Entscheidungs- und Aufzeichnungszeit, Request-ID, Vorgänger-Ereignis, exakte Artefaktversion/Hash, Aktion/Ziel und ggf. Budget. Bestehende Zeilen bleiben erhalten. Bei Freigabe werden Datei-Hash sowie die vorhandenen G2-/G3-Bundle-Gates erneut geprüft. Eine Ablehnung oder Änderungsanforderung bleibt auch möglich, wenn eine Datei inzwischen fehlt oder verändert wurde.
5. **Widerruf:** Eine spätere, nachgewiesene menschliche Rücknahme erzeugt `revoked` als neues Ereignis. Der jüngste Zustand dieses Requests ist maßgeblich; frühere `approved`-Zeilen dürfen nicht isoliert als aktuelle Erlaubnis ausgewertet werden. Ein Widerruf führt keine Rückbuchung, Löschung oder Rücknahme bereits ausgeführter Aktionen aus. Der Harness muss bereits laufende oder eingeplante Vorgänge entsprechend seinen Möglichkeiten stoppen bzw. eskalieren.
6. **Ausführung:** Unmittelbar vor einer Aktion prüft der ausführende Harness bzw. Adapter unabhängig die echte Identität und Befugnis, die neueste vollständige Ereigniskette, Widerruf/Ablauf, aktuelle Datei/Hash/Version, Prüfungen, Konto/Ziel, Budget und gegebenenfalls schon verbrauchte Beträge oder frühere Ausführung. Er verhindert doppelte Ausführung und protokolliert echte Providerantworten separat. Eine Freigabe von 500 EUR ist kein wiederverwendbarer Betrag je Werkzeugaufruf. Das Dashboard ist weder Freigabestelle noch Ausführungsgate.

## Zustände und neue Anforderungen

| Ereignis / abgeleiteter Status | Bedeutung | Nächster Schritt |
|---|---|---|
| `requested` → `pending` | konkrete Anfrage ausstehend | Mensch entscheidet |
| `approved` | menschliche Freigabe protokolliert, noch keine Ausführung | Harness prüft vor jeder tatsächlichen Aktion |
| `denied` | abgelehnt | keine Ausführung; ggf. neue Anforderung |
| `changes_requested` | Änderung verlangt | Datei überarbeiten, neue Version/Hash und neue Request-ID |
| `revoked` | zuvor erteilte Freigabe widerrufen | keine weitere Ausführung auf dieser Grundlage |
| `expired` (nur abgeleitet) | begrenzte Anforderung/Freigabe abgelaufen | neue Anforderung; Historie bleibt erhalten |

Eine ausstehende Anforderung kann einmal freigegeben, abgelehnt oder zur Änderung zurückgegeben werden. Eine Freigabe kann widerrufen werden, auch nach ihrem Ablauf. Abgelehnte, zur Änderung zurückgegebene oder widerrufene Anforderungen werden nicht überschrieben und nicht erneut freigegeben; dafür eine neue Request-ID verwenden. Änderung an Datei, Version, Aktion, Ziel, Prüfungen oder Budget benötigt eine neue Anforderung. Auch eine neue Anforderung hebt eine andere bestehende Freigabe nicht stillschweigend auf: dazu den betreffenden Request ausdrücklich widerrufen. Ein Agent darf keine neue Anfrage verwenden, um eine menschliche Ablehnung zu umgehen.

## Offene Dateien und Werkzeuge

- [approval-request.schema.json](contracts/approval-request.schema.json) ergänzt die bestehenden [Artefakt-](contracts/artifact.schema.json) und [Review-Verträge](contracts/review.schema.json) durch einen unveränderlichen Anforderungssnapshot.
- [approval-event.schema.json](contracts/approval-event.schema.json) beschreibt einzelne Ereignisse. `requested` enthält die Anforderung; Folgeereignisse referenzieren den unmittelbar vorherigen Eintrag dieses Requests und wiederholen dessen Bindung an Version, Aktion, Ziel und Budget.
- [approval_audit.py](tools/approval_audit.py) erfasst lokal, hängt ausschließlich an, validiert vollständige Protokolle und liefert eine lesbare Statusprojektion. Python 3.9+, nur Standardbibliothek, keine Netzwerkverbindung.
- [validate_records.py](tools/validate_records.py) kennt die zusätzlichen Einzelverträge. Eine Einzelprüfung ersetzt weder die vollständige Protokollprüfung noch die tatsächliche Ausführungsprüfung.

Ablage beispielsweise im **privaten Arbeitsverzeichnis außerhalb der Anweisungsbibliothek**, `…/vorhaben/<vorgang>/approvals.jsonl`. Innerhalb einer Suite kann das auch ein Arbeitsergebnisordner des führenden Moduls sein. Der Operator legt das vorhandene, geschützte Zielverzeichnis fest; es wird nicht automatisch ein zentrales Archiv erzeugt. `approvals.jsonl` und seine Schreibsperre werden von Git ausgeschlossen. Keine Kundenprotokolle in `.suite/` oder öffentlichen Repositorys speichern.

Das Werkzeug erzeugt eine exklusive Sidecar-Sperre, validiert vor jedem Anhängen das vorhandene Protokoll, schreibt mit Append-Modus und synchronisiert den Eintrag auf Datenträger (`fsync`). Neue Protokolle und Sperren erhalten restriktive Dateirechte, soweit das Betriebssystem diese unterstützt. Bei konkurrierendem Schreiben, inkonsistenter Kette oder unvollständiger letzter Zeile wird abgebrochen; alte Zeilen werden nicht still repariert. Nach einem Absturz kann eine Sperre zurückbleiben. Nur nach nachgewiesenem Prozessende und gesicherter unveränderter Historie administrativ untersuchen; keine automatische Übernahme einer vermeintlich alten Sperre.

**Vertrauensgrenze:** Das ist ein append-only arbeitendes Hilfswerkzeug, kein manipulationssicherer Speicher und kein Identitätsnachweis. Wer Schreibrechte auf die Dateien hat, könnte sie außerhalb des Werkzeugs ändern, vollständig zurücksetzen oder entfernen. Der Harness verantwortet vertrauenswürdige Erfassung, Zugriffsrechte, geschützte Backups und gegebenenfalls extern gesicherte Prüfpunkte. Eine plausibel aussehende Zeichenfolge in `actor` oder `evidence_ref` authentifiziert niemanden. Keine Geheimnisse, vollständigen Kundennachrichten oder unnötigen personenbezogenen Daten ins Protokoll kopieren. Aufbewahrung, Löschrechte und Sperrkonzepte organisatorisch festlegen; „nicht überschreiben“ ist kein unbegrenztes personenbezogenes Archiv.

**Ohne getrennten Harness keine Kontrolle:** Läuft der Agent unter demselben Betriebssystembenutzer wie Protokoll, Adapter und Zugangsdaten, kann er technisch eine Entscheidung eintragen und ausführen. Die Freigabe ist dann eine Dokumentationshilfe, keine Sicherung gegen den Agenten. Mindestens: Agenten `approval_audit.py decide` und `--harness-authorized` per Harness-Regel verbieten (für Claude Code in `.claude/settings.json` mitgeliefert) und Adapter-Zugangsdaten nicht in die Agentenumgebung geben (das Dashboard filtert sie). Wirksam wird die Trennung erst, wenn Entscheidungen über einen separaten Benutzer oder Dienst erfasst werden, auf den der Agent keinen Schreibzugriff hat, und nur ein getrennter Ausführer die Zugangsdaten hält.

## Verwendung

Fiktive, strukturell prüfbare Beispiele liegen unter [approval-demo/](beispiele/approval-demo/). Sie zeigen keine reale Freigabe. Für eigene Arbeit erstellt der Spezialist eine neue Anforderung anhand dieser Struktur und der tatsächlichen Dateien/Prüfberichte. Das Artefakt wird für den zu prüfenden Entwurf typischerweise als `review` erfasst. Alte Aktionsfreigaben werden nicht automatisch als menschliche Ereignisse importiert.

```sh
# Anforderung und tatsächliche Datei prüfen, requested-Ereignis anhängen.
python3 .suite/tools/approval_audit.py request \
  --request /privater/pfad/request.json \
  --root /pfad/zur/suite --log /privater/pfad/approvals.jsonl

# Echter, vom vertrauenswürdigen Harness erfasster menschlicher Entscheidungsdatensatz.
python3 .suite/tools/approval_audit.py decide \
  --decision /privater/pfad/decision.json \
  --root /pfad/zur/suite --log /privater/pfad/approvals.jsonl

# Read-only: vollständige Struktur/Kette prüfen bzw. Status ableiten.
python3 .suite/tools/approval_audit.py check --log /privater/pfad/approvals.jsonl
python3 .suite/tools/approval_audit.py status --log /privater/pfad/approvals.jsonl
```

Der Entscheidungsdatensatz hat folgende Form; die Werte stammen aus der tatsächlichen menschlichen Bestätigung und dem präsentierten Request. `previous_event_id` ist die bei der Vorlage angezeigte aktuelle `event_id`; veraltete Bestätigungen werden abgewiesen.

```json
{
  "request_id": "req-eigener-vorgang-v2",
  "decision": "approved",
  "actor": "Name der tatsächlich entscheidenden Person",
  "actor_role": "Geschäftsführung",
  "occurred_at": "2026-10-27T09:15:00+01:00",
  "evidence_ref": "trusted-harness:referenz-auf-echte-bestaetigung",
  "reason": "Begründung der menschlichen Entscheidung",
  "previous_event_id": "evt-aktuell-praesentierte-ereignis-id"
}
```

`decision` kann `approved`, `denied`, `changes_requested` oder später `revoked` sein. Budget, Ziel und Version sind nicht im Entscheidungsinput änderbar. Die Statusprojektion liefert nur für aktuell freigegebene, nicht abgelaufene Requests einen `action_approval_candidate` gemäß bestehendem `action-approval`-Vertrag, immer mit `execution_status: not_attempted`. Das ist ein **Prüfkandidat für den Harness**, keine Ausführungserlaubnis. Widerruf oder Ablauf entfernt ihn aus der Projektion, ohne einen früheren Eintrag zu verändern.

## Dashboard-Anzeige

Das Dashboard zeigt die read-only Projektion unter **Freigaben** an. Die gewünschten Quellen werden ausdrücklich in `approvals.logs` der Dashboard-Konfiguration hinterlegt; standardmäßig sind keine Protokolle verbunden. [Einrichtung und Grenzen](dashboard/README.md) beschreiben lokale Pfade, automatische Aktualisierung und Fehlerzustände. `GET /api/approvals` liefert ausschließlich Anzeigedaten, keine vollständigen Aktionsfreigabekandidaten. Es gibt keine Freigabe-/Widerrufsschaltflächen und keine Schreib- oder Ausführungsrechte.

| Freigaben – fiktive Beispielansicht | Kontext | Status |
|---|---|---|
| LinkedIn-Beitrag | Social Media · Version 3 | Ausstehend |
| Website-Startseite | Website · Version 2 · 27.10.2026, 09:15 Uhr (Europe/Vienna) · Erika Beispiel, Geschäftsführung | Freigegeben |
| Google-Ads-Kampagne | Advertising · Budget 500 EUR | Abgelehnt |

[approvals-demo.jsonl](beispiele/approval-demo/approvals-demo.jsonl) enthält diese fiktiven Zustände. [approvals-revoked-demo.jsonl](beispiele/approval-demo/approvals-revoked-demo.jsonl) hat exakt denselben Anfang und einen zusätzlichen Widerruf der Website-Freigabe; die Ansicht zeigt dann „Widerrufen“. Entscheider und Uhrzeit einer ausstehenden Anforderung nicht als bereits getroffene menschliche Entscheidung darstellen. Zeitstempel mit Zeitzone speichern, in der Anzeige lokal umrechnen. Jeder Leser muss die gesamte Kette prüfen und darf nicht nur nach einer `approved`-Zeile suchen.

## Offene Freigaben im Terminal

`python3 .suite/tools/pending.py` liest die explizit konfigurierten `approvals.logs` aus der Dashboard-Konfiguration. Alternativ `--config /privat/dashboard.json` oder mehrfach `--log /privat/approvals.jsonl` verwenden. Konfigurationspfade werden wie im Dashboard relativ zur Konfigurationsdatei aufgelöst.

Die Übersicht enthält `pending`, `changes_requested` und `expired`. `--json` liefert `open` und `errors`; `--strict` liefert Exit 1 bei offenen Vorgängen, sonst Exit 0. Fehlende/defekte/zu große Protokolle, aktive Schreibsperren, Symlinks oder ungültige Konfiguration ergeben Exit 2 und niemals Entwarnung; gültige andere Protokolle bleiben sichtbar. Die Ausgabe ist nur ein Status-Snapshot, keine Freigabe oder Aktionsprüfung. Das Werkzeug schreibt und entscheidet nichts.
