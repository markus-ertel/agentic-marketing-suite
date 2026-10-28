# Zeitplanung durch die vorhandene Laufzeit

Die Suite liefert den fachlichen Wochencheck, ein privates Profil und einen einmaligen technischen Datenteil. Ein Zeitgeber löst den vorhandenen Harness-Auftrag aus. Hier wird weder eine neue Jobengine installiert noch ein bestimmtes Produkt vorausgesetzt.

## Einrichtung durch den Harness

1. **Manuell abnehmen:** Profil, tatsächliche Datenzugriffe, minimierte Modellverarbeitung, technischer Lauf und fachlicher Bericht funktionieren in der vorgesehenen Umgebung. Synthetischer Test und echte Kontoabnahme unterscheiden. Erstanmeldung oder noch fehlende Befugnis mit der Person klären.
2. **Tatsächlichen Auslöser prüfen:** Unterstützt die verwendete Laufzeit eine passende geplante Automation auf dem richtigen Host? Deren aktuellen Einrichtungsweg prüfen. Wenn nein, einen vorhandenen lokalen Zeitgeber mit einem unterstützten, tatsächlich getesteten Harness-Aufruf verbinden. CLI-Parameter nicht aus Erinnerung erfinden.
3. **Konkrete Registrierung vorbereiten:** Privater Profilpfad, vollständiger Harness-Auftrag, Arbeitsverzeichnis, Host, Zeitzone, Termin, erlaubte Credentials und Ergebnisablage bestimmen. Ein Shell-Zeitgeber allein mit `weekly_review.py` erzeugt nur technische Daten; die fachliche Auswertung braucht den bestehenden Harness. Keine neue Modell-/Provider-Engine in die Suite einbauen.
4. **Ausdrücklichen Zeitplanauftrag umsetzen:** Nur den vom Menschen tatsächlich gewünschten Termin registrieren; das Beispiel „Montag 07:00“ ist keine allgemeine Erlaubnis. Danach die tatsächliche Scheduler-ID/Bestätigung, Konfiguration und einen Testlauf im privaten Arbeitsbereich dokumentieren. Erst eine bestätigte Registrierung als `konfiguriert` bezeichnen. Sie beweist den zukünftigen Lauf noch nicht.
5. **Nichtverfügbarkeit vereinbaren:** Rechner/Host muss verfügbar sein; Rechte, Secret Store und Modellzugriff müssen auch ohne interaktive Sitzung funktionieren. Falls das nicht unterstützt wird, die Grenze nennen und manuell weiterarbeiten. Nicht heimlich Credentials in Scheduler-Dateien, öffentliche Repositories oder Prompttexte kopieren.
6. **Verpasste Termine behandeln:** `ask` = vor Nachholen rückfragen; `skip` = ausgelassenen Termin kenntlich machen; `latest_only` = höchstens einen frischen aktuellen Lauf gemäß Auftrag, kein stilles Nacharbeiten aller Wochen. Diese Policy übernimmt der tatsächlich eingerichtete Harness/Auslöser. Das Profil setzt sie nicht technisch durch.
7. **Ergebnis und Fehler melden:** Nur über einen verfügbaren, autorisierten Benachrichtigungsweg. Ein gescheiterter oder unterbrochener Lauf ist keine unauffällige Wochenzusammenfassung. Wiederholungen erzeugen eigene Laufverzeichnisse; keine `|| true`-Entwarnung oder unbeobachtete Erfolgsmeldung.

## Optionale technische Anschlussmöglichkeiten

Wenn schon vorhanden und passend autorisiert, können cron, launchd oder n8n den geprüften Harness-Auftrag auslösen. Der Harness erzeugt die konkrete Registrierung für die reale CLI/Umgebung und prüft sie; diese Suite liefert bewusst keine ungetesteten produktübergreifenden Befehlszeilen oder Pflichtvorlagen mit angenommenen Login-/Modellparametern. Ein bestehender Zeitgeber wird nicht durch einen zusätzlichen Suite-Daemon ersetzt.

GitHub Actions bleibt für Repository-/Testdaten zuständig. Geplante Arbeit an tatsächlichen Kennzahlendaten verwendet die vereinbarte private Umgebung und deren Geheimnisverwaltung, nicht die öffentliche Suite-CI.

Zum Entfernen/Ändern einer Automation den tatsächlich registrierten Auftrag anhand seiner ID ändern und den neuen Zustand prüfen. Keine behauptete Deaktivierung allein durch Änderung von `schedule` im Profil; die Scheduler-Registrierung muss real angepasst werden.
