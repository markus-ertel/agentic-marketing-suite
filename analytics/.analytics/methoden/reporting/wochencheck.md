# Wochencheck als wiederkehrender Analytics-Auftrag

## Zweck

Einen regelmäßigen Entscheidungsüberblick aus berechtigt zugänglichen Kennzahlen, Datenlücken und optional offenen Freigaben erstellen. Die Suite beschreibt das Verfahren; der vorhandene Harness übernimmt Ausführung, fachliche Einordnung und gegebenenfalls Einrichtung eines Zeitgebers.

## Einsatz und Eingaben

Konkreter Analyseauftrag mit Zweck, Quellen, Kennzahlen und Vergleichslogik. Bestehende Unterlagen gezielt lesen, fehlende wesentliche Angaben gebündelt klären und ein privates Profil vorbereiten. Keine Accountzugänge, automatische Befugnisse oder bisher nicht beobachtete Verbindungen erfinden. Der [Profilvertrag](../../schemas/weekly-review-profile.schema.json) beschreibt die Konfiguration; eine Profilreferenz ist kein Identitätsnachweis.

## Vorgehen

1. Entscheidungsfrage und Grenzen verstehen. Nur tatsächlich benötigte Datenquellen und minimierte Modellkontexte auswählen. Mit den bestehenden Analytics-Regeln Quelle, Zeitzone, Metrikdefinitionen und Population prüfen. Fehlende Daten als solche kennzeichnen.
2. [Wochencheck-Werkzeug](../../tools/WEEKLY_REVIEW.md) mit `plan` verwenden. Zeitfenster pro Quelle, private Ablage und tatsächliche Zugriffe prüfen. Eine vorhandene Einrichtung kann wiederkehrende lesende Läufe abdecken; keine neue Zustimmung pro Woche erfinden oder unnötig verlangen.
3. Erst mit tatsächlich geprüfter aktueller Befugnis `run --harness-authorized` aufrufen. Keine Quelle durch einen alten Zufallsfund ersetzen, keine Fehlerrückgabe mit `|| true` verbergen. Die exakten zurückgegebenen Laufpfade verwenden.
4. Technischen Status und Ergebnis-Hash prüfen. Ein unvollständiger oder blockierter Datenteil ergibt keinen grünen Wochenbericht. Verwertbare Teilergebnisse mit ihren Lücken berichten; fehlende Werte nicht als Null auslegen.
5. Mit vereinbartem `harness-context.json` arbeiten. Beobachtete Veränderungen beschreiben, Quelle/Zeitraum und Unsicherheit erhalten. Keine Kausalität oder repräsentative Wirkung erfinden. Auffälligkeiten gegen Trackingänderungen, Saisonalität und Alternativerklärungen prüfen; nötige Fachmethoden selektiv laden.
6. Separate fachliche Einordnung mit wenigen priorisierten nächsten Schritten schreiben. Freigabeübersicht nur als Momentaufnahme behandeln; menschliche Entscheidungen oder spätere Ausführung nicht daraus ableiten. Vorschläge an zuständige Fachbereiche formulieren, keine automatischen Budget-/Publikations-/Versandänderungen.
7. Ergebnis über den bereits eingerichteten, ausdrücklich erlaubten Weg bereitstellen. Keine Nachricht an unbekannte Empfänger versenden. Nach einem tatsächlichen erfolgreichen Probelauf auf Wunsch denselben Auftrag zeitgesteuert einrichten; keine zweite abweichende Fachlogik und keine neue eigene Runtime erzeugen.

## Ergebnis und Qualität

Ein belegbarer privater technischer Lauf und eine klar getrennte fachliche Einordnung mit wenigen Entscheidungen/Handlungsvorschlägen. Sprache verständlich halten. „Vollständig“ im technischen Lauf ist kein Fach- oder Rechtsfreigabestatus. Tatsächliche Lauf-/Benachrichtigungsergebnisse festhalten; einen Zeitplanwunsch nie als aktive Automation ausgeben.

## Grenzen

Keine automatischen Rechte, Wahrheitsprüfung, Signifikanz oder Verfügbarkeit zur geplanten Uhrzeit. Das Vorhandensein eines Skripts beweist weder eine eingerichtete Verbindung noch einen funktionierenden zeitgesteuerten Harness. Profil, Speicher, Modellverarbeitung und Credentials müssen in der realen Umgebung passend eingerichtet sein. Ohne Zeitgeber funktioniert derselbe Auftrag manuell.
