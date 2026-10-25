# AKTIONEN — externe Aktionen, Adapter und Freigaben

**Grundsatz:** Das Modul ist führende Quelle (Schreib-Owner) für Katalog, Preislogik, Feed und Funnel-Spezifikation. Das Live-Shop-System (Shopify, WooCommerce, Shopware, Eigenbau) und Zahlungsdienste sind externe Laufzeitsysteme in eigener Verantwortung und eigenem Repository. Jeder schreibende Zugriff dorthin läuft **ausschließlich über einen Adapter** mit Freigabe.

## Freigabepflichtige Aktionen
| Ziel (`target`-Präfix) | Beispiel | Suite `action` | Zusatz im `action-approval` | Mindest-Reviews (G2 + G3) |
|---|---|---|---|---|
| `ecommerce:price_update` | Preis-, Streichpreis-, Aktions- oder Gutscheinänderung | `modify_external` | `expires_at` = Aktionsende | `technical` (Werkzeuglauf) + `legal` (Preisangaben) |
| `ecommerce:inventory_sync` | Bestands- oder Verfügbarkeitsabgleich, Massenupdate | `modify_external` | Artikelanzahl in `notes` | `technical` + `legal` oder begründet `not_applicable` |
| `ecommerce:feed_publish` | Feed-Upload, Abruf-URL ändern, Merchant-API-Insert | `publish` | SHA-256 der Feed-Datei | `technical` + `legal` |
| `ecommerce:funnel_publish` | Funnel/Order Bump/Upsell/Test aktivieren oder ändern | `publish` | Funnel-Version | `expert` + `legal` (+ `privacy` bei Tracking) |
| `ecommerce:payment_config` | Zahlarten, gespeicherte Zahlungsmittel, Mandatstext | `modify_external` | Bestätigung Zahlungsdienst | `security` + `legal` |
| `ecommerce:refund` | Erstattung, Gutschrift | `modify_external` | `budget_limit` + `currency` = Betrag | `expert` + `legal` oder begründet `not_applicable` |
| `ecommerce:order_status` | Bestellstatus setzen, stornieren | `modify_external` | Bestellreferenz ohne Personendaten | `expert` + `legal`/`privacy` |
| `ecommerce:delete` | Produkt, Feed-Datenquelle oder Funnel löschen | `delete` | Wiederherstellungsweg | `technical` + `legal` |

`target` vollständig, z. B. `ecommerce:feed_publish:merchant-center/<konto>/<datenquelle>` oder `ecommerce:price_update:shop/<system>/<sku-liste-datei>`. Kontokennungen ohne Geheimnisse.

## Ablauf
1. Artefakt erstellen (Katalogversion, Feed-Datei, Funnel-JSON) und SHA-256 bilden.
2. Lokaler Preflight: `generate_gmc_feed.py` bzw. `validate_compliance.py` ohne Fehler.
3. Reviews derselben Artefaktversion; Freigabe durch einen Menschen bzw. eine verantwortliche Rolle (nie KI).
4. Adapter führt **genau** die freigegebene Aktion aus: Dry-run bzw. Vorschau zuerst, Idempotenzschlüssel, keine Ausweitung (z. B. nicht mehr Artikel als freigegeben).
5. Read-back: Zielsystem lesen (Preis, Bestand, Datenquellenstatus) und Ergebnis mit externer ID in `.e-commerce/LOG.md`.
6. Timeout oder unklare Antwort → `execution_status: uncertain`, Status abfragen, **nicht** blind wiederholen.
7. Neue Version (geänderter Preis, neue Feed-Datei) = neue Freigabe.

## Adaptervertrag (Mindestinhalt)
Ein Adapter wird pro Zielsystem getrennt beschrieben und liegt außerhalb der Methodenbibliothek. Er dokumentiert: unterstützte Aktionen, Authentifizierung über Secret-Store, Dry-run/Vorschau, Idempotenz, Read-back, Rate-Limits, Fehlerbilder, Rückmeldung als `execution_external_id`. Dieses Modul liefert **keinen** produktiven Adapter.

## Nicht freigabepflichtig
Lokale Entwürfe, Kataloge, Feed-Dateien, Funnel-Spezifikationen, Analysen und Prüfungen ohne Schreibzugriff auf externe Systeme.
