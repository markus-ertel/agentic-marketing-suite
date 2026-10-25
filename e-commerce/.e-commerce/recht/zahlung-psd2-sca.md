# Zahlung, SCA und 1-Klick-Upsells – Prüfleitfaden v0.1

**Rechtsgrundlagen:** PSD2 RL (EU) 2015/2366, Art. 97 (starke Kundenauthentifizierung); Delegierte VO (EU) 2018/389 (RTS SCA, Ausnahmen Art. 10–18); EBA Single-Rulebook-Q&A 2018_4031 (vom Zahlungsempfänger allein ausgelöste Kartenzahlungen auf Basis eines Mandats), 2018_4131 und 2019_4792; AT: Zahlungsdienstegesetz 2018 (ZaDiG 2018). Kartennetzregeln (Stored-Credential-Rahmenwerke) gelten zusätzlich über Acquirer/Zahlungsdienst.

**Einordnung für Upsells nach dem Kauf:**
| `payment_mode` | Bedeutung | Voraussetzung |
|---|---|---|
| `new_payment_sca` | neuer Zahlvorgang mit SCA oder zulässiger Ausnahme | keine besondere; sicherster Weg |
| `stored_credential_cit` | Kundin klickt, Zahlung mit gespeicherten Zahlungsdaten (kundeninitiiert) | Einwilligung zur Speicherung bei Erstkauf, `payment_agreement_ref`; SCA-Pflicht bzw. Ausnahme bestimmt der Zahlungsdienst |
| `mit_agreed` | vom Händler ausgelöste Zahlung ohne Mitwirkung (MIT) | **vorab** mit SCA eingerichtetes Mandat, das genau diese Art Folgezahlung abdeckt; `payment_agreement_ref` |

**Regeln:**
- MIT ist nicht der Weg, SCA für einen spontanen Zusatzkauf zu umgehen. Ein Upsell, bei dem die Kundin aktiv klickt, ist regelmäßig kundeninitiiert; die Einstufung trifft der Zahlungsdienst (`psp_confirmation_ref`).
- Mandatstext: Zweck, Umfang (Betrag/Art der Folgezahlungen), Dauer, Widerruf; mit Erstkauf eingeholt und gespeichert.
- Soft Declines (SCA nachgefordert) im Ablauf vorsehen: dann Weiterleitung zur Authentifizierung, kein stiller Abbruch, keine Mehrfachbelastung.
- Erstattungen sind Zahlungsvorgänge im Zielsystem: externe Aktion `modify_external` mit Betrag und Währung im `action-approval`.
- Das Modul speichert und verarbeitet **keine** Zahlungsdaten und löst keine Zahlung aus.

**Gate:** `stored_credential_cit` oder `mit_agreed` ohne `payment_agreement_ref` = `blocked`; ohne Bestätigung des Zahlungsdienstes = `warning` (Risikoübernahme durch verantwortliche Person).
