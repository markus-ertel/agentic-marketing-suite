# Preis- und Aktionsgestaltung

**Methoden-ID:** `angebot/preis-aktionsgestaltung` · **Typ:** fachliche Arbeitsanleitung · **Version:** 0.1

## Zweck
Preise, Rabatte, Bundles und Aktionen so planen, dass sie Marge, Markenwirkung und Preisangabenrecht (inkl. Streichpreise nach Omnibus-Regeln) gleichzeitig erfüllen.

## Eingaben und Umgang mit Lücken
Ziel/Auftrag, Sortiment, Zielmärkte, Shop-System, vorhandene Daten und Ressourcen soweit für diese Methode nötig heranziehen. Bestehende, berechtigt zugängliche Projektartefakte vor neuen Fragen nutzen. Fehlende Angaben markieren; reversible Hypothesen formulieren. Nur nachfragen, wenn das Ergebnis sonst riskant oder eine verbindliche Entscheidung unmöglich wäre.

## Vorgehen
1. Ziel der Aktion bestimmen (Abverkauf, Neukunden, Warenkorbwert, Saison) und Deckungsbeitrag nach Rabatt, Versand und Zahlungsgebühren berechnen.
2. Mechanik wählen: Prozentrabatt, Betragsrabatt, Bundle, Staffel, Gratisartikel, Gutschein; Wechselwirkungen mit Order Bumps und Upsells prüfen.
3. **Streichpreise:** Bei Preisermäßigungsankündigung ist als früherer Preis der niedrigste Preis der letzten 30 Tage vor der Ermäßigung anzugeben (`.e-commerce/recht/preisangaben-omnibus.md`). Im Katalog `lowest_price_30d` aus der Preishistorie pflegen; das Werkzeug blockiert Abweichungen.
4. Gesamtpreis inkl. USt., Grundpreis, Versandkosten und Aktionszeitraum (`sale_price_effective_date`) festlegen; Aktion im Feed und auf der Seite gleichzeitig starten und beenden.
5. Preisänderungen im Shop oder Feed sind externe Aktionen (Ziel `ecommerce:price_update`) mit `action-approval`.
6. Wirkung danach mit `../analytics/` gegen eine Vergleichsbasis bewerten, nicht nur Umsatz im Aktionszeitraum.

## Ergebnis für den Menschen
**Aktionsplan mit Preislogik, Deckungsbeitragsrechnung und Preisnachweis.** Beginne mit einer klaren Empfehlung bzw. einem verwendbaren Entwurf. Kennzeichne Tatsachen, Hypothesen und ausstehende Freigaben.

## Grenzen
Keine Preisempfehlung ohne Kosten- und Marktdaten; kein Kartell- oder Preisbindungsrat. Ausnahmen der 30-Tage-Regel (z. B. verderbliche Ware, schrittweise Ermäßigung) nur nach Rechtsprüfung nutzen.

## Anwendungsfälle
- **Positiv:** Herbstaktion −20 % auf Jacken: niedrigster 30-Tage-Preis aus der Preishistorie belegt, Aktionszeitraum im Feed, Grundpreis wo nötig, Freigabe vor Preisänderung.
- **Negativ:** „Setz den UVP als Streichpreis, dann wirkt der Rabatt größer“, obwohl der Artikel seit Wochen günstiger verkauft wird: blockiert (Omnibus/Irreführung).

## Qualitätssicherung / Red Flags
- Kein Streichpreis ohne `lowest_price_30d`.
- Keine „nur heute“- oder Knappheitsangaben ohne reale Grundlage.
- Keine erfundenen Preise, Bestände, Kennzahlen, Benchmarks oder Plattformfähigkeiten.
- Externe Änderungen nur gemäß `.e-commerce/AKTIONEN.md`; Rechtsfragen nach `.e-commerce/RECHT.md`.

## Übergaben und Ablage
Ergebnis außerhalb `.e-commerce/` als Markdown-/CSV-/JSON-Artefakt speichern. Weiterführende Methoden selektiv aus `.e-commerce/METHODEN.md` wählen. Bei tatsächlichen Änderungen STATE/LOG/HISTORY sachgerecht aktualisieren.
