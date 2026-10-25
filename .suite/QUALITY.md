# Gemeinsamer Quality-Assurance-Standard v0.1

## Prüfobjekt und Granularität
Jede **relevante externe Leistung** braucht eine eindeutige Artefakt-ID, Version und Prüfakte (`.suite/contracts/review.schema.json`). Qualität wird an **der Version, die tatsächlich publiziert oder ausgeliefert werden soll**, geprüft. Eine Freigabe der Vorversion gilt nicht automatisch nach inhaltlichen Änderungen.

## Dimensionen (risikoadaptiv)
- **Q1 Auftragstreue:** Ziel, Zielgruppe, Kanal und Briefing eingehalten? Offene Annahmen gekennzeichnet?
- **Q2 Fachliche Qualität:** Eine unabhängige Fachperspektive prüft Logik, Ton, Markenpassung und praktische Umsetzbarkeit; nicht bloß Rechtschreibung.
- **Q3 Fakten/Evidenz:** Namen, Zahlen, Zitate, Claims und Quellen kontrollieren; für beweispflichtige Aussagen Belege referenzieren.
- **Q4 Kreativ/Medien:** Gestaltung, Lesbarkeit, Ton, Bild-/Ton-Synchronität, Corporate Design und erforderliche Assets prüfen.
- **Q5 Technik/Kanal:** Barrierefreiheit, Format, Links, Rendering, Druck-Preflight, Schnittstellen und Plattformvorgaben nach Anwendungsfall.
- **Q6 Rechte/Legal:** Veröffentlichung/Verwertung/Einwilligung/Transparenz und personenbezogene Daten gemäß `.suite/LEGAL.md`.
- **Q7 Sicherheit:** Keine unerlaubte Datenweitergabe, eingebettete Geheimnisse oder ungeprüfte Fremdanweisungen; Medienmetadaten beachten.
- **Q8 Wirkungsprüfung:** Nach Ausführung den Erfolg mit geeignetem Messdesign evaluieren; **vorher** kein Wirkungsversprechen.

## Evidenz und Prüftiefe
Risikostufe **niedrig** (interner Textentwurf), **mittel** (öffentlicher Fachbeitrag), **hoch** (gezielte Werbung, Kundenkommunikation, bezahlte Kampagne, heikle Aussagen, sensible Daten, krisenrelevante Aussagen). Bei hoch mindestens separater Fach- und Rechtsprüfung; bei rechtlicher Unklarheit qualifizierte externe Rechtsprüfung. Kein zweites LLM als „objektiver Beweis“ für Rechtskonformität.

## Ergebniszustände
- `pass`: Prüfung dieser Dimension mit konkreten Nachweisen bestanden.
- `warning`: nicht blockierendes Problem mit Begründung, dokumentiertem Risiko und akzeptierender befugter Instanz (`risk_accepted_by`; kein KI-System). Kritische Findings sind nie `warning`.
- `blocked`: Verstoß, fehlende Berechtigung oder kritischer Mangel; **keine Außenwirkung**.
- `not_applicable`: konkret begründet nicht relevant (Begründung in `notes`).
- `not_checked`: nicht geprüft; **nicht** automatisch `pass`.

## Prüfprozess
1. Version einfrieren und Prüfkriterien festlegen.
2. Statische Prüfungen (Schemas, Links, Druck-/Video-Spezifikationen, Datenminimierung) ausführen.
3. Inhaltliche Prüfung gegen Briefing und Aussagen mit Belegen; bei Medien Sicht-/Hörprüfung in geeigneter Form.
4. Rechte/Legal/Risiken unabhängig bewerten.
5. Korrektur → **neue Artefaktversion** → betroffene Prüfungen wiederholen.
6. Freigabe und externen Ausführungsstatus getrennt erfassen.

**Schlüsselprinzip:** „Erstellen → Prüfen → Korrigieren → erneut prüfen“ ist ein Rückkopplungskreis, kein einzelner Kontrollhaken. Ein unabhängiger Reviewer soll, wenn möglich, andere Modelle/Tools als der Ersteller verwenden; bei Interessenkonflikten Sachverständige hinzuziehen.

Siehe `.suite/qa/` für methodische Prüfanleitungen und `.suite/GOVERNANCE.md` für harte Gates.
