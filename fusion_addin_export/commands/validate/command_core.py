import adsk.fusion

from commands.export import command_core as export_core
from shared.catalog import get_type_capabilities, get_type_fields, load_catalog

_EDGE_ATTRS = (
    export_core._ATTR_KEY_EDGE_FRONT,
    export_core._ATTR_KEY_EDGE_BACK,
    export_core._ATTR_KEY_EDGE_LEFT,
    export_core._ATTR_KEY_EDGE_RIGHT,
)
_SURFACE_ATTRS = (
    export_core._ATTR_KEY_SURFACE_TOP,
    export_core._ATTR_KEY_SURFACE_BOTTOM,
)
_ATTR_LABELS = {
    export_core._ATTR_KEY_EDGE_FRONT: "Kante vorne",
    export_core._ATTR_KEY_EDGE_BACK: "Kante hinten",
    export_core._ATTR_KEY_EDGE_LEFT: "Kante links",
    export_core._ATTR_KEY_EDGE_RIGHT: "Kante rechts",
    export_core._ATTR_KEY_SURFACE_TOP: "Oberflaeche oben",
    export_core._ATTR_KEY_SURFACE_BOTTOM: "Oberflaeche unten",
    export_core._ATTR_KEY_TRIM_ALLOWANCE_MM: "Fraeszulage",
}


class _BodyAnalysisTarget:
    def __init__(self, body, component_path):
        self.body = body
        self.display_name = _build_body_display_name(body, component_path)


class _AnalysisResult:
    def __init__(self):
        self.ready_count = 0
        self.excluded_count = 0
        self.issues_by_body = []
        self.ready_bodies = []

    @property
    def issue_count(self):
        return len(self.issues_by_body)


def analyze_visible_bodies(app):
    catalog = _try_load_catalog()
    bodies = _collect_visible_bodies(app)
    return _analyze_bodies(bodies, catalog)


def _collect_visible_bodies(app):
    bodies = []
    seen_tokens = set()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        print("DIYGC Analyse: Kein aktives Fusion-Design.")
        return bodies

    root = design.rootComponent
    if root:
        root_path = [_safe_component_name(root)]
        _append_component_bodies(root, root_path, bodies, seen_tokens)
        _append_occurrence_bodies_recursive(root.occurrences, root_path, bodies, seen_tokens)
    return bodies


def _append_component_bodies(component, component_path, bodies, seen_tokens):
    try:
        for body in component.bRepBodies:
            _append_body_if_visible(body, component_path, bodies, seen_tokens)
    except Exception as exc:
        raise RuntimeError(f"DIYGC Analyse: Component-Bodies konnten nicht gelesen werden: {exc}") from exc


def _append_occurrence_bodies_recursive(occurrences, parent_path, bodies, seen_tokens):
    try:
        if not occurrences:
            return
        for occ in occurrences:
            occurrence_path = parent_path + [_safe_occurrence_name(occ)]
            for body in occ.bRepBodies:
                _append_body_if_visible(body, occurrence_path, bodies, seen_tokens)
            _append_occurrence_bodies_recursive(occ.childOccurrences, occurrence_path, bodies, seen_tokens)
    except Exception as exc:
        raise RuntimeError(f"DIYGC Analyse: Occurrence-Bodies konnten nicht gelesen werden: {exc}") from exc


def _append_body_if_visible(body, component_path, bodies, seen_tokens):
    if not body:
        return
    try:
        if not body.isVisible:
            return
        token = body.entityToken or f"id_{id(body)}"
        if token in seen_tokens:
            return
        seen_tokens.add(token)
        bodies.append(_BodyAnalysisTarget(body, component_path))
    except Exception as exc:
        body_name = export_core._safe_body_name(body)
        raise RuntimeError(f"DIYGC Analyse: Body '{body_name}' konnte nicht gelesen werden: {exc}") from exc


