
# Workflow

## Ziel

Möglichst einfacher und schneller Möbelbau-Workflow in Fusion 360.

---

# Konstruktion

Der Anwender konstruiert Möbelteile normal in Fusion 360.

Empfehlung:
- lokale Orientierung konsistent halten
- Bauteile möglichst sauber ausrichten

---

# Materialzuweisung

Das technische Material wird als Physical Material gesetzt.

Beispiele:
- MDF
- Multiplex
- Massivholz

---

# Kanten definieren

Der Anwender weist Seitenflächen spezielle Appearances zu.

Beispiele:
- EDGE_ABS_1
- EDGE_ABS_2
- EDGE_WOOD

---

# Furniere definieren

Große Flächen können Furnier- oder HPL-Appearances erhalten.

---

# Zusatzinformationen

Über das Add-in werden zusätzliche Informationen gespeichert:
- Maserungsrichtung
- Notizen
- Fertigungshinweise
- Sonderbearbeitung

---

# CSV-Export

Das Exportskript:
- analysiert Bodies
- bestimmt Bounding Boxen
- erkennt Maße
- liest Material
- liest Appearances
- liest Attributes
- exportiert CSV

---

# Weiterverarbeitung

Die CSV-Datei wird:
- in Zuschnittsoftware importiert
- gemappt
- kalkuliert
- optimiert

---

# Arbeitsweise im Repo

Zusätzlich zum fachlichen Workflow gilt:

- jedes Thema startet als GitHub-Issue
- jedes Issue hat einen eigenen Thread
- jedes Issue bekommt einen eigenen Pull Request
- `main` wird nur über Pull Requests geändert
- offene Fragen werden im Issue gesammelt, nicht verteilt
