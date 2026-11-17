# Geprüfte Quellen als lokale Importdateien vorbereiten

`export_platform.py` erzeugt lokale Dateien, führt keinen Plattformimport und keine Veröffentlichung aus. Es gibt keine Verbindung zu einem Werbekonto oder Scheduler. `--check` prüft nur die unterstützten Struktur-/Längengrenzen und erzeugt nichts; es ist keine vollständige fachliche/rechtliche Abnahme.

```sh
python3 .suite/tools/export_platform.py google-ads advertising/kampagne.json --check
python3 .suite/tools/export_platform.py social-csv social-media/job.json --check --scheduler-time-zone Europe/Vienna
python3 .suite/tools/export_platform.py email-html noCRM/entwurf.json --check
```

Für Ausgabe `--out`, `--log`, `--request-id` und `--target` angeben. Die aktuelle nachgewiesene menschliche Freigabe muss genau Quellpfad/Hash, Aktion (`spend`, `publish`, `send`) und Ziel binden. Geänderte Datei, Widerruf oder Ablauf blockieren. Keine Entscheidung erfinden. Ausgabe wird nicht überschrieben. Der Export ist kein Freigabenachweis für später veränderte Dateien; nach Bearbeitung neue Version/Prüfung/Freigabe verlangen. Vor dem tatsächlichen Import erneut G2/G3/G4, Konto und aktuellen Widerrufsstand prüfen.

## Google Ads Editor

Das optionale `search_ads`-Objekt im Advertising-Manifest enthält Kampagnenname, Gruppen, HTTPS-Ziel, 3–15 Headlines (max. 30), 2–4 Descriptions (max. 90), Pfade (max. 15) und Keywords mit Match-Typ. CSV enthält Kampagne **Paused**, Tagesbudget sowie Start-/Enddatum. Gesamtbudget und Währung dürfen die menschliche Freigabe nicht überschreiten. Weil die Datei nur das Tagesbudget überträgt, wird der Export blockiert, wenn Tagesbudget × Laufzeittage das freigegebene Gesamtbudget übersteigt.

Das Lifetime-Limit ist **kein technisch durch diese CSV erzwungenes Plattformlimit**. Google Ads verwendet ein durchschnittliches Tagesbudget; vor Aktivierung Kontowährung, Laufzeit, tatsächliche Ausgabengrenzen, Sprache, Region, Gebotsstrategie und weitere Kontoeinstellungen prüfen. Neue Kampagnen können Editor-Defaults übernehmen. Importvorschau kontrollieren und fehlende Einstellungen bewusst ergänzen; eine manuelle Aktivierung ist eine eigene Ausführung, die aktuelle Autorisierung erfordert. Kein Live-Testimport wurde durchgeführt.

## Buffer-/Scheduler-CSV

Unterstützt werden Text- und Einzelbild-Posts mit `Text`, `Image URL`, `Tags`, `Posting Time`. Mehrere Bilder, Karussells, Videos, Stories/Reels und derzeit Pinterest/YouTube werden abgelehnt, statt Inhalte zu verlieren. Keine implizite Umwandlung in einen anderen Posttyp. Eine Datei enthält nur einen Kanal und ein Konto; Plattform-/Kontozuordnung vor dem Import selbst wählen und prüfen. `Tags` bleibt leer, weil ein Suite-Kanalname kein vorhandenes Buffer-Tag ist.

Geplante Posts brauchen eine zonierte `scheduled_at`-Zeit und die tatsächliche IANA-Zeitzone des Scheduler-Kanals als `--scheduler-time-zone`. Ausgabe ist `YYYY-MM-DD HH:mm` in dieser Zone. Sekunden und mehrdeutige lokale Zeiten während der Herbstumstellung werden abgelehnt; nicht still runden oder umplanen. Ohne Planzeit bleibt das Feld leer: ein Import kann dann einen Queue-Slot wählen, deshalb vor Bestätigung prüfen.

Öffentliche direkte Bild-URLs und ihre tatsächliche Sichtbarkeit/Dateigröße im Import prüfen; die Offline-Prüfung ruft sie nicht ab. Maximal 100 Zeilen; Buffer Free erlaubt höchstens zehn und kann bei zu wenig freien Queue-Plätzen weitere Zeilen auslassen. Deshalb Kontolimit, Importvorschau und tatsächliche Zeilenzahl kontrollieren. Keine reale Scheduler-Importabnahme erfolgt.

## E-Mail

Erzeugt in einem neuen Ordner `subject.txt`, HTML-escaped `body.html` und `body.txt`. Kein Versand, keine Vorlage mit verstecktem Tracking und keine Empfänger-/Providerverbindung. noCRM-Zweck, Einwilligung/Rechtsgrundlage und konkreten Empfänger vor Versand separat prüfen. Ein Datei-Export ist kein Provider-Annahmenachweis.

Primärquellen, geprüft 27.10.2026: [Google-Ads-CSV-Spalten](https://support.google.com/google-ads/editor/answer/57747), [Laufzeitformat](https://support.google.com/google-ads/editor/answer/57775), [Buffer-Bulk-Upload und Grenzen](https://support.buffer.com/articles/how-to-upload-posts-in-bulk-to-buffer-cTIhl4mv6H).
