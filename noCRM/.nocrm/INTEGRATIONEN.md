# Provider-unabhängige Integration

Die kanonische Handlung ist `draft`, `review`, `authorize`, `send`, `check_status`, `cancel` oder `import_inbound`. Fachmethoden kennen keine Zugangstokens oder Vendor-SDKs. Adapter legen Fähigkeiten per `capabilities` offen: erlaubte Zwecke, Medienformate, freigeschaltete Accounts, Templatepflicht, Limits, mögliche Sende-/Lesefunktionen, Zustellstatus und Kosten.

**Kanonischer Request für weitere Anbieteradapter** (Zuordnung zum ausgelieferten IMAP/SMTP-Plan siehe unten): `action_id`, `draft_id`, `contact_id`, `channel`, `purpose`, `content_hash`, `recipient_handle`, `authorization_ref`, `legal_basis_evidence_ref`, `idempotency_key`, `timeout`, `cost_limit`.

**Response:** `provider`, `account_id`, `provider_message_id`, `accepted_at`, `status`, `error`, `status_checked_at`; `accepted` ≠ `delivered`. Adapter speichern keine Tokens im Projektordner.

Zusätzlich zu den lokalen Prüfern wird ab v0.2.3 ein optionaler [IMAP-/SMTP-Adapter](integrationen/email/README.md) ausgeliefert. `prepare` bleibt lokal; berechtigter Read-only-Import, IMAP-Entwürfe und SMTP werden erst durch explizite, geprüfte Aufträge ausgeführt. Es gibt keine eingerichteten Konten. Weitere, noch nicht implementierte Anbieteradapter: Gmail, Microsoft Graph, WhatsApp Business Platform, Telegram Bot, eigener Website-Chat, Telefondienst. Signal nur nach besonderer Prüfung möglicher Integrationen, keinesfalls als offiziell unterstützte Bot-API ausgeben.

Priorität: Inbox-Import mit Autorisierung → individuelle Antwortentwürfe → menschliche Freigabe → gesicherter Sendeadapter → Status/Recovery → ggf. teilautomatische, eng begrenzte Routineantworten.

Der technische Mail-Adapter ist auch für PR nutzbar und kann private Website-Kontakt-Outboxes mit `import-contact` ohne Versand übernehmen. Modulübergreifende Nutzung erweitert keine Zugriffs-, Einwilligungs- oder Versandrechte. Der adaptereigene Plan friert Konto, Envelope, Zweck, Evidenzreferenz und EML-Hash ein; menschliche Aktionsfreigabe und private Ausführungsereignisse folgen dem Capability-Register.

## Gesprächsfeedback für Business-DNA

[Externe Feedback-Evidenz](../../business-dna/.business-dna/integrationen/customer-feedback/README.md) übernimmt nur bewusst geprüfte, bestätigte Ableitungen als eingeschränkte Hypothesen. Persönliche Gesprächsnotizen und Folgeentwürfe bleiben bei noCRM. Kein vollständiger Verlaufsexport und keine automatische Rohdatenlöschung. Der optionale [Befehl /call-notes](../../.claude/commands/call-notes.md) verbindet die bestehenden Verfahren; die Werkzeuge funktionieren auch ohne Claude Code.
