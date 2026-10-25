# Shop-System-Auswahl (Shopify, WooCommerce, Shopware, Eigenbau)

**Methoden-ID:** `strategie/shop-system-auswahl` · **Typ:** fachliche Arbeitsanleitung · **Version:** 0.1

## Zweck
Ein Shop-System wählen oder einen Wechsel bewerten, das zu Sortiment, Märkten, Prozessen, Budget und Betriebsfähigkeit der Organisation passt — nicht zum Funktionsumfang einer Werbebroschüre.

## Eingaben und Umgang mit Lücken
Ziel/Auftrag, Sortiment, Zielmärkte, Shop-System, vorhandene Daten und Ressourcen soweit für diese Methode nötig heranziehen. Bestehende, berechtigt zugängliche Projektartefakte vor neuen Fragen nutzen. Fehlende Angaben markieren; reversible Hypothesen formulieren. Nur nachfragen, wenn das Ergebnis sonst riskant oder eine verbindliche Entscheidung unmöglich wäre.

## Vorgehen
1. Anforderungen nach Muss/Soll trennen: Sortiment und Varianten, B2C/B2B, Märkte/Sprachen/Währungen, Steuerlogik, Zahlarten, Versand, Schnittstellen (ERP, Warenwirtschaft, Merchant Center), Funnel-Bedarf.
2. Betriebsmodell klären: SaaS (z. B. Shopify), selbst gehostetes Open Source mit Plugins (z. B. WooCommerce, Shopware Community), Enterprise-Lizenz oder Eigenbau; wer übernimmt Updates, Sicherheit, Hosting, Backups?
3. Gesamtkosten über 3 Jahre als Formel aufstellen: Lizenz/Abo + Transaktions- und Zahlungsgebühren + Plugins/Apps + Hosting + Pflege + Migration. Fehlende Preise als Platzhalter, nicht schätzen und als Fakt ausgeben.
4. Risiken bewerten: Datenportabilität (Export von Produkten, Kunden, Bestellungen), Lock-in, Plugin-Abhängigkeiten, PCI-DSS-Umfang, Barrierefreiheit (BaFG/EAA), Performance.
5. Eigenbau nur empfehlen, wenn ein dokumentiertes Alleinstellungsmerkmal im Kaufprozess besteht, das Standardsysteme nicht abbilden, und dauerhaft Entwicklungs- und Sicherheitskapazität vorhanden ist.
6. Fähigkeiten vor Entscheidung in aktueller Herstellerdokumentation verifizieren; Proof-of-Concept für kritische Muss-Anforderungen.

## Ergebnis für den Menschen
**Systementscheidungsvorlage** mit Primärempfehlung, Alternativen, Kostenformel, Risiken und PoC-Kriterien. Beginne mit einer klaren Empfehlung bzw. einem verwendbaren Entwurf. Kennzeichne Tatsachen, Hypothesen und ausstehende Freigaben.

## Grenzen
Keine verbindlichen Preis- oder Featureaussagen ohne aktuelle Herstellerquelle. Rechtliche und steuerliche Beurteilung (z. B. OSS-Verfahren) nur als Prüfhinweis. Die Methode trifft keine Vertragsentscheidung.

## Anwendungsfälle
- **Positiv:** Ein Kosmetikhändler mit 300 Artikeln in AT/DE ohne eigene IT will einen Shop: Empfehlung eines SaaS- oder gemanagten Systems mit Kostenformel, Exportpfad und PoC-Liste.
- **Negativ:** „Wir bauen unseren eigenen Shop, weil WooCommerce langsam ist“, ohne Messdaten und ohne Entwicklerteam: Eigenbau abraten, zuerst Performance messen (mit `../website/`) und Hosting/Plugins prüfen.

## Qualitätssicherung / Red Flags
- Keine Feature-Tabelle aller Systeme ohne Bezug zu den Muss-Anforderungen.
- Migrations- und Exportfähigkeit immer bewerten.
- Keine erfundenen Preise, Bestände, Kennzahlen, Benchmarks oder Plattformfähigkeiten.
- Externe Änderungen nur gemäß `.e-commerce/AKTIONEN.md`; Rechtsfragen nach `.e-commerce/RECHT.md`.

## Übergaben und Ablage
Ergebnis außerhalb `.e-commerce/` als Markdown-/CSV-/JSON-Artefakt speichern. Weiterführende Methoden selektiv aus `.e-commerce/METHODEN.md` wählen. Bei tatsächlichen Änderungen STATE/LOG/HISTORY sachgerecht aktualisieren.
