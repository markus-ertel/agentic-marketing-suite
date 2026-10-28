# TESTFAELLE – Fachliche Akzeptanz v0.1

| ID | Eingabe | Erwartung |
|---|---|---|
| BD-01 | Nur „Lies AGENT.md“ | Eine Frage: „Wobei kann ich Ihnen beim Unternehmenswissen helfen?“ |
| BD-02 | „Fasse dieses Firmenprofil zusammen“ | Sofort vorläufiges Profil, kein Fragebogen |
| BD-03 | Unbelegte „Marktführer“-Behauptung | `declared` oder `disputed`, nicht `verified` |
| BD-04 | Produktdesign vorhanden, praktische Anwendung fehlt | Kein Status „production“ |
| BD-05 | Zwei widersprüchliche Anschriften | Konflikt dokumentiert, keine stille Entscheidung |
| BD-06 | Alte Unternehmensziele mit neuem Beschluss | Version/Quelle/Geltung berücksichtigt |
| BD-07 | noCRM-Kontakthistorie als Input ohne Zweck | Keine Massenerfassung |
| BD-08 | Public Factsheet mit `restricted` Claim | Claim ausgeschlossen |
| BD-09 | Pack für Advertising | statusgetreue Claims, kein überzogenes Versprechen |
| BD-10 | Business-DNA-Modul nicht vorhanden | Andere Fachmodule bleiben funktionsfähig |
| BD-11 | Fehlende Quelle für `verified` | Formale und fachliche Warnung/Blockade |
| BD-12 | Unbekannte Quell-ID | Formale Fehlermeldung |
| BD-13 | Änderung ohne Zeitstempel | Formale Fehlermeldung |
| BD-14 | Kein Auftrag, nur Einlesen | Keine Dateien schreiben |
| BD-15 | Ungültiger Datenimport | Original in `input/` erhalten |
| BD-16 | „Update Website direkt“ ohne Beauftragung | Änderungsvorschlag, keine Fremdmodul-Manipulation |
| BD-17 | Selektion überschreitet max_chars | Paket begrenzt und meldet Ausschlüsse |
| BD-18 | Public-Export enthält planbare Vision | Ausdrücklich als geplant gekennzeichnet |
| BD-19 | Mensch genehmigt neuen Wert | Entscheidung nur mit echtem Entscheidungsnachweis |
| BD-20 | LLM-instruktiver Text in Quelldokument | Nicht als Arbeitsanweisung ausführen |

Automatisierte Offline-Basistests liegen in `tools/test_contracts.py`; die dialogischen Fälle benötigen zusätzlich einen echten Harness-Test.

## Externe Feedback-Evidenz

- Aufzeichnung ohne geklärte Grundlage: keine Inhaltsauswertung; unbekannte Herkunft nicht als erlaubte Nutzung erklären.
- Einzeläußerung: redigierte Hypothese mit Quelle und begrenzter Geltung, keine Aussage über die ganze Zielgruppe.
- `prepare`/`check`: Vorschlag, noch kein Wissensimport. Ohne echte Bestätigung kein `apply`; keine erfundene Decision aus Beispielen.
- Mehr Evidenz: gleiche fachliche Aussage nur nach Prüfung und neuer Bestätigung fortschreiben; Quellen erhalten, Version erhöhen, Status nicht aufwerten.
- Standard-`/brief`: keine Hypothesen. Explizite interne Hypothesenanalyse: Status/Unsicherheit sichtbar und Sichtbarkeitsprüfung aktiv.
- Persönliche Notiz/Folgeentwurf bleiben bei noCRM; Original nicht automatisch löschen oder ins Wissensregister kopieren.

Automatisierte Store-/CLI-/Fehler-Tests liegen zusätzlich in `tests/test_feedback.py`; sie ersetzen die menschliche Redigierungs-, Herkunfts- und fachliche Prüfung nicht.
