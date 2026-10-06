# EDIFACT-Viewer: Prüfbericht Sicherheit, Datenschutz, Datenintegrität

Geprüft wurde die hochgeladene Version (Einzeldatei-HTML, rein clientseitig). Die verbesserte Version liegt in `EDIFACT-Viewer.html`.

## Sicherheit

| # | Befund | Schwere | Maßnahme |
|---|--------|---------|----------|
| 1 | **XSS** im Eigenschaften-Panel: Das UNB-Datum („Erstellt“) wurde ungeprüft in `innerHTML` geschrieben. Eine präparierte Datei konnte Skript im Viewer ausführen. | hoch | Format wird geprüft, Ausgabe wird maskiert. |
| 2 | **Keine Content-Security-Policy.** Ein einzelner Maskierungsfehler wie in 1 reichte für Datenabfluss. | hoch | Strenge CSP (`default-src 'none'`, Skript und Style per SHA-256-Hash, `connect-src 'none'`, `form-action 'none'`, `base-uri 'none'`). Selbst bei einer XSS-Lücke kann nichts versendet werden. |
| 3 | **CSV-Injection:** Zellen aus der Datei, die mit `=`, `+`, `-`, `@` beginnen, wurden unverändert exportiert und von Excel als Formel ausgeführt. | mittel | Apostroph-Präfix bei Text. Zahlen bleiben Zahlen. |
| 4 | **Rechenschritt-Bombe** in UTILTS: Mehrfach verwiesene Schritte bliesen die Formel exponentiell auf und froren den Tab ein. | mittel | Knoten- und Tiefenlimit in `stepExpr`. |
| 5 | **Prototyp-Schlüssel:** Werte wie `constructor` in Qualifier-Feldern lieferten Funktionen aus den Nachschlagetabellen. | niedrig | Tabellen ohne Prototyp. |
| 6 | **Keine Größen- und Mengenlimits** (Dateigröße, Anzahl Dateien, Ordnerrekursion, Text-DOM). | mittel | 50 MB je Datei, 25 Dateien je Vorgang, 40 Tabs, Rekursionstiefe 8, Textansicht auf 20.000 Zeilen begrenzt (Kopieren liefert alles). |
| 7 | Ungültiges UNA (fehlende, doppelte oder alphanumerische Trennzeichen) führte zu Laufzeitfehlern oder falscher Zerlegung. | niedrig | UNA wird validiert, sonst klare Fehlermeldung. |
| 8 | Dateinamen gingen ungefiltert in Download-Namen ein. | niedrig | Bereinigung (`safeName`). |

## Datenschutz

| # | Befund | Maßnahme |
|---|--------|----------|
| 1 | **Google Fonts** wurden von `fonts.googleapis.com` und `fonts.gstatic.com` geladen. Das überträgt die IP-Adresse an Google (DSGVO-relevant). Der Hinweis „nirgendwohin übertragen“ stimmte damit nicht. | Externe Schriften entfernt, Systemschriften verwendet. Die CSP verbietet jede Netzwerkverbindung, die Aussage in der Oberfläche ist jetzt zutreffend. |
| 2 | Kein `referrer`-Schutz. | `referrer: no-referrer`. |
| 3 | Lastgänge und Zählpunkte sind personenbezogene Daten. Es gab keine Möglichkeit, sie gezielt aus dem Speicher zu entfernen. | Schaltfläche „Alle schließen“ entfernt alle Daten aus dem Speicher. Es wird nichts persistent gespeichert (kein localStorage, keine Cookies). |

## Datenintegrität

| # | Befund | Maßnahme |
|---|--------|----------|
| 1 | `parseFloat` schnitt Werte still ab (`1,5abc` wurde 1). Das Dezimalzeichen aus UNA wurde ignoriert. | Strenge Zahlenerkennung nach UNA-Dezimalzeichen. Ungültige Werte werden ausgeschlossen **und** in „Prüfergebnis“ gemeldet. |
| 2 | Datumsprüfung nur per Präfix-Regex. `20261305…` wurde in ein anderes Datum umgerechnet, angehängter Text wurde akzeptiert. | Längenprüfung je Formatcode, Kalenderprüfung, Zeitzonenprüfung. |
| 3 | Mengensumme mit Gleitkomma-Rauschen (`0.1+0.2`). CSV-Export von Messwerten über `String(float)`, teils in Exponentialschreibweise. | Rundung der Summe auf 9 Nachkommastellen. Werte-CSV nutzt die Originalschreibweise. |
| 4 | Kontrollzählungen verwendeten `+""` (= 0) und lose Vergleiche. Mehrere UNB, verschachtelte UNH, Text vor dem ersten Segment und fehlendes Segmentende wurden nicht gemeldet. | Strenge Prüfung, zusätzliche Warnungen. |
| 5 | Doppelte Zeitstempel, Ende ≤ Beginn und wechselnde Einheiten in einer Reihe wurden nicht erkannt. | Neue Warnungen im Prüfergebnis. |
| 6 | Zeichensatz wurde nur geraten. | Auswertung der UNB-Angabe (UNOC → ISO 8859-1), sonst wie bisher. |
| 7 | Keine Möglichkeit, die geprüfte Datei eindeutig zu identifizieren. | SHA-256 der Originaldatei in den Eigenschaften. |
| 8 | Syntaxzeichen als Trennzeichen (z. B. `l`) zerstörten in der Textansicht HTML-Entitäten. | Zuerst zerlegen, dann maskieren. |

## Hinweise

- Die CSP bindet das Skript per Hash. **Nach jeder Änderung am Skript oder Style müssen die Hashes neu berechnet werden.** Dafür liegt `tools/update-csp-hash.py` bei.
- Wird die Datei in einer Umgebung eingebettet, die selbst Skripte einfügt (z. B. eine Artifact-Vorschau), kann die CSP diese blockieren. Dann die Datei lokal öffnen oder die CSP anpassen.
- `frame-ancestors` lässt sich per `<meta>` nicht setzen. Beim Hosting auf einem Server den Header `Content-Security-Policy: frame-ancestors 'none'` und `X-Content-Type-Options: nosniff` setzen.
- Der Viewer ändert die Quelldateien nie. Es ist ein reiner Leser.
