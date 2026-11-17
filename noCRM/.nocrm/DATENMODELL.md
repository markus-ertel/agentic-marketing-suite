# Kanonisches offenes Datenmodell – v0.1

**Kontaktindex:** `kontakte/contacts.csv` (UTF-8, RFC-4180-kompatibel; CSV ist keine Zugriffskontrolle). Feldnamen in `.nocrm/vorlagen/contacts-template.csv`: `contact_id`, `display_name`, `organization`, `email`, `phone`, `preferred_channel`, `language`, `relationship_role`, `updated_at`. Nicht enthalten: automatisch inferierte Persönlichkeit, Emotion, Gesundheit, Ideologie.

**Einwilligungen:** `kontakte/consents.csv`: `contact_id`, `channel`, `purpose`, `status`, `recorded_at`, `evidence_ref`, `basis`, `valid_until`, `notes`. Einträge für unterschiedliche Zwecke/Kanäle getrennt; bei Widersprüchen restriktiver Zustand; Nachweise müssen validiert sein. Statuswerte: `granted`, `revoked`, `denied`, `objected`, `unknown`. Besondere Ausnahmebestätigungen dokumentieren, nicht über eine boolesche Flag vortäuschen.

**Ereignisprotokoll:** `kommunikation/events.jsonl` – ein JSON-Objekt pro Zeile mit `event_id`, `contact_id`, `timestamp`, `channel`, `direction`, `kind`, `status`, `provider_ref`, `source_ref`, `purpose`. Inhalte wenn möglich als gesondertes Artefakt unter Zugriffskontrolle, nicht unbeschränkt ins Ereignislog. Keine geheimen Tokens.

**Entwurf:** `kommunikation/drafts/<id>.json` mit `draft_id`, `contact_id`, `channel`, `purpose`, `body`, `subject`, `status`, `review`, `authorization`, `idempotency_key`. Genehmigung gilt nur für konkrete Empfänger, Kanal, Inhalt, Zeitpunkt/Frist und ggf. Kosten. Inhaltsänderung nach Freigabe ⇒ neue Freigabe.

**Wahrheit/Provenienz:** Gesicherte Angaben nur bei belastbarer Quelle/letztem Datum; Aussagen des Menschen, offizielle Dokumente, externe Information und KI-Hypothesen getrennt.

**Export/Löschung:** Kontaktbezogene Einträge mit `contact_id` referenzieren, damit Datenexport, Einschränkung und Löschverfahren möglich sind; Aufbewahrungsfristen, Sicherungen und Rechtsgründe berücksichtigen. Kein blindes Entfernen rechtlich erforderlicher Nachweise.

**Skalierung:** Für Mehrbenutzerbetrieb optional SQLite oder Postgres mit rollenbasierten ACLs und verschlüsseltem Speicher; CSV/JSONL bleiben Interchange-Format. Keine Migration nur wegen zusätzlicher Kontakte erzwingen.

## Einfacher lokaler Init-Modus

`.nocrm/tools/contact_store.py` kann den Kontaktindex und einen leeren Ereignisspeicher bei ausdrücklichem Aufruf erstellen; nur Einzelbenutzer-Demo, keine Datenbank. Schreibvorgänge sind über eine Sperrdatei serialisiert, damit parallele Agenten keine Kontakte überschreiben. Zellen, die mit `=`, `+`, `-`, `@`, Tab oder Wagenrücklauf beginnen, werden mit `'` gespeichert, damit Tabellenprogramme sie nicht als Formel ausführen.
