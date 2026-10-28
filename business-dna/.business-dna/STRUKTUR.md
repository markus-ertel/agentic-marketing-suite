# STRUKTUR – Verzeichniskonventionen

**Pflicht:** `AGENT.md`, `.business-dna/`, `input/`, `archiv/`. Alle anderen Ergebnisordner nur bei Bedarf.

- Unter `.business-dna/` liegen Methoden, Schemas, Hilfswerkzeuge, State, History, Log.
- Unter `business-dna/unternehmen/`, `wissen/`, `angebote/`, `kontext/` entstehen konkrete Ergebnisse dynamisch.
- Keine künstlich angelegten leeren Themenordner im Runtime-Ergebnisbereich.
- Bei erfolgreicher Übernahme Originale nachvollziehbar archivieren und `input/` leeren; fehlgeschlagene Übernahme darf kein Original vernichten.
- `wissen/` und sensible Ergebnisse gehören standardmäßig nicht in öffentliche Git-Repositories.
- Keine Methode wird von ihrer festen Stelle nach außen kopiert; Fachwissen wird referenziert.
- `STATE.md` = aktueller Zustand, `LOG.md` = tatsächliche Operationen, `HISTORY.md` = wesentliche fachliche Entscheidungen.

## Optionaler versionierter Feedback-Store

Nur nach tatsächlicher bestätigter Übernahme: `wissen/CURRENT.json`, private `wissen/generations/` mit JSONL-Snapshots und `wissen/proposals/` mit redigierten Vorschlagsfassungen. Keine Rohtranskripte in diesem Store. Erhaltene flache Ausgangsdateien sind nach Initialisierung keine fortgeschriebene Wahrheit mehr; Verbraucher nutzen `build_context.py --store`. [Details](integrationen/customer-feedback/README.md).
