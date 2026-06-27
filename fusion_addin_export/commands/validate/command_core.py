import adsk.core
import adsk.fusion

import export_config as config
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

_handlers = []
_active_panel_id = None
_is_started = False
_command_created_handler = None


class _AnalysisResult:
    def __init__(self):
        self.ready_count = 0
        self.excluded_count = 0
        self.issues_by_body = []

    @property
    def issue_count(self):
        return len(self.issues_by_body)


class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        event_args = adsk.core.CommandCreatedEventArgs.cast(args)
        cmd = event_args.command
        on_execute = _CommandExecuteHandler()
        cmd.execute.add(on_execute)
        _handlers.append(on_execute)


class _CommandExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        app = adsk.core.Application.get()
        ui = app.userInterface if app else None
        if not app or not ui:
            print("DIYGC Analyse: App/UI nicht verfuegbar.")
            return

        try:
            _run_analysis(app, ui)
        except Exception as exc:
            print(f"DIYGC Analyse fehlgeschlagen: {exc}")
            ui.messageBox(f"DIYGC Analyse fehlgeschlagen:\n{exc}")


def _run_analysis(app, ui):
    catalog = _try_load_catalog()
    bodies = _collect_visible_bodies(app)
    if not bodies:
        ui.messageBox("DIYGC Analyse\n\nKeine sichtbaren Bodies gefunden.")
        return

    result = _analyze_bodies(bodies, catalog)
    ui.messageBox(_format_result_message(result))


def _collect_visible_bodies(app):
    bodies = []
    seen_tokens = set()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        print("DIYGC Analyse: Kein aktives Fusion-Design.")
        return bodies

    root = design.rootComponent
    if root:
        _append_component_bodies(root, bodies, seen_tokens)
        _append_occurrence_bodies_recursive(root.occurrences, bodies, seen_tokens)
    return bodies


def _append_component_bodies(component, bodies, seen_tokens):
    try:
        for body in component.bRepBodies:
            _append_body_if_visible(body, bodies, seen_tokens)
    except Exception as exc:
        raise RuntimeError(f"DIYGC Analyse: Component-Bodies konnten nicht gelesen werden: {exc}") from exc


def _append_occurrence_bodies_recursive(occurrences, bodies, seen_tokens):
    try:
        if not occurrences:
            return
        for occ in occurrences:
            for body in occ.bRepBodies:
                _append_body_if_visible(body, bodies, seen_tokens)
            _append_occurrence_bodies_recursive(occ.childOccurrences, bodies, seen_tokens)
    except Exception as exc:
        raise RuntimeError(f"DIYGC Analyse: Occurrence-Bodies konnten nicht gelesen werden: {exc}") from exc


def _append_body_if_visible(body, bodies, seen_tokens):
    if not body:
        return
    try:
        if not body.isVisible:
            return
        token = body.entityToken or f"id_{id(body)}"
        if token in seen_tokens:
            return
        seen_tokens.add(token)
        bodies.append(body)
    except Exception as exc:
        body_name = export_core._safe_body_name(body)
        raise RuntimeError(f"DIYGC Analyse: Body '{body_name}' konnte nicht gelesen werden: {exc}") from exc


def _analyze_bodies(bodies, catalog):
    result = _AnalysisResult()
    for body in bodies:
        if export_core._is_excluded_from_export(body):
            result.excluded_count += 1
            continue

        issues = _validate_export_body(body, catalog)
        if issues:
            result.issues_by_body.append((export_core._safe_body_name(body), issues))
        else:
            result.ready_count += 1
    return result


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
        issues.append(_strip_body_prefix(body, str(exc)))
        return None


def _validate_type_fields(catalog_item, material_type, issues):
    properties = catalog_item.properties or {}
    for field in get_type_fields(material_type):
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
            issues.append(f"Kante '{attr_key}' ist gesetzt, obwohl der Materialtyp keine Kanten unterstuetzt.")
            continue
        try:
            export_core._resolve_edge_export_for_side(body, catalog, attr_key)
        except ValueError as exc:
            issues.append(_strip_body_prefix(body, str(exc)))


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
                f"Oberflaeche '{attr_key}' ist gesetzt, obwohl der Materialtyp keine Oberflaechen unterstuetzt."
            )
            continue
        try:
            export_core._resolve_surface_export_for_side(body, catalog, attr_key)
        except ValueError as exc:
            issues.append(_strip_body_prefix(body, str(exc)))


def _validate_custom_text_pair(label, attr_key, selected_value, custom_text, issues):
    if selected_value == export_core._CUSTOM_TEXT_VALUE:
        return
    if custom_text:
        issues.append(
            f"{label} '{attr_key}' hat Freitext, aber die Auswahl steht nicht auf Freitext."
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


def _get_or_create_panel(workspace):
    global _active_panel_id

    primary = workspace.toolbarPanels.itemById(config.PRIMARY_PANEL_ID)
    if primary:
        _active_panel_id = config.PRIMARY_PANEL_ID
        return primary

    for panel_id in config.PANEL_IDS:
        candidate = workspace.toolbarPanels.itemById(panel_id)
        if candidate:
            _active_panel_id = panel_id
            return candidate

    tab = workspace.toolbarTabs.itemById(config.CUSTOM_TAB_ID)
    if not tab:
        return None

    panel = tab.toolbarPanels.itemById(config.CUSTOM_PANEL_ID)
    if panel:
        _active_panel_id = config.CUSTOM_PANEL_ID
        return panel

    panel = tab.toolbarPanels.add(config.CUSTOM_PANEL_ID, config.CUSTOM_PANEL_NAME, "", False)
    _active_panel_id = config.CUSTOM_PANEL_ID
    return panel


def start():
    global _active_panel_id, _is_started, _command_created_handler
    if _is_started:
        return

    app = adsk.core.Application.get()
    ui = app.userInterface

    cmd_def = ui.commandDefinitions.itemById(config.VALIDATE_COMMAND_ID)
    if not cmd_def:
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            config.VALIDATE_COMMAND_ID,
            config.VALIDATE_COMMAND_NAME,
            config.VALIDATE_COMMAND_TOOLTIP,
            config.VALIDATE_COMMAND_RESOURCES,
        )

    _command_created_handler = _CommandCreatedHandler()
    cmd_def.commandCreated.add(_command_created_handler)
    _handlers.append(_command_created_handler)
    _is_started = True

    workspace = ui.workspaces.itemById(config.WORKSPACE_ID)
    if not workspace:
        return

    panel = _get_or_create_panel(workspace)
    if not panel:
        return

    control = panel.controls.itemById(config.VALIDATE_COMMAND_ID)
    if not control:
        control = panel.controls.addCommand(cmd_def)

    if control:
        try:
            control.isPromotedByDefault = True
            control.isPromoted = True
        except Exception:
            pass


def stop():
    global _active_panel_id, _is_started, _command_created_handler
    app = adsk.core.Application.get()
    ui = app.userInterface
    cmd_def = ui.commandDefinitions.itemById(config.VALIDATE_COMMAND_ID)

    if cmd_def and _command_created_handler:
        try:
            cmd_def.commandCreated.remove(_command_created_handler)
        except Exception:
            pass
        _command_created_handler = None

    workspace = ui.workspaces.itemById(config.WORKSPACE_ID)
    if workspace:
        panel = workspace.toolbarPanels.itemById(_active_panel_id) if _active_panel_id else None
        if panel:
            control = panel.controls.itemById(config.VALIDATE_COMMAND_ID)
            if control:
                control.deleteMe()

    if cmd_def:
        cmd_def.deleteMe()

    _handlers.clear()
    _active_panel_id = None
    _is_started = False
