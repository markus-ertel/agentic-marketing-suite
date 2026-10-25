# Preisangaben und Streichpreise (Omnibus) – Prüfleitfaden v0.1

**Rechtsgrundlagen:** Preisangaben-RL 98/6/EG, Art. 6a (eingefügt durch Omnibus-RL (EU) 2019/2161); AT: § 9a Preisauszeichnungsgesetz (PrAG, in Kraft seit 20.07.2022); DE: § 11 PAngV; EuGH C-330/23 (Aldi Süd, 26.09.2024): auch Prozentangaben und „Preis-Highlights“ müssen sich auf den niedrigsten 30-Tage-Preis beziehen.

**Kernregel:** Wer eine Preisermäßigung bekannt gibt, nennt als früheren Preis den **niedrigsten Preis, der in den 30 Tagen vor der Ermäßigung** im selben Vertriebskanal verlangt wurde. Rabattprozent und Streichpreis werden von diesem Wert aus berechnet.

**Ausnahmen (nur nach Prüfung):** schrittweise steigende Ermäßigung (Bezug auf den Preis vor der ersten Stufe), Waren kürzer als 30 Tage am Markt, schnell verderbliche Waren. Im Katalog als `omnibus_exception` mit Begründung und Review-Referenz dokumentieren; das Werkzeug stuft den Befund dann nur als Warnung ein.

**Weitere Preisangaben:** Gesamtpreis inkl. USt.; Grundpreis (z. B. je kg/l) bei Waren nach Gewicht/Volumen (`unit_pricing_measure`); Versandkosten oder deren Berechnung; Preise in Feed, Produktseite und Checkout identisch. UVP-Vergleiche nur korrekt bezeichnet und nicht als eigene Preisermäßigung.

**Datenhaltung:** `lowest_price_30d` kommt aus einer Preishistorie (Shop-Export, Warenwirtschaft), nie aus Schätzung. Preishistorie mindestens 30 Tage rückwirkend aufbewahren.

**Gate:** Streichpreis ohne belegten `lowest_price_30d` oder mit abweichendem Wert = `blocked`.
