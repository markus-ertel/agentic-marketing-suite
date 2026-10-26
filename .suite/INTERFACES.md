# Offene Übergabeverträge v0.2

## Ziel
Jedes Fachmodul bleibt unabhängig. Bei Zusammenarbeit wird **nicht die ganze Projektmappe** an ein anderes Modul übergeben, sondern ein kontrolliertes, beschreibbares Arbeitsobjekt.

### Arbeitsauftrag (`work-order.schema.json`)
ID, Aufgabe, führendes Modul, weitere Fähigkeiten, Ziel/gewünschte Wirkung, benötigte Eingabereferenzen, Zweck/Grenzen, Status und Risiko. Keine zwangsweisen CRM- oder Kundendaten.

### Artefakt (`artifact.schema.json`)
ID, Modul, Dateipfad, Typ, Versionsnummer, ggf. SHA-256, Ausgangsreferenzen, Inhaltsstatus, personenbezogene Daten (ja/nein), Medienrechte (geklärt/offen/nicht relevant). `draft` ≠ `approved` ≠ `published`.

### Prüfbericht (`review.schema.json`)
Artefakt-ID und Version, Prüftyp, Status, konkrete Findings, Evidenz-Referenzen, prüfende Kompetenz, Zeitpunkt. Prüfen ohne „juristisch freigegeben“ zu behaupten.

### Aktionsfreigabe (`action-approval.schema.json`)
Exakter Kanal/Aktion, Autorisierender, Zeit-/Budgetgrenze, Zielartefakt samt Hash, Freigabeergebnis, Ausführungs-ID. Niemals nur „ok“ als implizite Allzweckfreigabe speichern.

## Austauschprinzip
- `path` (Artefaktvertrag) bezieht sich auf den **Suite-Root**; keine absoluten externen Pfade in Artefakten.
- IDs sind stabil, Überschreibungen erzeugen neue Version; ein einziges Modul ist Schreib-Owner des Artefakts.
- Prüfer geben Findings zurück, statt Dateien fremder Module unaufgefordert zu ändern.
- Quellenmaterial und personenbezogene Daten werden über erlaubte Referenzen, ggf. redigierte Ausschnitte übergeben.
- JSON-Schemas dürfen via Python-Standardbibliothek syntaktisch geprüft werden; vollwertige Validierung nutzt einen externen JSON-Schema-Validator oder das enthaltene lokale begrenzte Prüfwerkzeug.

## Prüf- und Freigabekette (ab v0.2)
- `action-approval` mit `decision: approved` verlangt `review_refs` auf Prüfberichte **genau dieser Artefaktversion**: mindestens eine G2-Dimension (`brief`, `expert`, `evidence`, `creative`, `technical`, `accessibility`, `consistency`, `security`) und eine G3-Dimension (`legal` oder `privacy`), jeweils `pass`, `warning` mit `risk_accepted_by` oder begründet `not_applicable`.
- `execution_status` ≠ `not_attempted` nur bei `decision: approved`; `confirmed` nur mit `execution_external_id`.
- `authorizer` und `risk_accepted_by` sind Menschen bzw. verantwortliche Rollen, **nie ein KI-System**.
- Budgets: `budget_limit` + `currency` (ISO 4217); `budget_limit_eur` bleibt als v0.1-Altfeld gültig.
- Querprüfung mehrerer Datensätze: `python3 .suite/tools/validate_records.py bundle <datei.json>` mit den Schlüsseln `work_orders`, `artifacts`, `reviews`, `approvals` (Beispiel: `.suite/beispiele/demo-freigabe-bundle.json`). Geprüft werden u. a. Hash-Gleichheit, Version, blockierende Reviews und `published` nur mit bestätigter Ausführung.

## Status-Mapping Module → Suite
Lokale Status bleiben im Modul maßgeblich. Für suiteweite Übergaben gilt folgende Übersetzung. **Im Zweifel den niedrigeren Suite-Status wählen** (z. B. lieber `review` als `approved`).

