from shared.catalog import get_type_capabilities, get_type_fields, load_catalog

try:
    from .constants import (
        TYPE_FIELD_DEFAULT_GRAIN_DIRECTION,
        TYPE_FIELD_EDGE_THICKNESS,
        TYPE_FIELD_HAS_GRAIN,
        TYPE_FIELD_TRIM_ALLOWANCE,
    )
except ImportError:
    from constants import (
        TYPE_FIELD_DEFAULT_GRAIN_DIRECTION,
        TYPE_FIELD_EDGE_THICKNESS,
        TYPE_FIELD_HAS_GRAIN,
        TYPE_FIELD_TRIM_ALLOWANCE,
    )


class _MaterialEntry:
    def __init__(
        self,
        item_id,
        item_type,
        name,
        appearance_name,
        supports_trim_allowance,
        default_trim_allowance_mm,
        supports_grain,
        sheet_has_grain,
        default_grain_direction,
        supports_body_material,
        supports_edges,
        supports_surface,
        surface_entry_mode,
        edge_entry_mode,
    ):
        self.id = item_id
        self.type = item_type
        self.name = name
        self.appearance_name = appearance_name
        self.supports_trim_allowance = supports_trim_allowance
        self.default_trim_allowance_mm = default_trim_allowance_mm
        self.supports_grain = supports_grain
        self.sheet_has_grain = sheet_has_grain
        self.default_grain_direction = default_grain_direction
        self.supports_body_material = supports_body_material
        self.supports_edges = supports_edges
        self.supports_surface = supports_surface
        self.surface_entry_mode = surface_entry_mode
        self.edge_entry_mode = edge_entry_mode


class _EdgeEntry:
    def __init__(self, item_id, name, appearance_name, thickness_mm):
        self.id = item_id
        self.name = name
        self.appearance_name = appearance_name
        self.thickness_mm = thickness_mm


class _SurfaceEntry:
    def __init__(self, item_id, name, appearance_name):
        self.id = item_id
        self.name = name
        self.appearance_name = appearance_name


def _type_supports_trim_allowance(type_id):
    for field in get_type_fields(type_id):
        if str(field.get("key", "")).strip() == TYPE_FIELD_TRIM_ALLOWANCE:
            return True
    return False


def _type_supports_grain(type_id):
    keys = {str(field.get("key", "")).strip() for field in get_type_fields(type_id)}
    return TYPE_FIELD_HAS_GRAIN in keys and TYPE_FIELD_DEFAULT_GRAIN_DIRECTION in keys


def _extract_default_trim_allowance(item, supports_trim):
    if not supports_trim:
        return 0.0
    raw = (item.properties or {}).get(TYPE_FIELD_TRIM_ALLOWANCE)
    if raw in (None, ""):
        return 0.0
    try:
        numeric = float(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Katalog-Eintrag '{item.id}' hat ungültige {TYPE_FIELD_TRIM_ALLOWANCE}: {raw}"
        ) from exc
    if numeric < 0:
        raise RuntimeError(
            f"Katalog-Eintrag '{item.id}' hat negative {TYPE_FIELD_TRIM_ALLOWANCE}: {raw}"
        )
    return numeric


def _extract_sheet_has_grain(item, supports_grain):
    if not supports_grain:
        return "none"
    raw = str((item.properties or {}).get(TYPE_FIELD_HAS_GRAIN, "none") or "none").strip().lower()
    if raw not in ("none", "yes", "no"):
        raise RuntimeError(f"Katalog-Eintrag '{item.id}' hat ungültige {TYPE_FIELD_HAS_GRAIN}: {raw}")
    return raw


def _extract_default_grain_direction(item, supports_grain):
    if not supports_grain:
        return "none"
    raw = str((item.properties or {}).get(TYPE_FIELD_DEFAULT_GRAIN_DIRECTION, "none") or "none").strip().lower()
    if raw not in ("none", "length", "width"):
        raise RuntimeError(
            f"Katalog-Eintrag '{item.id}' hat ungültige {TYPE_FIELD_DEFAULT_GRAIN_DIRECTION}: {raw}"
        )
    return raw


def _extract_edge_thickness(item):
    raw = (item.properties or {}).get(TYPE_FIELD_EDGE_THICKNESS)
    if raw in (None, ""):
        return 0.0
    try:
        numeric = float(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Katalog-Eintrag '{item.id}' hat ungültige {TYPE_FIELD_EDGE_THICKNESS}: {raw}"
        ) from exc
    if numeric < 0:
        raise RuntimeError(
            f"Katalog-Eintrag '{item.id}' hat negative {TYPE_FIELD_EDGE_THICKNESS}: {raw}"
        )
    return numeric


def load_catalog_entries(type_label):
    catalog = load_catalog()
    entries = []
    edge_entries = []
    surface_entries = []
    for item in catalog.items:
        if not item.id or not item.name:
            raise RuntimeError("Katalog enthält ungültiges Material ohne id/name.")
        if not item.appearance:
            raise RuntimeError(f"Katalog-Eintrag '{item.id}' hat keine Appearance.")
        capabilities = get_type_capabilities(item.type)
        supports_trim = _type_supports_trim_allowance(item.type)
        default_trim = _extract_default_trim_allowance(item, supports_trim)
        supports_grain = _type_supports_grain(item.type)
        sheet_has_grain = _extract_sheet_has_grain(item, supports_grain)
        default_grain_direction = _extract_default_grain_direction(item, supports_grain)
        if capabilities.get("supports_body_material", True):
            entries.append(
                _MaterialEntry(
                    item_id=item.id,
                    item_type=item.type,
                    name=item.name,
                    appearance_name=item.appearance,
                    supports_trim_allowance=supports_trim,
                    default_trim_allowance_mm=default_trim,
                    supports_grain=supports_grain,
                    sheet_has_grain=sheet_has_grain,
                    default_grain_direction=default_grain_direction,
                    supports_body_material=True,
                    supports_edges=bool(capabilities.get("supports_edges")),
                    supports_surface=bool(capabilities.get("supports_surface")),
                    surface_entry_mode=str(capabilities.get("surface_entry_mode", "none")),
                    edge_entry_mode=str(capabilities.get("edge_entry_mode", "none")),
                )
            )
        if item.type == "edge":
            edge_entries.append(
                _EdgeEntry(
                    item_id=item.id,
                    name=item.name,
                    appearance_name=item.appearance,
                    thickness_mm=_extract_edge_thickness(item),
                )
            )
        if item.type == "surface":
            surface_entries.append(
                _SurfaceEntry(
                    item_id=item.id,
                    name=item.name,
                    appearance_name=item.appearance,
                )
            )

    if not entries:
        raise RuntimeError("Katalog enthält keine Einträge.")
    if not edge_entries:
        raise RuntimeError("Katalog enthält keine Einträge vom Typ 'edge'.")

    entries.sort(key=lambda entry: (type_label(entry.type).lower(), entry.name.lower(), entry.id.lower()))
    edge_entries.sort(key=lambda entry: (entry.name.lower(), entry.id.lower()))
    surface_entries.sort(key=lambda entry: (entry.name.lower(), entry.id.lower()))
    return entries, edge_entries, surface_entries
