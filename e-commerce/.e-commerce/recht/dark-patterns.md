# Dark Patterns und Zusatzleistungen – Prüfleitfaden v0.1

**Rechtsgrundlagen:** UGP-RL 2005/29/EG (Irreführung, Aggressivität, Anhang I „schwarze Liste“, u. a. Nr. 7 falsche Befristung) mit Leitlinien der Kommission (2021/C 526/01, Abschnitt 4.2.7 Dark Patterns); AT: UWG; Verbraucherrechte-RL Art. 22 (Zusatzzahlungen nur mit ausdrücklicher Zustimmung, keine Voreinstellung) – AT: § 6c KSchG, DE: § 312a Abs. 3 BGB; DSA Art. 25 (VO (EU) 2022/2065) für Online-Plattformen (Marktplätze), nicht für reine Händler-Shops.

**Unzulässig bzw. `blocked`:**
- Vorausgewählte Kästchen oder automatisch hinzugefügte kostenpflichtige Artikel, Versicherungen, Spenden, Abos (`preselected: false` Pflicht).
- Countdown, „nur noch 2 auf Lager“, „15 Personen sehen gerade“ ohne reale, belegte Grundlage (`urgency.truthful_basis_ref`); Countdown, der beim Neuladen neu startet.
- Confirmshaming („Nein, ich will kein Geld sparen“), versteckte oder visuell unterdrückte Ablehnungsoption (`decline_label` gleichwertig).
- Versteckte Kosten, die erst im letzten Schritt erscheinen (Drip Pricing); erschwerte Kündigung von Abos.
- Automatische Annahme eines Angebots ohne aktive Handlung.

**Warnung, prüfen:** sozialer Beweis (Bewertungen, Verkaufszahlen) ohne Quelle; Standardauswahl teurerer Versandart; Vorauswahl kostenloser, aber datenintensiver Optionen (zusätzlich Datenschutz).

**Gate:** Jeder Punkt der ersten Liste = `blocked`; der Befund geht an die verantwortliche Stelle, nicht still „wegoptimiert“.
