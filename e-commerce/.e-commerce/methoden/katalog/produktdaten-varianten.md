# Produktdaten und Varianten

**Methoden-ID:** `katalog/produktdaten-varianten` · **Typ:** fachliche Arbeitsanleitung · **Version:** 0.1

## Zweck
Einen konsistenten, führenden Produktkatalog mit stabilen IDs, sauberen Varianten und belegten Attributen aufbauen, aus dem Shop, Feeds und Werbemittel gespeist werden.

## Eingaben und Umgang mit Lücken
Ziel/Auftrag, Sortiment, Zielmärkte, Shop-System, vorhandene Daten und Ressourcen soweit für diese Methode nötig heranziehen. Bestehende, berechtigt zugängliche Projektartefakte vor neuen Fragen nutzen. Fehlende Angaben markieren; reversible Hypothesen formulieren. Nur nachfragen, wenn das Ergebnis sonst riskant oder eine verbindliche Entscheidung unmöglich wäre.

## Vorgehen
1. Führende Datenquelle festlegen (ERP, Warenwirtschaft, Shop, Katalogdatei) und Schreib-Owner benennen.
2. Datenmodell nach `.e-commerce/FORMATE.md` anwenden: eine Zeile je kaufbarer Variante; `id` (SKU) stabil und eindeutig, `item_group_id` verbindet Varianten.
3. Variantenachsen definieren (`color`, `size`, `material`, `pattern`, `gender`, `age_group`); jede Variante einer Gruppe muss sich in mindestens einer Achse unterscheiden.
4. Identifikatoren erfassen: GTIN nur vom Hersteller bzw. aus GS1-Zuteilung, nie erfinden; sonst MPN + Marke; nur ohne beides `identifier_exists = no`.
5. Pflichtinformationen nach Warengruppe ergänzen (z. B. Grundpreis, Herstellerangaben und Sicherheitsinformationen nach GPSR, Energieeffizienz, Inhaltsstoffe).
6. Katalog mit `python3 .e-commerce/tools/generate_gmc_feed.py -i <katalog> --check-only` (vom Modulordner aus) prüfen und Befunde abarbeiten.
7. Stichproben gegen Produktseite und Warenwirtschaft abgleichen (Preis, Bestand, Bilder).

## Ergebnis für den Menschen
**Katalog (CSV/JSON) mit Datenqualitätsprotokoll** des Werkzeugs. Beginne mit einer klaren Empfehlung bzw. einem verwendbaren Entwurf. Kennzeichne Tatsachen, Hypothesen und ausstehende Freigaben.

## Grenzen
Die Methode erzeugt keine Produktfakten. Rechtliche Kennzeichnungspflichten einzelner Warengruppen sind fallweise zu prüfen. Bestandszahlen im Katalog sind eine Momentaufnahme, kein Live-Bestand.

## Anwendungsfälle
- **Positiv:** T-Shirt in 3 Farben × 4 Größen: 12 Zeilen mit gemeinsamer `item_group_id`, eindeutige SKUs, je Farbe eigenes Bild, GTINs aus der Lieferantenliste.
- **Negativ:** „Erfinde passende GTINs, damit Google die Artikel annimmt“: ablehnen; Hersteller-GTIN beschaffen oder `identifier_exists = no` korrekt verwenden.

## Qualitätssicherung / Red Flags
- Doppelte IDs, Varianten ohne Unterscheidungsmerkmal, fehlende Bilder je Farbvariante.
- Preis und Verfügbarkeit nie aus Werbetexten übernehmen.
- Keine erfundenen Preise, Bestände, Kennzahlen, Benchmarks oder Plattformfähigkeiten.
- Externe Änderungen nur gemäß `.e-commerce/AKTIONEN.md`; Rechtsfragen nach `.e-commerce/RECHT.md`.

## Übergaben und Ablage
Ergebnis außerhalb `.e-commerce/` als Markdown-/CSV-/JSON-Artefakt speichern. Weiterführende Methoden selektiv aus `.e-commerce/METHODEN.md` wählen. Bei tatsächlichen Änderungen STATE/LOG/HISTORY sachgerecht aktualisieren.
