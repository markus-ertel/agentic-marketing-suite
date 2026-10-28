# Business-DNA Workspace v0.1

Eigenständiger KI-Fachspezialist für Organisationswissen. Konzipiert als optionaler Bestandteil der **Agentic Marketing Suite**, aber ohne deren Installation lauffähig.

## Schnellstart

1. `business-dna/` in das Repository oder einen eigenen Projektordner kopieren.
2. Deinen Agenten anweisen: „Lies `business-dna/AGENT.md`“.
3. Ohne weiteren Auftrag fragt er: **„Wobei kann ich Ihnen beim Unternehmenswissen helfen?“**
4. Mit konkretem Auftrag liefert er eine erste nutzbare Analyse, ohne einen starren Fragenkatalog zu starten.
5. Bestehende Unterlagen nach `business-dna/input/` legen; ein Harness muss Lesen/Schreiben selbst bereitstellen.

## Was liegt wo?

- `business-dna/AGENT.md`: Gesprächsstart, Fachrolle und Arbeitseinstieg.
- `business-dna/.business-dna/`: interne Methoden, Regeln, Schemas und Hilfswerkzeuge.
- `business-dna/input/`, `business-dna/archiv/`: temporäre Übergabe und Original-/Versionsablage.
- Ergebnisordner wie `wissen/`, `angebote/`, `kontext/` entstehen nur bei Bedarf.
- `Business-DNA-Conceptual-Architecture-Organizational-Knowledge-Specification-v0.1.md`: vollständige Architektur- und Fachspezifikation.

## Beispiel: lokale Tools

```bash
python3 business-dna/.business-dna/tools/lint_records.py \
  business-dna/.business-dna/beispiele/topaca/claims.jsonl \
  --sources business-dna/.business-dna/beispiele/topaca/sources.jsonl

python3 business-dna/.business-dna/tools/build_context.py \
  business-dna/.business-dna/beispiele/topaca/claims.jsonl \
  --sources business-dna/.business-dna/beispiele/topaca/sources.jsonl \
  --purpose "Produktkommunikation" --requester advertising \
  --topics product,stage --visibility shared
```

Die Tools lesen Daten lokal, prüfen und erzeugen ein Context-Pack auf stdout; sie kontaktieren keine Netzdienste und haben keine Schreibbefugnis auf fremde Module.

## Sicherheit und Reifegrad

Die mitgelieferten Tools sind Referenzwerkzeuge, keine vollwertige Zugriffskontrolle. Vertrauliche Unternehmensdaten dürfen nicht ohne bewusstes Vorgehen in öffentliche Repositories gelangen. Keine echte automatische Synchronisation, kein eigener Harness, keine automatische Wahrheits- oder Rechtsprüfung. Der Einstieg folgt der Fachrollen-Konvention der übrigen Suite-Module.

## Integration in diesem Repository

Business-DNA ist als elfter optionaler Fachbereich registriert. Die CLI kann zusätzlich eine JSON-Anfrage mit `--request` verarbeiten. [Konkrete Übergaben, Statusmapping und private Ablage](.business-dna/SUITE.md). Die ursprünglichen v0.1-Unterlagen bleiben als Herkunftsdokumentation erhalten.

## Externe Quelle: Kundenfeedback

Die aktuelle Entwicklung ergänzt [Kundenfeedback als externe Evidenz](.business-dna/integrationen/customer-feedback/README.md): redigierter Vorschlag, konkrete menschliche Bestätigung, wiederholsichere lokale Übernahme und gezielte nichtöffentliche Hypothesenanalyse. Der Methodenindex umfasst jetzt 37 Methoden; die ursprünglichen v0.1-Paketunterlagen bleiben als Herkunftsstand erhalten. Es wird keine automatische Verifikation oder Anonymisierung behauptet.
