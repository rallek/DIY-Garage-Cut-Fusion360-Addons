# Lastenheft

Stand: 2026-05-17 18:45 UTC

# Anforderungen

## Properties-Addin

Muss:
- Material zuweisen
- Fräszulage speichern
- Kanten speichern
- Hinweise speichern
- Export ausschließen

---

## Katalog

Gemeinsames:

```text
catalog.json
```

Typen:
- sheet
- bar
- edge
- profile
- hardware
- consumable

---

## Kantenmodell

Explizite Felder:

```text
edge_front
edge_back
edge_left
edge_right
```

Keine Appearance-Erkennung.

---

## Export

Muss exportieren:
- Maße
- Material
- Kanten
- Hinweise

Muss prüfen:
- vollständig
- oder ausgeschlossen

---

## Nicht-Ziele

Keine:
- Optimierung
- CAM
- CNC-Automatik
- QR-Erzeugung
