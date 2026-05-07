import adsk.core
import adsk.fusion
import csv
import re

import export_config as config

_handlers = []
_active_panel_id = None
_is_started = False
_command_created_handler = None


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
            print("CSV-Export: App/UI nicht verfuegbar.")
            return

        try:
            _run_export_mode(app, ui)
        except Exception as exc:
            print(f"Export-Command-Fehler: {exc}")
            ui.messageBox(f"CSV-Export fehlgeschlagen:\n{exc}")


def _run_export_mode(app, ui):
    export_path = _pick_export_path(app, ui)
    if not export_path:
        ui.messageBox("CSV-Export abgebrochen. Es wurde keine Datei geschrieben.")
        print("CSV-Export: Vom Nutzer abgebrochen.")
        return

    rows = _collect_visible_body_rows(app)
    if not rows:
        ui.messageBox("Keine sichtbaren Bodies gefunden. Es wurde keine CSV erzeugt.")
        print("CSV-Export: Keine sichtbaren Bodies gefunden.")
        return

    _write_csv(export_path, rows)
    ui.messageBox(f"CSV-Export abgeschlossen.\nDatei: {export_path}\nBodies: {len(rows)}")
    print(f"CSV-Export abgeschlossen: {export_path} ({len(rows)} Bodies)")


def _pick_export_path(app, ui):
    try:
        dialog = ui.createFileDialog()
        dialog.isMultiSelectEnabled = False
        dialog.title = "CSV speichern"
        dialog.filter = "CSV-Dateien (*.csv);;Alle Dateien (*.*)"
        dialog.filterIndex = 0
        dialog.initialFilename = _build_default_export_filename(app)
        result = dialog.showSave()
        filename = dialog.filename if getattr(dialog, "filename", None) else ""
        if result == adsk.core.DialogResults.DialogOK and filename:
            return filename
        return None
    except Exception as exc:
        print(f"CSV-Export: Dateidialog fehlgeschlagen: {exc}")
        return None


def _build_default_export_filename(app):
    base_name = "fusion_bodies_export"
    try:
        document = app.activeDocument if app else None
        name = document.name if document else ""
        if name:
            if name.lower().endswith(".f3d"):
                name = name[:-4]
            cleaned = re.sub(r'[<>:"/\\|?*]', "_", name).strip()
            if cleaned:
                base_name = cleaned
    except Exception as exc:
        print(f"CSV-Export: Konnte Dokumentnamen nicht lesen: {exc}")
    return f"{base_name}.csv"


def _collect_visible_body_rows(app):
    rows = []
    seen_tokens = set()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        print("CSV-Export: Kein aktives Fusion-Design.")
        return rows

    root = design.rootComponent
    if root:
        _append_component_bodies(root, rows, seen_tokens)
        _append_occurrence_bodies_recursive(root.occurrences, rows, seen_tokens)
    return rows


def _append_component_bodies(component, rows, seen_tokens):
    try:
        for body in component.bRepBodies:
            _append_body_row_if_visible(body, rows, seen_tokens)
    except Exception as exc:
        print(f"CSV-Export: Component-Bodies konnten nicht gelesen werden: {exc}")


def _append_occurrence_bodies_recursive(occurrences, rows, seen_tokens):
    try:
        if not occurrences:
            return
        for occ in occurrences:
            try:
                for body in occ.bRepBodies:
                    _append_body_row_if_visible(body, rows, seen_tokens)
                _append_occurrence_bodies_recursive(occ.childOccurrences, rows, seen_tokens)
            except Exception as exc:
                print(f"CSV-Export: Occurrence konnte nicht gelesen werden: {exc}")
    except Exception as exc:
        print(f"CSV-Export: Occurrence-Liste konnte nicht gelesen werden: {exc}")


def _append_body_row_if_visible(body, rows, seen_tokens):
    if not body:
        return
    try:
        if not body.isVisible:
            return
        token = body.entityToken or f"id_{id(body)}"
        if token in seen_tokens:
            return
        seen_tokens.add(token)
        rows.append(_body_to_csv_row(body))
    except Exception as exc:
        print(f"CSV-Export: Body uebersprungen: {exc}")


def _body_to_csv_row(body):
    name = _safe_body_name(body)
    width, height, depth = _get_dimensions_from_bounding_box(body)
    material_name = _safe_name(getattr(body, "material", None))
    appearance_name = _safe_name(getattr(body, "appearance", None))
    attr_text = _collect_attributes_as_text(body)
    return [name, width, height, depth, material_name, appearance_name, attr_text]


def _safe_body_name(body):
    try:
        if body.name:
            return body.name
    except Exception:
        pass
    return "-"


def _get_dimensions_from_bounding_box(body):
    try:
        bbox = body.boundingBox
        min_p = bbox.minPoint
        max_p = bbox.maxPoint
        width = abs(max_p.x - min_p.x)
        height = abs(max_p.y - min_p.y)
        depth = abs(max_p.z - min_p.z)
        return _fmt_num(width), _fmt_num(height), _fmt_num(depth)
    except Exception as exc:
        print(f"CSV-Export: BoundingBox-Fehler bei Body: {exc}")
        return "-", "-", "-"


def _fmt_num(value):
    try:
        return f"{float(value):.6f}"
    except Exception:
        return "-"


def _safe_name(obj):
    try:
        if obj and obj.name:
            return obj.name
    except Exception:
        pass
    return "-"


def _collect_attributes_as_text(body):
    entries = []
    try:
        attributes = getattr(body, "attributes", None)
        if not attributes or attributes.count < 1:
            return "-"
        for i in range(attributes.count):
            attr = attributes.item(i)
            if not attr:
                continue
            group = attr.groupName if attr.groupName else "-"
            name = attr.name if attr.name else "-"
            value = attr.value if attr.value is not None else "-"
            entries.append(f"{group}:{name}={value}")
    except Exception as exc:
        print(f"CSV-Export: Attribute konnten nicht gelesen werden: {exc}")
        return "-"
    return ";".join(entries) if entries else "-"


def _write_csv(path, rows):
    header = ["body_name", "width", "height", "depth", "material", "appearance", "attributes"]
    with open(path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)
        writer.writerows(rows)


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

    cmd_def = ui.commandDefinitions.itemById(config.COMMAND_ID)
    if not cmd_def:
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            config.COMMAND_ID,
            config.COMMAND_NAME,
            config.COMMAND_TOOLTIP,
            config.COMMAND_RESOURCES,
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

    control = panel.controls.itemById(config.COMMAND_ID)
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
    cmd_def = ui.commandDefinitions.itemById(config.COMMAND_ID)

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
            control = panel.controls.itemById(config.COMMAND_ID)
            if control:
                control.deleteMe()

    if cmd_def:
        cmd_def.deleteMe()

    _handlers.clear()
    _active_panel_id = None
    _is_started = False
