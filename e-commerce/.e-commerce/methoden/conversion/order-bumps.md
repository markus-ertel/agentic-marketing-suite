# Order Bumps

**Methoden-ID:** `conversion/order-bumps` · **Typ:** fachliche Arbeitsanleitung · **Version:** 0.1

## Zweck
Ein passendes Zusatzangebot im Checkout (vor der Bestellung) so gestalten, dass es Kundinnen und Kunden nützt, den Warenkorbwert erhöht und rechtlich einwandfrei ist.

## Eingaben und Umgang mit Lücken
Ziel/Auftrag, Sortiment, Zielmärkte, Shop-System, vorhandene Daten und Ressourcen soweit für diese Methode nötig heranziehen. Bestehende, berechtigt zugängliche Projektartefakte vor neuen Fragen nutzen. Fehlende Angaben markieren; reversible Hypothesen formulieren. Nur nachfragen, wenn das Ergebnis sonst riskant oder eine verbindliche Entscheidung unmöglich wäre.

## Vorgehen
1. Passung prüfen: ergänzt das Angebot den Hauptartikel sachlich (Zubehör, Verlängerung, Versicherung mit eigener Prüfung)? Marge nach Zusatzkosten berechnen.
2. Gestaltung: Zusatzangebot **nicht vorausgewählt**; Aktivierung nur durch aktive Handlung (Häkchen setzen, Button); Preis inkl. USt. und ggf. Grundpreis direkt sichtbar; Ablehnung ohne Nachteil und ohne Confirmshaming.
3. Gesamtpreis unmittelbar aktualisieren; der Zusatzartikel erscheint vor dem Bestellbutton in der Bestellübersicht.
4. Bei Versicherungen, Garantien oder Abos zusätzliche Fachprüfung (Versicherungsvertrieb, Abo-Pflichten).
5. In der Funnel-Definition als Schritt `order_bump` mit `preselected: false` und `requires_explicit_consent: true` dokumentieren und mit `.e-commerce/tools/validate_compliance.py` prüfen.
6. Test nach `messung/funnel-ab-tests`; Erfolgskennzahl nicht nur Annahmequote, sondern Deckungsbeitrag und Retourenquote.

## Ergebnis für den Menschen
**Order-Bump-Spezifikation** (Angebot, Text, Preislogik, Platzierung, Test). Beginne mit einer klaren Empfehlung bzw. einem verwendbaren Entwurf. Kennzeichne Tatsachen, Hypothesen und ausstehende Freigaben.

## Grenzen
Keine vorausgewählten Kästchen, keine automatisch hinzugefügten Artikel, keine irreführenden „nur heute“-Angaben ohne Grundlage. Die Methode legt keine Preise fest.

## Anwendungsfälle
- **Positiv:** Kamera-Shop: Speicherkarte passend zum Modell als nicht vorausgewähltes Zusatzangebot mit sichtbarem Preis; Messung der Annahmequote und Retouren.
- **Negativ:** „Setze die Garantieverlängerung standardmäßig auf ausgewählt“: blockiert (Art. 22 Verbraucherrechte-RL / § 6c KSchG / § 312a Abs. 3 BGB).

## Qualitätssicherung / Red Flags
- `preselected` muss `false` sein; jede Abweichung ist `blocked`.
- Kein Zusatzangebot, das den Hauptkauf verzögert oder verwirrt.
- Keine erfundenen Preise, Bestände, Kennzahlen, Benchmarks oder Plattformfähigkeiten.
- Externe Änderungen nur gemäß `.e-commerce/AKTIONEN.md`; Rechtsfragen nach `.e-commerce/RECHT.md`.

## Übergaben und Ablage
Ergebnis außerhalb `.e-commerce/` als Markdown-/CSV-/JSON-Artefakt speichern. Weiterführende Methoden selektiv aus `.e-commerce/METHODEN.md` wählen. Bei tatsächlichen Änderungen STATE/LOG/HISTORY sachgerecht aktualisieren.
