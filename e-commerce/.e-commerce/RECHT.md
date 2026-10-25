# RECHT — Rechts- und Risikoregeln für Online-Shops (AT/EU-Fokus)
**Stand der Recherche:** 25.10.2026 · ergänzt `../.suite/LEGAL.md` und `../.suite/legal/`. **Keine anwaltliche Einzelfallberatung.** Zielmärkte, Warengruppe, B2C/B2B und Zeitpunkt der Umsetzung bestimmen weitere Pflichten; Quellen in `.e-commerce/QUELLEN.md`.

## Prüfthemen
| Thema | Kernregel | Leitfaden | Werkzeugprüfung |
|---|---|---|---|
| Bestellbutton, Fernabsatz | Button eindeutig „zahlungspflichtig bestellen“ o. Ä.; Pflichtinformationen unmittelbar davor; Widerrufsbelehrung | `.e-commerce/recht/fernabsatz-button.md` | `button_label` bei Folgekäufen |
| Preisangaben, Streichpreise | Gesamtpreis inkl. USt., Grundpreis, Versandkosten; Ermäßigung bezieht sich auf den niedrigsten Preis der letzten 30 Tage | `.e-commerce/recht/preisangaben-omnibus.md` | `lowest_price_30d` bei `sale_price`/`compare_at_price` |
| Dark Patterns, Zusatzleistungen | keine Voreinstellung kostenpflichtiger Extras, keine falsche Dringlichkeit, kein Confirmshaming | `.e-commerce/recht/dark-patterns.md` | `preselected`, `requires_explicit_consent`, `urgency`, `decline_label` |
| Zahlung, 1-Klick-Upsell | SCA nach PSD2; MIT nur mit vorab vereinbartem Mandat; Einstufung durch Zahlungsdienst | `.e-commerce/recht/zahlung-psd2-sca.md` | `payment_mode`, `payment_agreement_ref`, `psp_confirmation_ref` |
| Kartendaten | SAQ A nur bei vollständig ausgelagerter Zahlungsseite und Skriptschutz | `.e-commerce/recht/pci-dss.md` | – (Architekturprüfung) |
| Datenschutz, Tracking | Rechtsgrundlage, Einwilligung für Test- und Marketing-Tracking | `../.suite/legal/datenschutz.md` | – |
| Barrierefreiheit | BaFG/EAA für Online-Shops (B2C) seit 28.06.2025, Kleinstunternehmen-Ausnahme prüfen | `../.suite/legal/barrierefreiheit.md` | – |
| Produktinformationen | GPSR-Angaben (Hersteller, Kennzeichnung, Warn- und Sicherheitshinweise) im Online-Angebot | `.e-commerce/methoden/katalog/produktdaten-varianten.md` | – |
| Werbeaussagen | Claims, Bewertungen (Hinweis, ob und wie geprüft), Vergleiche | `../.suite/legal/werberecht.md` | – |

## Externe Aktionen
Jede **Preis-, Zahlungs-, Erstattungs- oder Feed-Änderung** ist eine externe Aktion und braucht einen `action-approval` mit Reviews derselben Artefaktversion (`.e-commerce/AKTIONEN.md`). Zusätzlich gilt: Bei Preisänderung `legal`-Review zur Preisangabe; bei Funnel mit Folgekauf `legal`-Review zu Fernabsatz/Dark Patterns und Bestätigung des Zahlungsdienstes.

## Disposition
`pass | warning | blocked | not_applicable | not_checked` mit Quelle und Zeitpunkt. Ein grüner Lauf von `generate_gmc_feed.py` oder `validate_compliance.py` ist **strukturell**, nie `legal: pass`. Unklare Einzelfälle (Ausnahmen der 30-Tage-Regel, Abo-Modelle, Versicherungs-Zusatzprodukte, regulierte Warengruppen) juristisch beurteilen lassen.
