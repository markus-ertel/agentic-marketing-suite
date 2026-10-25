# Funnel-A/B-Tests (mit analytics)

**Methoden-ID:** `messung/funnel-ab-tests` · **Typ:** fachliche Arbeitsanleitung · **Version:** 0.1

## Zweck
Änderungen an Produktseite, Checkout, Order Bump oder Upsell als kontrollierte Experimente planen und gemeinsam mit `../analytics/` auswerten, statt Bauchgefühl als Ergebnis zu verkaufen.

## Eingaben und Umgang mit Lücken
Ziel/Auftrag, Sortiment, Zielmärkte, Shop-System, vorhandene Daten und Ressourcen soweit für diese Methode nötig heranziehen. Bestehende, berechtigt zugängliche Projektartefakte vor neuen Fragen nutzen. Fehlende Angaben markieren; reversible Hypothesen formulieren. Nur nachfragen, wenn das Ergebnis sonst riskant oder eine verbindliche Entscheidung unmöglich wäre.

## Vorgehen
1. Hypothese formulieren: Änderung → erwartete Verhaltensänderung → Geschäftswirkung.
2. Primäre Messgröße festlegen, die Geschäftswert abbildet (Deckungsbeitrag je Besuch oder Bestellung, nicht nur Klick- oder Annahmequote); Schutzmetriken (Retouren, Stornos, Beschwerden, Ladezeit).
3. Varianten, Zuteilung (zufällig, stabil je Person/Sitzung), Laufzeit über volle Wochenzyklen, Mindeststichprobe und Abbruchregel vor Start festlegen; mit `../analytics/` abstimmen und deren Methoden nutzen.
4. Einwilligung für Test- und Tracking-Werkzeuge prüfen (`../.suite/legal/datenschutz.md`); Preisunterschiede zwischen Varianten nur nach Rechtsprüfung (Preisdiskriminierung, Preisangaben).
5. Test in der Funnel-Definition (`experiment`) dokumentieren; Aktivierung im Shop-System ist eine externe Aktion.
6. Auswertung durch `../analytics/`; Entscheidung und Version in HISTORY festhalten.

## Ergebnis für den Menschen
**Testplan** (Hypothese, Metriken, Design, Stoppregel, Verantwortliche) und Übergabe an analytics. Beginne mit einer klaren Empfehlung bzw. einem verwendbaren Entwurf. Kennzeichne Tatsachen, Hypothesen und ausstehende Freigaben.

## Grenzen
Kein Test ohne ausreichenden Traffic; bei geringer Fallzahl qualitative Methoden oder Vorher-nachher mit klar benannten Grenzen. Das Modul berechnet keine Signifikanz selbst, sondern übergibt an `../analytics/`.

## Anwendungsfälle
- **Positiv:** Zwei Varianten eines Order-Bump-Textes, primäre Messgröße Deckungsbeitrag je Bestellung, Schutzmetrik Retourenquote, Laufzeit 4 Wochen, Auswertung durch analytics.
- **Negativ:** „Teste fünf Preise gleichzeitig bei 200 Besuchen pro Woche und nimm den besten nach zwei Tagen“: abraten (Fallzahl, Peeking, Preisrecht).

## Qualitätssicherung / Red Flags
- Kein Abbruch beim ersten „signifikanten“ Zwischenstand.
- Keine Kausalbehauptung ohne Testdesign.
- Keine erfundenen Preise, Bestände, Kennzahlen, Benchmarks oder Plattformfähigkeiten.
- Externe Änderungen nur gemäß `.e-commerce/AKTIONEN.md`; Rechtsfragen nach `.e-commerce/RECHT.md`.

## Übergaben und Ablage
Ergebnis außerhalb `.e-commerce/` als Markdown-/CSV-/JSON-Artefakt speichern. Weiterführende Methoden selektiv aus `.e-commerce/METHODEN.md` wählen. Bei tatsächlichen Änderungen STATE/LOG/HISTORY sachgerecht aktualisieren.