| Suite `artifact.status` | advertising (Manifest) | social-media (Publish-Job) | creative (Job) | noCRM (Entwurf/Aktion) | website (Release) | marketing · pr · analytics |
|---|---|---|---|---|---|---|
| `draft` | `draft` | `idea`, `draft` | `draft`, `concept_review`, `production`, `rework` | `proposed`, `drafted` | in Arbeit / `OFFEN` | Entwurf |
| `review` | `ready_for_review` | `in_review` | `technical_qa`, `visual_qa`, `approval_pending` | `reviewed` | geprüft, nicht freigegeben | in Prüfung |
| `approved` | `approved`, `staged`¹ | `approved`, `scheduled`¹, `publishing`¹ | `approved`, `released`² | `approved`, `queued`¹ | `Veröffentlichung vorbereitet` | freigegeben |
| `published` | `active`³ | `published`³ | – (nur über Zielmodul) | `sent`³, `delivered`³ | `Veröffentlicht`³ | veröffentlicht³ |
| `archived` | `completed` | `archived` | – | – | ältere Releases in `archiv/releases/` | archiviert |
| kein Artefaktstatus → Review `blocked` bzw. Freigabe `denied`/`revoked` | `rejected`, `error` | `blocked`, `failed`, `cancelled`, `unknown`⁴ | – | `blocked`, `cancelled`, `failed`, `expired`, `unknown_outcome`⁴ | `Fehlgeschlagen / Blockiert` | – |

¹ Ausführung läuft oder ist eingeplant: Artefakt bleibt `approved`, `execution_status` = `queued`/`submitted`.
² `released` = freigegebene Übergabe an ein anderes Modul oder eine Druckerei, **keine** Veröffentlichung.
³ Nur mit bestätigter externer Rückmeldung (Plattform-ID, Provider-Referenz, verifiziertes Deployment) → `execution_status: confirmed`.
⁴ Unklarer Ausgang → `execution_status: uncertain`; Status abfragen, nicht wiederholen.

## Freigabe-Mapping Module → `action-approval`
Modul-Freigabefelder sind **lokale Vorstufen**. Für Außenwirkung im Suite-Kontext wird zusätzlich ein `action-approval`-Datensatz mit Prüfberichten erstellt; bei Abweichung gilt die strengere Seite (z. B. advertising verlangt `legal_reviewed` **und** die Suite einen `legal`-Review).

| `action-approval` | advertising | social-media | creative | noCRM | website |
|---|---|---|---|---|---|
| `action` | `approved_action`: `activate`/`update` mit Budgetwirkung → `spend`, sonst → `modify_external`; `stage_paused`, `pause` → `modify_external` | `publish` | `print` bzw. `publish` laut `approval.scope` | `send` | `publish` |
| `decision: approved` | `approval.ref` + `approved_by` gesetzt, `approved_action` ≠ `none` | `content_approved` **und** `execution_authorized` | `approved_by` + `approved_at` gesetzt | `review.approved` **und** `authorization.allowed` | Freigabeeintrag in `.nocms/HISTORY/` bzw. `BRIEFING.md` |
| `authorizer` | `approval.approved_by` | `approval.approved_by` | `approval.approved_by` | Autorisierende laut `.nocrm/AKTIONEN.md` | Freigabestelle laut `.nocms/STATE.md` |
| `decided_at` | nicht vorhanden → im Suite-Datensatz ergänzen | `approval.approved_at` | `approval.approved_at` | nicht vorhanden → ergänzen | Datum des Freigabeeintrags |
| `artifact_sha256` | SHA-256 der Manifestdatei | `approval.revision_sha256` | `manifest_sha256` aus `creative_preflight.py` | SHA-256 der Entwurfsdatei | SHA-256 des Release-ZIP |
| `budget_limit` + `currency` | `approval.approved_budget` + `currency` | – | Druck-/Produktionskosten, falls kostenpflichtig | Versandkosten, falls kostenpflichtig | – |
| `review_refs` | `claims_reviewed`/`legal_reviewed` sind Booleans → als Review-Datensätze belegen | Prüfungen laut `PUBLISHING.md` | Preflight-/QA-Berichte | `review`-Objekt des Entwurfs | Prüfergebnisse laut `RULES.md` |
| `execution_external_id` | `external_ids` | `external_post_id` | Druckerei-Auftragsnummer | `provider_ref` (`idempotency_key` ist **keine** Bestätigung) | Deployment-ID/URL |

### Grenzen der strukturellen Prüfung

Der Bundle-Preflight vergleicht die angegebenen Versionen und Hashwerte zwischen Datensätzen. Er berechnet nicht selbst den Hash der referenzierten Datei, authentifiziert keine Person und bestätigt keine tatsächliche externe Ausführung. Die Erkennung von KI-Bezeichnungen im Freigabenamen ist eine Plausibilitätsprüfung, kein Identitätsnachweis. Der ausführende Harness muss Dateiinhalt, Identität, Berechtigungen und Gültigkeit der Freigabe vor einer Aktion unabhängig prüfen. Ein Review mit schwerwiegenden oder kritischen Befunden darf nicht als `not_applicable` eine Freigabe ermöglichen.