def _analyze_bodies(targets, catalog):
    result = _AnalysisResult()
    for target in targets:
        body = target.body
        if export_core._is_excluded_from_export(body):
            result.excluded_count += 1
            continue

        issues = _validate_export_body(body, catalog)
        if issues:
            result.issues_by_body.append((target.display_name, issues))
        else:
            result.ready_count += 1
            result.ready_bodies.append(body)
    return result


def _build_body_display_name(body, component_path):
    body_name = export_core._safe_body_name(body)
    path = [part for part in component_path if part and part != "-"]
    if not path:
        return body_name
    return " / ".join(path + [body_name])


def _safe_component_name(component):
    try:
        if component and component.name:
            return str(component.name).strip()
    except Exception:
        pass
    return "Root"


def _safe_occurrence_name(occurrence):
    try:
        if occurrence and occurrence.name:
            return str(occurrence.name).strip()
    except Exception:
        pass
    try:
        component = occurrence.component if occurrence else None
        if component and component.name:
            return str(component.name).strip()
    except Exception:
        pass
    return "Komponente"


def _validate_export_body(body, catalog):
    issues = []
    catalog_item = _resolve_body_material(body, catalog, issues)
    if not catalog_item:
        return issues

    material_type = str(catalog_item.type or "").strip()
    capabilities = get_type_capabilities(material_type)
    if not capabilities.get("supports_body_material", True):
        issues.append(
            f"Material '{catalog_item.name}' hat Typ '{material_type}' und ist nicht als Body-Material erlaubt."
        )

    _validate_type_fields(catalog_item, material_type, issues)
    _validate_trim_allowance(body, material_type, issues)
    _validate_edges(body, catalog, capabilities, issues)
    _validate_surfaces(body, catalog, capabilities, issues)
    return issues


def _resolve_body_material(body, catalog, issues):
    try:
        return export_core._resolve_catalog_material_ref(body, catalog)
    except ValueError as exc:
        issues.append(_humanize_issue_message(_strip_body_prefix(body, str(exc))))
        return None


def _validate_type_fields(catalog_item, material_type, issues):
    properties = catalog_item.properties or {}
    for field in get_type_fields(material_type):
        if not field.get("csv", False):
            continue
        key = str(field.get("key", "")).strip()
        if not key:
            continue
        if key not in properties:
            continue
        value = properties.get(key)
        kind = field.get("kind")
        if kind == "number":
            _validate_number_field(key, value, field, f"Material '{catalog_item.name}'", issues)
        elif kind == "enum":
            options = field.get("options", [])
            if str(value or "") not in options:
                issues.append(
                    f"Material '{catalog_item.name}': Feld '{key}' muss einer dieser Werte sein: {', '.join(options)}."
                )


def _validate_trim_allowance(body, material_type, issues):
    if not export_core._material_type_supports_trim_allowance(material_type):
        value = export_core._resolve_text_attribute_for_export(body, export_core._ATTR_KEY_TRIM_ALLOWANCE_MM)
        if value:
            issues.append("Fräszulage ist gesetzt, obwohl der Materialtyp sie nicht unterstuetzt.")
        return

    raw = export_core._resolve_text_attribute_for_export(body, export_core._ATTR_KEY_TRIM_ALLOWANCE_MM)
    if not raw:
        issues.append("Fräszulage fehlt.")
        return

    field = _type_field_by_key(material_type, "sheet_default_trim_allowance")
    if field:
        _validate_number_field("trim_allowance_mm", raw, field, "Body", issues)
        return
    try:
        float(str(raw).replace(",", "."))
    except Exception:
        issues.append(f"Fräszulage ist nicht numerisch: '{raw}'.")


