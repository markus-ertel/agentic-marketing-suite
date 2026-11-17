# Sicherheitsmeldungen

## Unterstützter Stand

Das Projekt befindet sich im Prototypstadium; die aktuelle Veröffentlichung ist v0.2.6. Sicherheitskorrekturen werden für den aktuellen Stand auf `main` bereitgestellt; für ältere Kopien gibt es keine zugesagte Rückportierung oder feste Reaktionszeit.

## Eine Schwachstelle melden

Bitte Sicherheitslücken vertraulich an [markus@ertel.at](mailto:markus@ertel.at) melden. Kein öffentliches Issue mit ausnutzbaren Details, echten Zugangsdaten oder personenbezogenen Daten anlegen.

Die Meldung sollte den betroffenen Commit, das Werkzeug oder Dokument, Voraussetzungen, reproduzierbare Schritte und die mögliche Auswirkung enthalten. Für Beispiele ausschließlich Testdaten verwenden. Eine Veröffentlichung der Details bitte mit dem Maintainer abstimmen.

## Betrieb und Grenzen

Die Suite enthält Anweisungen, Methoden und lokale Hilfsprogramme. Ein KI-Harness muss Berechtigungen, Dateizugriffe, Geheimnisverwaltung und externe Aktionen selbst technisch absichern. Ein bestandener lokaler Preflight erteilt keine Handlungserlaubnis. Weitere Laufzeitregeln stehen in [`.suite/SECURITY.md`](.suite/SECURITY.md) und [`.suite/GOVERNANCE.md`](.suite/GOVERNANCE.md).

Zugangsdaten außerhalb des Repositorys speichern. Vor öffentlichen Commits insbesondere Kontaktbestände, Briefings, Ergebnisse, Zustandsdateien und Protokolle prüfen. Bei versehentlich veröffentlichten Zugangsdaten diese beim Anbieter widerrufen und ersetzen; das Entfernen aus dem aktuellen Dateistand genügt nicht.
