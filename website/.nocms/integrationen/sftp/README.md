# SFTP-Publishing · Capability v0.1

**Live-Ausführung:** Die [getrennte Ausführung](../../../../.suite/EXECUTOR.md) administrativ einrichten. `execute` als separates Ausführungskonto aus der geschützten Installation mit isoliertem Python (`python3 -I`) starten. Ohne Policy bleibt die Aktion gesperrt.

## Zweck und Voraussetzungen

Ein geprüftes Website-Dateiset über das vorhandene OpenSSH-CLI `sftp` übertragen. Python 3.9+, OpenSSH, ein vorbereitetes Zielverzeichnis, vorab unabhängig verifizierte Host-Keys und passende SSH-Kontorechte sind erforderlich. Standardverfahren ist ausschließlich SFTP; weder FTP/FTPS noch Remote-Löschung oder automatischer Host-Key-Trust sind implementiert.

## Konfiguration / Ein- und Ausgaben

[deployment.example.json](deployment.example.json) zeigt die projektbezogene Konfiguration. `credential_ref: WEBSITE_PRODUCTION` referenziert die vom Harness gesetzten Variablen `WEBSITE_PRODUCTION_KEY_FILE` und `WEBSITE_PRODUCTION_KNOWN_HOSTS_FILE`; keine Schlüssel oder Passwörter in der Projektdatei. SSH-Batch-Modus erwartet einen ohne Rückfrage nutzbaren Schlüssel. Eigene SSH-Konfigurationsdateien, Weiterleitungen und implizite LocalCommands werden nicht übernommen.

`--root` ist der Root der freizugebenden Arbeitskopie. Innerhalb der Suite ist `source` normalerweise `website/site/`; in einer separaten Website `site/`. Plan- und Freigabepfade müssen sich auf denselben Root beziehen. `release_archive` verweist auf das unveränderliche ZIP des Website-Releases außerhalb von `site/`; der Plan prüft jedes Archivmitglied gegen die Website und bindet auch den ZIP-Hash. Damit bleibt die vorhandene noCMS-Archivpflicht erhalten. `target`, Host, Port, Benutzer, Source und Credential-Referenz sind Bestandteil des freigegebenen Plans. `delete_remote` muss false und `verify_upload` true sein. Ziel muss bereits existieren; notwendige Unterordner werden angelegt.

```sh
# Archivordner vorher anlegen. Ein vorhandenes Release-ZIP wird nie ersetzt.
python3 website/.nocms/integrationen/sftp/publisher.py --root /arbeitskopie archive \
  --source site/ --output archiv/releases/site-v1.zip

python3 website/.nocms/integrationen/sftp/publisher.py --root /arbeitskopie plan \
  --config /privat/deployment.json --output /arbeitskopie/release-plan.json

python3 website/.nocms/integrationen/sftp/publisher.py --root /arbeitskopie execute \
  --plan /arbeitskopie/release-plan.json --approvals /privat/approvals.jsonl \
  --request-id req-konkreter-release --execution-log /privat/executions.jsonl \
  --key release-eindeutig-001 --harness-authorized
```

Zwischen beiden Schritten erstellt der Spezialist eine `approval-request` für die Plan-Datei mit deren SHA-256, Reviews, `action: publish` und dem vom Plan ausgegebenen exakten `target`. Der Mensch entscheidet; die tatsächliche Ausführungsprüfung folgt dem gemeinsamen [Capability-Vertrag](../../../../.suite/capabilities/REGISTRY.md). Planerstellung startet keine Verbindung.

## Prüfungen, Status und Recovery

Privat-/Schlüsseldateien, Punktordner außer `.htaccess`, Symlinks, unsichere Batch-Pfade und Dateien über 100 MiB werden abgewiesen. Es gibt keinen Remote-RM-Befehl. Die Quelldateien werden erneut geprüft und mit identischen Hashes lokal eingefroren. Temporäre Remote-Dateien werden zurückgelesen; erst nach identischen SHA-256 und erneuter Freigabeprüfung werden sie auf ihre Zielnamen umbenannt. Ein zweites Readback prüft die finalen Dateien.

`confirmed` bescheinigt diesen Transfernachweis, keine HTTP-, PHP-, DNS-, Browser- oder rechtliche Abnahme. Die Umbenennungen sind pro Datei, **kein atomarer Gesamt-Release und kein automatischer Rollback**. Bei Abbruch können temporäre Dateien oder eine teilweise aktualisierte Website verbleiben. Status `uncertain` bzw. ein liegen gebliebenes `started` blockiert automatische Wiederholung. Providerstand prüfen; temporäre Dateien nur nach gesonderter autorisierter Bestandsaufnahme bereinigen. Manche Server können bestehende Ziele nicht per Rename ersetzen; dann mit dokumentiertem Hostingverfahren arbeiten, nicht auf ungeprüftes Löschen ausweichen.

Kontrollierte Protokolltests liegen in `website/.nocms/tests/test_web_capabilities.py`. Ein reales Hoster-/SSH-Konto wurde damit nicht abgenommen. Nach Testbereitstellung die echte Website im Browser und mit dem jeweiligen PHP-Host prüfen.
