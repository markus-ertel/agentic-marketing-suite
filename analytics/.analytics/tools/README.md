# Lokale Analysetools

`evaluate_csv.py` vergleicht zwei CSV-Zeitfenster rein deskriptiv. Es nutzt ausschließlich Python-Standardbibliothek, stellt keine Netzwerkverbindungen her, verändert niemals Quell-CSV und nimmt keine externen Aktionen vor. Additive Metriken werden summiert; Raten als **Summe Zähler / Summe Nenner** berechnet.

```sh
python3 .analytics/tools/evaluate_csv.py \
  --input .analytics/beispiele/topaca-demo-synthetisch.csv \
  --metric branded_search_clicks \
  --period-a 2026-08-31:2026-09-27 \
  --period-b 2026-09-28:2026-10-25 \
  --expected-direction up
```

Optional `--denominator impressions` für gewichtete Raten, `--segment-column` und `--segment` für Segmentfilter, `--output` für JSON-Datei. Keine Signifikanztests, kein Modell-Fitting, keine Causal-Lift-Auswertung. Vor produktivem Betrieb Quellen, Zeitzone, Granularität, Rechenlogik und Datenschutz prüfen.

## Privater Wochencheck

[weekly_review.py](weekly_review.py) führt einen einmaligen, profilgesteuerten Datenteil aus. [WEEKLY_REVIEW.md](WEEKLY_REVIEW.md) beschreibt Demo, Profil, Berechtigungen, Ausgaben, Datenschutz und vollständige/teilweise/blockierte Ergebnisse. Die fachliche Bewertung und ein optionaler Zeitplan gehören zum Harness.
