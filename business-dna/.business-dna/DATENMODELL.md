# DATENMODELL – Kanonische v0.1-Objekte

**Claim:** `claim_id`, `subject`, `predicate`, `value`, `status`, `visibility`, `version`, `updated_at`, `source_refs`, optional `valid_from`, `valid_until`, `review_due_at`, `supersedes`, `scope`.

**Source:** `source_id`, `kind`, `locator`, `captured_at`, optional `sha256`, `description`, `visibility`.

**Decision:** `decision_id`, `decision`, `decider`, `decided_at`, `claim_refs`, optional `reason`.

**Event:** `event_id`, `event_type`, `occurred_at`, `subject_ref`, `actor`, optional `before_ref`, `after_ref`, `reason`.

**Context Request/Pack:** kleine zweckgebundene Schnittstelle, abhängig von `topics`, `visibility_max`, `as_of`, `purpose`, `requester`.

Mögliche States sind in `PROVENIENZ.md` definiert. Beispiele und JSON-Schemas liegen in `schemas/` und `beispiele/`. JSONL = eine JSON-Map je Zeile. IDs müssen stabil sein. **v0.1 speichert je Claim-ID im aktuellen claims.jsonl genau eine Fassung.** Bei Änderungen `version` erhöhen und frühere Fassung im Archiv sichern sowie Event-Referenz anlegen; niemals unprotokolliert alte Fassungen ausradieren. Historische Stände per Archiv rekonstruieren, nicht aus dem aktuellen Snapshot ableiten.

## Bestätigte externe Feedback-Hypothesen

Kundenfeedback verwendet `human_statement` (Äußerung), `internal_record` (eigene Notiz) oder `external_publication` (bereitgestelltes veröffentlichtes Feedback). Abgeleitete Einwände bleiben `hypothesis`, zunächst `restricted`, mit begrenztem Geltungsbereich. Die Bestätigung betrifft die Aufnahme genau dieser Fassung, nicht ihre Verifikation oder Repräsentativität. Wiederholte Evidenz erhöht nicht automatisch den Status.

`feedback-intake` und `feedback-proposal` bündeln vorhandene Records mit Redigierungs-/Nutzungsprüfbezug und Ausgangshashes. Decision hat optionale Hash-/Bestätigungsreferenzen. Der lokale Store hält ganze Generationen; `CURRENT.json` bestimmt den aktuellen Stand, frühere Generationen und Ereignisse bleiben für Versionsbezug erhalten. [Ablage, Wiederholung und Löschgrenzen](integrationen/customer-feedback/README.md).
