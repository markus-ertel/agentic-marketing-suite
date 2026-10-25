# PCI DSS und Kartendaten – Prüfleitfaden v0.1

**Grundlage:** PCI DSS v4.0.1 und Self-Assessment Questionnaire A (SAQ A, Revision Januar 2025) des PCI Security Standards Council; FAQ 1588 zu den Skript-Kriterien. Vertraglich verpflichtend über Acquirer bzw. Zahlungsdienst, nicht staatliches Recht.

**SAQ A** kommt nur in Frage, wenn alle Kartendaten-Funktionen vollständig an einen PCI-DSS-konformen Dienst ausgelagert sind (Weiterleitung oder eingebettetes iFrame/gehostetes Zahlungsformular des Dienstes) und der Händler keine Kartendaten speichert, verarbeitet oder überträgt. Seit der Revision 2025 gehört zur Eignung, dass der Händler bestätigt, dass seine Seite **nicht anfällig für Skriptangriffe** ist, die das Zahlungsformular beeinträchtigen können — entweder durch eigene Schutzmaßnahmen (ähnlich Anforderungen 6.4.3/11.6.1: Skriptinventar, Integrität, Änderungserkennung) oder durch Bestätigung des Zahlungsdienstes. Andernfalls SAQ A-EP oder SAQ D.

**Regeln für Empfehlungen:**
- Gehostete Zahlungsfelder/Weiterleitung bevorzugen; keine eigenen Kartenformulare, kein Logging von Zahlungsfeldern, keine Kartendaten in Bestellnotizen oder Exporten.
- Drittskripte auf Checkout- und Zahlungsseiten minimieren (Tag-Manager, Chat, A/B-Test-Werkzeuge); jede Erweiterung ist eine Sicherheitsänderung.
- Funnel-Plugins für 1-Klick-Upsells nur mit tokenisierten Zahlungsdaten des Zahlungsdienstes.
- Die konkrete SAQ-Einstufung und die aktuellen Dokumente mit Acquirer/Zahlungsdienst klären; Datum und Version festhalten.

**Gate:** Architektur mit Kartendaten im eigenen Code ohne geklärte PCI-Einstufung = `blocked`.
