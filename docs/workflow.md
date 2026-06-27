# Workflow

Stand: 2026-05-17 18:45 UTC

# Konstruktion

Body modellieren.

---

# Material

Im Properties-Addin:
- Material wählen
- Fräszulage prüfen/anpassen

Appearance wird gesetzt.

Im Catalog-Addin:
- für `sheet`: Standard-Fräszugabe pflegen (0.0 bis 5.0 mm)
- für `edge`: Materialdicke pflegen (0.0 bis 10.0 mm)

---

# Kanten

Festlegen:
- Vorderkante als konkrete Seitenfläche
  (`long_pos`, `long_neg`, `short_pos`, `short_neg`)

Dann:
- vorne
- hinten
- links
- rechts

mit Kantenmaterial belegen.

---

# Hinweise

Freitext:
- lackieren
- ölen
- furnieren
- Sonderbearbeitung

---

# Export ausschließen

Nicht relevante Bodies markieren:
- Hilfsgeometrie
- Vorrichtungen
- temporäre Bodies

Im Properties-Addin dafür `Vom Export ausschließen` aktivieren. Der CSV-Export schreibt diese Bodies nicht in die Ausgabedatei.

---

# Analyse

Im Export-Addin `DIYGC Analyse` ausführen.

Die Analyse zählt sichtbare Bodies als:
- exportbereit
- ausgeschlossen (`exclude_from_export=true`)
- mit fehlenden oder inkonsistenten Angaben

Geprüft werden Materialzuordnung, Fräszulage, Kanten- und Oberflächenwerte passend zu den Typ-Capabilities.

---

# Export

CSV exportieren.

DIY Garage Cut übernimmt:
- Rohmaße
- Optimierung
- Labels
