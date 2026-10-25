# noCMS — HISTORY/

**Chronik nachvollziehbarer Änderungen, Entscheidungen, Importe, Freigaben, Releases und Wiederherstellungen dieses Website-Projekts.**  
**Spezifikationsstand:** Suite v0.2 · **Vorlagenstatus:** `NICHT INITIALISIERT — keine Einträge`

> Entspricht der `HISTORY.md` der übrigen Suite-Module. Weil Releases, Importe und Rollbacks eigene Belege brauchen, führt noCMS je Vorgang eine eigene Datei statt einer einzigen Liste.

## Ablage
- Ein Vorgang = eine Datei: `YYYY-MM-DD_<art>_<kurztitel>.md`, z. B. `2026-11-03_release_v1.0.0.md`, `2026-11-01_import_logo-paket.md`, `2026-10-30_entscheidung_sitemap.md`.
- `<art>` ∈ `entscheidung` · `import` · `aenderung` · `freigabe` · `release` · `rollback`.
- Einträge **nie überschreiben**. Korrekturen als neuer Eintrag mit Verweis auf den alten.
- Diese Datei enthält nur das Register unten, keine Inhalte der Vorgänge.

## Pflichtangaben je Eintrag
- Datum/Uhrzeit mit Zeitzone, Art, kurzer Anlass und **Begründung** (warum, nicht nur was).
- Betroffene Dateien bzw. Bereiche (relative Pfade ab Projektwurzel, z. B. `site/kontakt.html`).
- Durchgeführte Prüfungen mit Ergebnis; nicht Geprüftes ausdrücklich als `NICHT GEPRÜFT`.
- Freigabe: wer, was genau, Umfang/Frist. Ohne Freigabe: `KEINE FREIGABE`.
- **Bei Releases zusätzlich:** Versionskennung, Pfad des ZIP unter `archiv/releases/`, **SHA-256 des ZIP**, Zielumgebung, Veröffentlichungsstatus (`Veröffentlichung vorbereitet` · `Veröffentlicht` · `Fehlgeschlagen / Blockiert`) und Nachweis (Deployment-ID/URL, Prüfzeitpunkt).
- **Im Suite-Kontext:** Verweise auf zugehörige Suite-Datensätze (`artifact`-, `review`-, `action-approval`-IDs), siehe `../.suite/INTERFACES.md` (ab Modulordner).

## Register

| Datum | Art | Eintrag | Status |
| --- | --- | --- | --- |
| — | — | Noch keine Einträge | — |
