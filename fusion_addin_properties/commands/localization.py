import locale

import adsk.core

from shared.catalog import get_catalog_types, get_type_capabilities, get_type_label

_STRINGS = {
    "de": {
        "body": "Körper",
        "body_prompt": "Einen Körper auswählen",
        "size": "Bauteilgröße (L x B x Dicke)",
        "filter_type": "Filter",
        "filter_all_types": "Alle Typen",
        "material": "Material",
        "material_none": "(Bitte wählen)",
        "trim_allowance": "Fräszulage (mm)",
        "trim_allowance_tooltip": "Numerischer Wert in mm (z. B. 0,5).",
        "grain_direction": "Maserungsrichtung",
        "grain_none": "Keine",
        "grain_length": "Längs",
        "grain_width": "Quer",
        "front_face": "Vorderkante (Fläche)",
        "edges_enabled": "Oberflächen definieren",
        "edges_section": "Oberflächen",
        "mode": "Modus",
        "mode_none": "Keine",
        "mode_all": "Alle gemeinsam",
        "mode_individual": "Individuell",
        "edge_all": "Kantenmaterial (alle)",
        "edge_none": "(Keine Kante)",
        "custom_text": "Text",
        "custom_text_value": "Freitext",
        "edge_front_enabled": "Vorne bekanten",
        "edge_front": "Kante vorne",
        "edge_back_enabled": "Hinten bekanten",
        "edge_back": "Kante hinten",
        "edge_left_enabled": "Links bekanten",
        "edge_left": "Kante links",
        "edge_right_enabled": "Rechts bekanten",
        "edge_right": "Kante rechts",
        "swap_left_right": "Links/Rechts tauschen",
        "surface_all_text": "Oberfläche (alle)",
        "surface_all": "Oberfläche (alle)",
        "top_enabled": "Oberseite bearbeiten",
        "top_text": "Oberfläche oben",
        "bottom_enabled": "Unterseite bearbeiten",
        "bottom_text": "Oberfläche unten",
        "swap_surfaces": "Oben/Unten tauschen",
        "exclude_from_export": "Vom Export ausschließen",
        "notes_section": "Fertigungshinweise",
        "surface_none": "(Keine Oberfläche)",
        "notes": "Fertigungshinweise",
        "apply": "Anwenden",
        "face_prompt": "Planare Seitenfläche wählen",
    },
    "en": {
        "body": "Body",
        "body_prompt": "Select a body",
        "size": "Part size (L x W x Thickness)",
        "filter_type": "Filter",
        "filter_all_types": "All types",
        "material": "Material",
        "material_none": "(Please select)",
        "trim_allowance": "Trim allowance (mm)",
        "trim_allowance_tooltip": "Numeric value in mm (e.g. 0.5).",
        "grain_direction": "Grain direction",
        "grain_none": "None",
        "grain_length": "Length",
        "grain_width": "Width",
        "front_face": "Front edge (face)",
        "edges_enabled": "Define surfaces",
        "edges_section": "Surfaces",
        "mode": "Mode",
        "mode_none": "None",
        "mode_all": "All together",
        "mode_individual": "Individual",
        "edge_all": "Edge material (all)",
        "edge_none": "(No edge)",
        "custom_text": "Text",
        "custom_text_value": "Free text",
        "edge_front_enabled": "Band front",
        "edge_front": "Front edge",
        "edge_back_enabled": "Band back",
        "edge_back": "Back edge",
        "edge_left_enabled": "Band left",
        "edge_left": "Left edge",
        "edge_right_enabled": "Band right",
        "edge_right": "Right edge",
        "swap_left_right": "Swap left/right",
        "surface_all_text": "Surface (all)",
        "surface_all": "Surfaces (all)",
        "top_enabled": "Edit top side",
        "top_text": "Top surface",
        "bottom_enabled": "Edit bottom side",
        "bottom_text": "Bottom surface",
        "swap_surfaces": "Swap top/bottom",
        "exclude_from_export": "Exclude from export",
        "notes_section": "Production notes",
        "surface_none": "(No surface)",
        "notes": "Production notes",
        "apply": "Apply",
        "face_prompt": "Select planar side face",
    },
}

_ui_lang = "de"


def _detect_ui_lang():
    app = adsk.core.Application.get()
    candidates = []
    try:
        prefs = getattr(app, "preferences", None)
        gp = getattr(prefs, "generalPreferences", None) if prefs else None
        for attr in ("userLanguage", "language"):
            val = getattr(gp, attr, None)
            if val is not None:
                candidates.append(str(val))
    except Exception:
        pass

    try:
        loc = locale.getdefaultlocale()
        if loc and loc[0]:
            candidates.append(loc[0])
    except Exception:
        pass

    for candidate in candidates:
        cand = (candidate or "").lower()
        if "de" in cand:
            return "de"
        if "en" in cand:
            return "en"
    return "de"


def _set_ui_lang(lang):
    global _ui_lang
    _ui_lang = lang if lang in _STRINGS else "de"


def _t(key):
    return _STRINGS.get(_ui_lang, _STRINGS["de"]).get(key, key)


def _type_label(type_id):
    return get_type_label(type_id, _ui_lang)


def _sorted_types():
    type_ids = [
        type_id
        for type_id in get_catalog_types()
        if get_type_capabilities(type_id).get("supports_body_material", True)
    ]
    return sorted(type_ids, key=lambda type_id: _type_label(type_id).lower())
