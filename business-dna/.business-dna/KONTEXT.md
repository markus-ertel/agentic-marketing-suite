# KONTEXT – Zweckgebundene Exporte

Erzeuge auf Anforderung nur benötigte Themen. Zu jedem Item: Claim-ID, Status, Zeit, Quellen und Wert. Berücksichtige Sichtbarkeit, verlangten Verwendungszweck und begrenztes Zeichenbudget.

Regelfall: nur aktive `verified`, `declared`, `planned` und innerhalb der gewünschten Sichtbarkeit. `disputed` nur für explizite Konfliktanalyse; `superseded` und `rejected` nicht als aktuelle Fakten.

**Keine Aufwertung** von `declared` oder `planned` im Export. `public` ist eine Datenkategorie, **keine** Freigabe. Ein Kontextpaket ist ein Snapshot und bleibt nachvollziehbar. Keine automatische Änderung fremder Module.

## Explizite Hypothesenanalyse

`include_hypotheses: true` ist eine optionale boolesche Anfrage-Erweiterung (CLI `--include-hypotheses`). Standard bleibt `false`. Nur für ausdrücklich beauftragte, tatsächlich berechtigte nichtöffentliche Analyse; der öffentliche Export wird abgelehnt. Status `hypothesis`, Quellen, Zeit und Einzelbeobachtungsgrenzen bleiben erhalten. Weder Sichtbarkeitsflag noch ausdrückliche Auswahl authentifizieren den Empfänger.

Nach Nutzung des versionierten Feedback-Stores `--store` statt alter flacher JSONL-Pfade verwenden. Der Export liest einen konsistenten aktuellen Snapshot und referenziert ihn als `source_snapshot`; er schreibt oder entscheidet nichts. Alte flache Dateien werden beim Bootstrap erhalten, nicht fortgeschrieben. [Feedback-Verfahren und Grenzen](integrationen/customer-feedback/README.md).
