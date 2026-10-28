# INTEGRATION – Zusammenarbeit ohne Lock-in

Entdeckung: optionaler relativer Pfad `../business-dna/`, konfigurierbar. Andere Module funktionieren ohne Business-DNA unverändert. Der aufrufende Spezialist kann eine zielgerichtete `context-request` als JSON erstellen und einen passenden Context Pack lesen, sofern seine Laufzeit Zugriff bietet.

`marketing`: Ziele und Angebot; `branding`: wahre Ausgangslage; `creative`: Produktfakten; `website`: offizielle Unternehmensangaben; `pr`: belegt kommunizierbare Meilensteine; `advertising`: Werbeclaims und Nachweise; `noCRM`: freigegebene Produktdaten, nicht Kontakthistorie; `analytics`: Ziele, Messdefinitionen und Änderungen.

Die Schnittstelle definiert ein Datenformat, keinen Server. Transport per Dateisystem, CLI oder optionalen Adapter. Das Dashboard visualisiert Dateien/Status; es ist keine Wissens- oder Berechtigungsinstanz.

## Integration in diese Suite

Business-DNA ist als elfter optionaler Fachbereich registriert. Auch Social Media und E-Commerce können begrenzte Faktenkontexte beziehen; Shop-Katalog, Preise und Feeds bleiben beim Shop-Fachbereich. [SUITE.md](SUITE.md) beschreibt konkrete Anfragen, CLI, Statusmapping und Freigabegrenzen. Die ursprünglichen Paketunterlagen bleiben als Herkunftsdokumentation erhalten.

## Kundenäußerungen als externe Evidenz

noCRM kann einen gezielt beauftragten Gesprächsbezug liefern; Rohdaten/Personenbezug verbleiben dort. Wissensübernahme und Hypothesenstatus liegen bei Business-DNA. Die [Feedback-Integration](integrationen/customer-feedback/README.md) beschreibt redigierten Vorschlag, menschliche Bestätigung, versionierte Übernahme und expliziten nichtöffentlichen Hypothesenexport. Keine Pflichtabhängigkeit zu noCRM und keine automatische Übernahme anderer Gesprächsverläufe.
