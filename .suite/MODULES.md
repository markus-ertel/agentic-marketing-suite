# Modulregister v0.2

| Modul | Zuständigkeit | Geeignete eingehende Aufgaben | Möglicher Ausgabevertrag |
|---|---|---|---|
| marketing/ | Unternehmens-, Marketing- und Kommunikationsstrategie | Ziele, Positionierung, Marketingkonzept | Strategie, Zielgruppe, Leitplanken |
| pr/ | Medien, Öffentlichkeiten, Reputation | Presse, Journalist:innen, Krisen | Pitch, Q&A, Statement, Medienplan |
| social-media/ | Social-Strategie, Community, organischer Content | Redaktion, Kanalwahl, Posts, Reels | kanaladaptierte Pakete, Publishing-Manifest |
| website/ | Webberatung und noCMS | Audit, IA, Landingpage, Website | Sitemap, HTML/CSS/JS, Release |
| advertising/ | Bezahlte Werbung, Media und Kampagnen | Creative Brief, Anzeigen, Shopping | Mediaplan, Anzeigenset, Budgetfreigabe |
| creative/ | Design, Corporate Design, Medienproduktion | Key Visual, Print, Bild, Video, Audio | Quellen, Medien, Export und QA |
| noCRM/ | Individuelle 1:1-Kommunikation | Rückfrage, Begleitung, Antwortentwurf | Nachricht, rechtmäßiger Versandnachweis |
| analytics/ | Evidenz, Messung, unabhängige Wirkungsevaluation | Ergebnisse, Qualitätslücken, KPIs | Analyse, Hypothesen, Verbesserungsauftrag |
| e-commerce/ | Online-Shop-Beratung, Produktdaten, Feeds, Checkout und Angebote; kein Shop-Betrieb | Shop-System, Katalog, Merchant-Center-Feed, Checkout, Order Bump, Upsell, Preisaktion | Katalog (CSV/JSON), Feed (XML/TSV), Funnel-Spezifikation, Preis-/Feed-Freigabe |

**Zuständigkeit Produktfeed:** Schreib-Owner von Katalog und Feed ist `e-commerce/`; `advertising/` nutzt den Feed für Shopping-Kampagnen und meldet Befunde zurück.

**Regel:** Nur benötigte Module aktivieren. Benachbarte Verzeichnisse sind optionale Quellen, keine Ausführungsermächtigung. Direkter Fachauftrag bleibt beim Fachspezialisten, ein fachübergreifender Auftrag verwendet `.suite/WORKFLOW.md`.