def _validate_edges(body, catalog, capabilities, issues):
    supports_edges = bool(capabilities.get("supports_edges", False))
    for attr_key in _EDGE_ATTRS:
        edge_id = export_core._resolve_text_attribute_for_export(body, attr_key)
        custom_text = export_core._resolve_text_attribute_for_export(
            body, export_core._custom_text_attr_for_attr(attr_key)
        )
        _validate_custom_text_pair("Kante", attr_key, edge_id, custom_text, issues)
        if not edge_id:
            continue
        if not supports_edges:
            issues.append(f"{_attr_label(attr_key)} ist gesetzt, obwohl der Materialtyp keine Kanten unterstuetzt.")
            continue
        try:
            export_core._resolve_edge_export_for_side(body, catalog, attr_key)
        except ValueError as exc:
            message = _humanize_issue_message(_strip_body_prefix(body, str(exc)))
            issues.append(f"{_attr_label(attr_key)}: {message}")


def _validate_surfaces(body, catalog, capabilities, issues):
    supports_surface = bool(capabilities.get("supports_surface", False))
    for attr_key in _SURFACE_ATTRS:
        surface_id = export_core._resolve_text_attribute_for_export(body, attr_key)
        custom_text = export_core._resolve_text_attribute_for_export(
            body, export_core._custom_text_attr_for_attr(attr_key)
        )
        _validate_custom_text_pair("Oberflaeche", attr_key, surface_id, custom_text, issues)
        if not surface_id:
            continue
        if not supports_surface:
            issues.append(
                f"{_attr_label(attr_key)} ist gesetzt, obwohl der Materialtyp keine Oberflaechen unterstuetzt."
            )
            continue
        try:
            export_core._resolve_surface_export_for_side(body, catalog, attr_key)
        except ValueError as exc:
            message = _humanize_issue_message(_strip_body_prefix(body, str(exc)))
            issues.append(f"{_attr_label(attr_key)}: {message}")


def _validate_custom_text_pair(label, attr_key, selected_value, custom_text, issues):
    if selected_value == export_core._CUSTOM_TEXT_VALUE:
        return
    if custom_text:
        issues.append(
            f"{_attr_label(attr_key)} hat Freitext, aber die Auswahl steht nicht auf Freitext."
        )


def _validate_number_field(key, value, field, owner_label, issues):
    text = "" if value is None else str(value).strip()
    if not text:
        issues.append(f"{owner_label}: Feld '{key}' fehlt.")
        return
    try:
        numeric = float(text.replace(",", "."))
    except Exception:
        issues.append(f"{owner_label}: Feld '{key}' ist nicht numerisch: '{text}'.")
        return

    min_value = float(field.get("min", 0.0))
    max_value = float(field.get("max", min_value))
    if numeric < min_value or numeric > max_value:
        issues.append(f"{owner_label}: Feld '{key}' muss zwischen {min_value:g} und {max_value:g} liegen.")


def _type_field_by_key(material_type, key):
    for field in get_type_fields(material_type):
        if str(field.get("key", "")).strip() == key:
            return field
    return None


def _strip_body_prefix(body, message):
    body_name = export_core._safe_body_name(body)
    prefix = f"Body '{body_name}' "
    if message.startswith(prefix):
        return message[len(prefix):]
    return message


def _humanize_issue_message(message):
    text = str(message or "")
    for key, label in _ATTR_LABELS.items():
        text = text.replace(f"'{key}'", label)
        text = text.replace(key, label)
    text = text.replace("'material_id'", "Material")
    text = text.replace("material_id", "Material")
    return text


def _attr_label(attr_key):
    return _ATTR_LABELS.get(attr_key, attr_key)


def _format_result_message(result):
    lines = [
        "DIYGC Analyse",
        "",
        f"Exportbereit: {result.ready_count}",
        f"Ausgeschlossen: {result.excluded_count}",
        f"Mit fehlenden/inkonsistenten Angaben: {result.issue_count}",
    ]
    if result.issues_by_body:
        lines.extend(["", "Details:"])
        for body_name, issues in result.issues_by_body:
            lines.append(f"- {body_name}:")
            for issue in issues:
                lines.append(f"  - {issue}")
    return "\n".join(lines)


def _try_load_catalog():
    try:
        return load_catalog()
    except Exception as exc:
        raise RuntimeError(f"Catalog konnte nicht geladen werden: {exc}") from exc


def start():
    return


def stop():
    return
