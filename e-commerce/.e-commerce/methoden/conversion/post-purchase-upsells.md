# Post-Purchase-Upsells (1-Klick)

**Methoden-ID:** `conversion/post-purchase-upsells` · **Typ:** fachliche Arbeitsanleitung · **Version:** 0.1

## Zweck
Nach abgeschlossener Bestellung ein relevantes Folgeangebot spezifizieren, das mit einem Klick angenommen werden kann, ohne Zahlungs- und Verbraucherrecht zu verletzen.

## Eingaben und Umgang mit Lücken
Ziel/Auftrag, Sortiment, Zielmärkte, Shop-System, vorhandene Daten und Ressourcen soweit für diese Methode nötig heranziehen. Bestehende, berechtigt zugängliche Projektartefakte vor neuen Fragen nutzen. Fehlende Angaben markieren; reversible Hypothesen formulieren. Nur nachfragen, wenn das Ergebnis sonst riskant oder eine verbindliche Entscheidung unmöglich wäre.

## Vorgehen
1. Angebot und Relevanz bestimmen (Ergänzung, Nachfüllpack, Upgrade); Ablehnung mit gleich gut sichtbarer Option.
2. **Zahlungsmodus mit dem Zahlungsdienst klären** (`.e-commerce/recht/zahlung-psd2-sca.md`): entweder erneute Zahlung mit SCA bzw. zulässiger Ausnahme, oder Belastung des gespeicherten Zahlungsmittels als kundeninitiierte Zahlung mit gespeicherten Daten, oder MIT nur mit vorab dokumentierter Vereinbarung (Mandat). Ergebnis als `payment_mode` mit `payment_agreement_ref` dokumentieren.
3. Die Annahme ist ein **eigener Vertragsschluss**: Bestellbutton-Beschriftung, Gesamtpreis, Lieferbedingungen und Widerrufsinformation gelten erneut (`.e-commerce/recht/fernabsatz-button.md`).
4. Bestätigung und Rechnung für den Zusatzkauf; Erstattungsablauf bei Widerruf festlegen.
5. Kein Zeitdruck ohne reale Grundlage (Countdown nur, wenn das Angebot tatsächlich endet, belegt mit `truthful_basis_ref`).
6. Funnel-Definition mit `.e-commerce/tools/validate_compliance.py` prüfen; Test mit `../analytics/` planen.

## Ergebnis für den Menschen
**Upsell-Spezifikation** mit Zahlungsablauf, Texten, Rechtsprüfungsstatus und Testplan. Beginne mit einer klaren Empfehlung bzw. einem verwendbaren Entwurf. Kennzeichne Tatsachen, Hypothesen und ausstehende Freigaben.

## Grenzen
Die Methode entscheidet nicht über die PSD2-Einstufung einer konkreten Zahlung; das tun Zahlungsdienst und Acquirer nach ihren Regeln. Kein Upsell bei Zahlarten, die keine Folgebelastung zulassen, ohne neuen Zahlvorgang.

## Anwendungsfälle
- **Positiv:** Nach Kauf eines Kaffeevollautomaten: Entkalker-Set als 1-Klick-Angebot; Zahlungsdienst bestätigt Ablauf mit gespeicherter Karte, Kundin klickt „Zahlungspflichtig hinzufügen“, eigene Bestätigung folgt.
- **Negativ:** „Buche das Upgrade automatisch von der Karte ab, wenn die Kundin nicht innerhalb von 10 Minuten ablehnt“: blockiert (keine Zustimmung, kein Mandat, Dark Pattern).

## Qualitätssicherung / Red Flags
- `payment_mode` `stored_credential` oder `mit` ohne `payment_agreement_ref` ist `blocked`.
- Keine Speicherung von Zahlungsdaten durch das Modul.
- Keine erfundenen Preise, Bestände, Kennzahlen, Benchmarks oder Plattformfähigkeiten.
- Externe Änderungen nur gemäß `.e-commerce/AKTIONEN.md`; Rechtsfragen nach `.e-commerce/RECHT.md`.

## Übergaben und Ablage
Ergebnis außerhalb `.e-commerce/` als Markdown-/CSV-/JSON-Artefakt speichern. Weiterführende Methoden selektiv aus `.e-commerce/METHODEN.md` wählen. Bei tatsächlichen Änderungen STATE/LOG/HISTORY sachgerecht aktualisieren.
