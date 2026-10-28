# Business-DNA in der Agentic Marketing Suite

Business-DNA ist der elfte optionale Fachbereich. [AGENT.md](../AGENT.md) bleibt sein direkter Einstieg; [RULES.md](RULES.md) bindet bei vorhandener Suite deren Mindeststandards ein. Die [ursprüngliche Spezifikation](../Business-DNA-Conceptual-Architecture-Organizational-Knowledge-Specification-v0.1.md) dokumentiert den Paketentwurf. Diese Notiz beschreibt die konkrete Integration einschließlich Branding und E-Commerce.

## Zuständigkeit

Business-DNA pflegt Organisationswissen mit Claim-ID, Erkenntnisstatus, Version, Quellen und Geltung. Es ist keine zentrale Pflichtdatenbank. Branding verantwortet gewünschte Markenentscheidungen, Marketing die Marktbearbeitung, Creative die Gestaltung, E-Commerce Katalog/Preise/Feeds und Analytics die empirische Wirkung. Eine Markenaussage wird nicht zur Unternehmenswahrheit; eine geplante Funktion nicht zum gegenwärtigen Leistungsbeleg. Preis-/Produktänderungen bleiben beim fachlichen Owner und werden nur referenziert.

Jeder Konsument funktioniert ohne Business-DNA mit eigenen berechtigten Quellen und offengelegten Unsicherheiten. Änderungen an widersprüchlichen Fakten als referenzierten Vorschlag zurückgeben. Kein automatisches Überschreiben, kein vollständiger noCRM-/Mail-Import und keine automatische Synchronisierung abhängiger Artefakte.

## Konkrete Anfrage und Export

Ein `context-request` gemäß [Schema](schemas/context-request.schema.json) enthält `request_id`, `requester`, `purpose`, `topics`, `max_characters`, `visibility_max` und `as_of`. Der Offline-Exporter unterstützt diese JSON-Datei mit `--request` und erhält die Request-ID im Pack. Die bisherigen einzelnen CLI-Parameter bleiben nutzbar; beide Varianten dürfen nicht gemischt werden. Fehlerhafte Anfragen erzeugen keinen Pack auf stdout.

Beispiele vom Suite-Root, ausschließlich mit mitgelieferten Beispieldaten:

```sh
python3 business-dna/.business-dna/tools/test_contracts.py
python3 business-dna/.business-dna/tools/lint_records.py business-dna/.business-dna/beispiele/topaca/claims.jsonl --sources business-dna/.business-dna/beispiele/topaca/sources.jsonl
python3 business-dna/.business-dna/tools/build_context.py business-dna/.business-dna/beispiele/topaca/claims.jsonl --sources business-dna/.business-dna/beispiele/topaca/sources.jsonl --request business-dna/.business-dna/beispiele/request-branding.json
```

Einzelparameter bleiben zum Beispiel möglich: `--requester marketing --purpose "Angebot prüfen" --topics product,stage --visibility shared --as-of 2026-10-27 --max-characters 6000`. Ausgabe erfolgt nur lokal auf stdout; sie wird nicht automatisch gespeichert, versendet oder veröffentlicht. Eine Dateiumleitung nur in einen bewusst gewählten privaten Arbeitsbereich vornehmen.

Der Export behält `verified`, `declared` und `planned` unverändert. Er filtert nach Themen, Claim- **und Quellensichtbarkeit**, Aktualisierungs-/Geltungsdatum und Zeichenbudget. `hypothesis`, `disputed`, `superseded`, `rejected`, `unknown` gehören nicht in diesen Standardexport; eine Konfliktanalyse anhand berechtigter Originale ist eine eigene Fachaufgabe. `excluded_count` zählt beim vorhandenen v0.1-Exporter die wegen des Zeichenbudgets ausgelassenen zulässigen Claims, nicht sämtliche Status-/Sichtbarkeitsausschlüsse. Das Budget wird an der JSON-Serialisierung ohne Einrückung geprüft.

`as_of` selektiert den jeweils geladenen Snapshot, rekonstruiert aber keinen historischen Vollbestand. Für eine historische Sicht passende archivierte Claims **und Quellen** laden. Vor Weiterverwendung Quellenaussage, Geltung und `review_due_at` prüfen; die CLI führt keine echte Quellenprüfung durch und unterdrückt nicht automatisch alle fachlich überfälligen Aussagen. Lints sind begrenzte Formprüfungen und kein vollständiger JSON-Schema-Validator oder Wahrheitsnachweis.

## Kontext an Marketing und Branding

Marketing erhält nur passende Ziele, Angebote, Produktstände oder Belege und bewertet ihre Verwendbarkeit im konkreten Auftrag. Branding referenziert passende Claims für die tatsächliche Ausgangslage und trennt sie von der gewünschten Marke. Beide erhalten Claim-ID, Version, Status, Zeit und `source_refs`; weder `declared` noch `planned` wird durch Übernahme zu `verified`.

