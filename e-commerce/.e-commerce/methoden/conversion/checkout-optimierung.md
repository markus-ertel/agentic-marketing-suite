# Checkout-Optimierung

**Methoden-ID:** `conversion/checkout-optimierung` · **Typ:** fachliche Arbeitsanleitung · **Version:** 0.1

## Zweck
Abbrüche im Warenkorb und Checkout mit belegten Ursachen senken, ohne Pflichtinformationen, Datenschutz oder Zahlungssicherheit zu opfern.

## Eingaben und Umgang mit Lücken
Ziel/Auftrag, Sortiment, Zielmärkte, Shop-System, vorhandene Daten und Ressourcen soweit für diese Methode nötig heranziehen. Bestehende, berechtigt zugängliche Projektartefakte vor neuen Fragen nutzen. Fehlende Angaben markieren; reversible Hypothesen formulieren. Nur nachfragen, wenn das Ergebnis sonst riskant oder eine verbindliche Entscheidung unmöglich wäre.

## Vorgehen
1. Ist-Ablauf dokumentieren (Schritte, Pflichtfelder, Zahlarten, Versandoptionen, Fehlermeldungen, Gastbestellung); Messdaten aus `../analytics/` nutzen, sonst Messplan erstellen.
2. Abbruchursachen priorisieren: unerwartete Kosten, Lieferzeit, fehlende Zahlart, Zwangsregistrierung, Formularfehler, Vertrauen, Performance.
3. Rechtsprüfung der Schlussseite: alle Kosten, wesentliche Merkmale, Lieferbedingungen und Laufzeiten unmittelbar vor dem Bestellbutton; eindeutige Beschriftung (`.e-commerce/recht/fernabsatz-button.md`).
4. Maßnahmen als Spezifikation (Feldliste, Ablaufdiagramm, Texte) mit Hypothese und Messgröße je Maßnahme.
5. Zahlungsintegration mit gehosteten Feldern/Weiterleitung bevorzugen (`.e-commerce/recht/pci-dss.md`); SCA-Ablauf mit dem Zahlungsdienst klären.
6. Wirkung nach `messung/funnel-ab-tests` prüfen.

## Ergebnis für den Menschen
**Checkout-Spezifikation mit priorisierter Maßnahmenliste** und Messplan. Beginne mit einer klaren Empfehlung bzw. einem verwendbaren Entwurf. Kennzeichne Tatsachen, Hypothesen und ausstehende Freigaben.

## Grenzen
Keine Umsetzung im Shop ohne Auftrag und Freigabe. Barrierefreiheit (BaFG/EAA) und Datenschutz sind mitzuprüfen, ersetzen aber keine Fachprüfung (`../.suite/legal/barrierefreiheit.md`).

## Anwendungsfälle
- **Positiv:** Hohe Abbrüche auf der Versandseite, weil Kosten erst dort erscheinen: Versandkosten bereits auf der Produktseite angeben, Gastbestellung ermöglichen, Wirkung messen.
- **Negativ:** „Lass den Hinweis auf Versandkosten bis nach dem Klick weg, das erhöht die Conversion“: ablehnen (Preisangaben- und Fernabsatzrecht).

## Qualitätssicherung / Red Flags
- Keine Pflichtinformationen entfernen, um Schritte zu sparen.
- Keine erfundenen Abbruchquoten.
- Keine erfundenen Preise, Bestände, Kennzahlen, Benchmarks oder Plattformfähigkeiten.
- Externe Änderungen nur gemäß `.e-commerce/AKTIONEN.md`; Rechtsfragen nach `.e-commerce/RECHT.md`.

## Übergaben und Ablage
Ergebnis außerhalb `.e-commerce/` als Markdown-/CSV-/JSON-Artefakt speichern. Weiterführende Methoden selektiv aus `.e-commerce/METHODEN.md` wählen. Bei tatsächlichen Änderungen STATE/LOG/HISTORY sachgerecht aktualisieren.