Business-DNA-`context-request.visibility_max` und Branding-`brand-context-request.audience` sind verschiedene lokale Felder. Business-DNA-Packs enthalten Claims/Quellen, Brand Context Packs freigegebene Markenentscheidungen. Keine automatische Schema-Konvertierung oder gegenseitige Freigabe. Relevante Faktenreferenzen können als Quellen einer späteren Markenentscheidung dienen, ersetzen aber deren menschliche Bestätigung nicht.

## Suite-Verträge und Freigaben

Die lokalen Schemas einschließlich der beiden additiven Feedback-Hüllen bleiben unter [schemas/](schemas/). Für automatisierte Mehrmodulaufträge gelten zusätzlich [Suite-Verträge](../../.suite/INTERFACES.md): `work-order.lead_module: business-dna`, passende `supporting_modules` und `artifact.owner_module: business-dna`. Dokumente/Context Packs erhalten eine eindeutige Artefakt-ID, Suite-root-relativen Pfad, Version und gegebenenfalls echten SHA-256.

**Keine direkte Statusgleichsetzung:** `verified` beschreibt einen Claim, nicht einen freigegebenen oder veröffentlichten Suite-Artefaktstand. Ein erzeugter Pack ist zunächst `draft`, fachlich geprüft gegebenenfalls `review`. Suite-`approved` braucht die reale menschliche Freigabe der konkreten Datei, Hash und geklärte Rechte; `published` zusätzlich eine bestätigte externe Ausführung. Historische/abgelöste Dokumente werden `archived`, ohne ihre lokale Herkunft oder den Erkenntnisstatus zu löschen.

Ein Quellenprüfbericht kann als Suite-`review` der Dimension `evidence` mit konkreter Artefakt-ID/-Version, Findings und Evidenzreferenzen übergeben werden. Ein erfolgreicher Lint ist lediglich ein formaler Prüfschritt, kein pauschaler `evidence: pass`. Lokale `decision`-/`event`-Datensätze bleiben fachliche Belege, keine automatisch authentifizierten Suite-`approval-event`-Einträge. Falls die [Freigabe-/Audit-Fähigkeit](../../.suite/APPROVALS.md) verwendet wird, nur nachgewiesene menschliche Entscheidungen erfassen und referenzieren. Factsheets/Exporte mit Außenwirkung benötigen separate Freigabe und tatsächliche Ausführungsprüfung beim Harness bzw. zuständigen Kanal. Das Dashboard zeigt Dateien und führt keine Wissens- oder Freigabeentscheidung aus.

## Vertrauliche Arbeitsbestände

Methoden und fiktive Beispiele unter `.business-dna/` bleiben versionierbar. Operative `wissen/`, `unternehmen/`, `angebote/`, `kontext/`, `input/` und `archiv/` sind standardmäßig aus Git ausgeschlossen; Ergebnisse nur nach Auftrag anlegen. Kein öffentlicher Export des gesamten Fachbereichs. Ein explizit freigegebenes öffentliches Factsheet außerhalb der privaten Bestände gesondert erzeugen.

`visibility` und `.gitignore` sind keine Zugriffskontrollen. Der Harness prüft Empfängerrechte, Zweck, Personenbezug, Quellenfundstellen und erlaubte Sichtbarkeit. Referenzen dürfen keine vertraulichen Pfade/Inhalte unbeabsichtigt weitergeben. Löschung, Berichtigung und tatsächliche Zugriffe bleiben organisatorisch und technisch zu regeln. Die Dashboard-Dateipolitik bleibt unverändert; interne Ordner benötigen weiterhin die bestehende Konfigurationsfreigabe.

## Prüfung

Die Repository-Prüfung führt die Modul-Vertragstests und Integrationstests für tatsächliche CLI-Requests aller Nachbarn, selektive Exporte, Status-/Quellenbezug, Budget, fehlerhafte Anfragen und Git-Ausschlüsse aus. Gesprächsqualität, fachliche Wahrheit und die echten Harness-Fälle aus [TESTFAELLE.md](TESTFAELLE.md) sind zusätzlich bei konkreter Arbeit zu prüfen. Es werden keine realen Firmenangaben verifiziert, Freigaben erzeugt oder Außenaktionen ausgeführt.

## Externe Feedbackquelle

[Kundenfeedback-Integration](integrationen/customer-feedback/README.md) ergänzt zwei Hüllenverträge (`feedback-intake`, `feedback-proposal`); Source-/Claim-/Event-Records behalten ihre bisherigen Verträge. Decision erweitert sich additiv um optionale `proposal_sha256` und `confirmation_ref`, für diesen Import zwingend. Die lokale Übernahme bestätigt weder faktische Wahrheit noch Versand-/Veröffentlichungsrechte.

Context Requests erlauben optional `include_hypotheses: true` nur für berechtigte nichtöffentliche Analyse. Der Standardexport bleibt unverändert. Versionierte private Stores werden mit `--store` gelesen, sonst könnten erhaltene alte flache JSONL-Dateien einen überholten Stand liefern. Kontextpacks können den verwendeten Stand additiv als `source_snapshot` referenzieren.
