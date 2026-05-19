import adsk.core
import adsk.fusion

from shared.catalog import load_catalog

WORKSPACE_ID = "FusionSolidEnvironment"
PRIMARY_PANEL_ID = "SolidModifyPanel"
PANEL_IDS = [
    "SolidModifyPanel",
    "SolidToolsPanel",
    "SolidCreatePanel",
    "SolidScriptsAddinsPanel",
]
CUSTOM_TAB_ID = "SolidTab"
CUSTOM_PANEL_ID = "DIYGarageCut_DIYGarageCutPropertiesAddin_Panel"
CUSTOM_PANEL_NAME = "DIY Garage Cut"
COMMAND_ID = "DIYGarageCut_DIYGarageCutPropertiesAddin_PropertiesCommand"
COMMAND_NAME = "DIYGC Eigenschaften"
COMMAND_TOOLTIP = "Material und Fräszulage fuer einen Body setzen."
COMMAND_RESOURCES = "./Resources"

ATTRIBUTE_GROUP = "DIYGarageCut.part_metadata"
ATTR_KEY_MATERIAL_ID = "material_id"
ATTR_KEY_TRIM_ALLOWANCE_MM = "trim_allowance_mm"

_INPUT_BODY = "diygc_body_selection"
_INPUT_SIZE = "diygc_size"
_INPUT_MATERIAL = "diygc_material"
_INPUT_TRIM_ALLOWANCE = "diygc_trim_allowance_mm"
_MATERIAL_NONE_LABEL = "(Bitte waehlen)"

_handlers = []
_active_panel_id = None
_is_started = False
_command_created_handler = None
_material_entries = []
_material_by_id = {}
_material_label_to_id = {}
_material_id_to_label = {}


class _MaterialEntry:
    def __init__(self, item_id, item_type, name, appearance_name, default_trim_allowance_mm):
        self.id = item_id
        self.type = item_type
        self.name = name
        self.appearance_name = appearance_name
        self.default_trim_allowance_mm = default_trim_allowance_mm


class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        event_args = adsk.core.CommandCreatedEventArgs.cast(args)
        cmd = event_args.command
        inputs = cmd.commandInputs

        _load_material_entries()

        sel = inputs.addSelectionInput(_INPUT_BODY, "Koerper", "Einen Koerper auswaehlen")
        sel.addSelectionFilter("Bodies")
        sel.setSelectionLimits(1, 1)

        size_box = inputs.addTextBoxCommandInput(_INPUT_SIZE, "Bauteilgroesse (L x B x Dicke)", "-", 1, True)
        size_box.isFullWidth = False

        material_pick = inputs.addDropDownCommandInput(
            _INPUT_MATERIAL,
            "Material",
            adsk.core.DropDownStyles.TextListDropDownStyle
        )
        material_pick.listItems.add(_MATERIAL_NONE_LABEL, True)
        for entry in _material_entries:
            label = _format_material_label(entry)
            material_pick.listItems.add(label, False)

        trim_input = inputs.addStringValueInput(_INPUT_TRIM_ALLOWANCE, "Fräszulage (mm)", "0.0")
        trim_input.tooltip = "Numerischer Wert in mm (z. B. 0.5)."

        on_input_changed = _InputChangedHandler()
        cmd.inputChanged.add(on_input_changed)
        _handlers.append(on_input_changed)

        on_execute = _ExecuteHandler()
        cmd.execute.add(on_execute)
        _handlers.append(on_execute)


class _InputChangedHandler(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        try:
            event_args = adsk.core.InputChangedEventArgs.cast(args)
            changed = event_args.input
            if not changed:
                return
            command = event_args.firingEvent.sender
            inputs = command.commandInputs if command else None
            if not inputs:
                return

            if changed.id == _INPUT_BODY:
                _refresh_inputs_from_selected_body(inputs)
                return

            if changed.id == _INPUT_MATERIAL:
                selected_id = _read_material_dropdown_value(inputs)
                if not selected_id:
                    _set_input_value(inputs, _INPUT_TRIM_ALLOWANCE, "")
                    return
                default_trim = _material_default_trim_allowance(selected_id)
                _set_input_value(inputs, _INPUT_TRIM_ALLOWANCE, _format_trim_allowance(default_trim))
        except Exception as exc:
            print(f"Properties: InputChanged-Fehler: {exc}")


class _ExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        app = adsk.core.Application.get()
        ui = app.userInterface if app else None
        if not app or not ui:
            print("Properties: App/UI nicht verfuegbar.")
            return
        try:
            event_args = adsk.core.CommandEventArgs.cast(args)
            command = event_args.command if event_args else None
            inputs = command.commandInputs if command else None
            if not inputs:
                ui.messageBox("Properties-Fehler: Keine Command-Inputs verfuegbar.")
                return

            body = _read_selected_body(inputs)
            if not body:
                ui.messageBox("Bitte im Dialog einen Koerper auswaehlen.")
                return

            material_id = _read_material_dropdown_value(inputs)
            if not material_id:
                ui.messageBox("Bitte ein Material auswaehlen.")
                return

            trim_input = _read_string_input(inputs, _INPUT_TRIM_ALLOWANCE, "")
            trim_allowance_mm = _parse_trim_allowance(trim_input)
            old_material_id = str(_get_attr(body, ATTR_KEY_MATERIAL_ID, "") or "").strip()

            _write_body_attribute_or_raise(body, ATTR_KEY_MATERIAL_ID, material_id)
            _write_body_attribute_or_raise(body, ATTR_KEY_TRIM_ALLOWANCE_MM, _format_trim_allowance(trim_allowance_mm))

            if material_id != old_material_id:
                _apply_material_appearance_or_raise(body, material_id)

            if _is_body_likely_read_only(body):
                diag = _diagnose_attribute_context(body)
                ui.messageBox(
                    "Eigenschaften gespeichert, aber Body wirkt schreibgeschuetzt.\n"
                    "Bitte Ergebnis pruefen.\n\nDiagnose:\n"
                    f"{diag}"
                )
                return

            print(f"Properties gespeichert fuer Body: {body.name}")
        except Exception as exc:
            print(f"Properties: Execute-Fehler: {exc}")
            ui.messageBox(f"Eigenschaften fehlgeschlagen:\n{exc}")


def _resolve_attr_target(entity):
    if not entity:
        return None
    try:
        native = getattr(entity, "nativeObject", None)
        if native:
            return native
    except Exception:
        pass
    return entity


def _load_material_entries():
    global _material_entries, _material_by_id, _material_label_to_id, _material_id_to_label
    catalog = load_catalog()
    entries = []
    for item in catalog.items:
        if not item.id or not item.name:
            raise RuntimeError("Catalog enthaelt ungueltiges Material ohne id/name.")
        if not item.appearance:
            raise RuntimeError(f"Catalog-Eintrag '{item.id}' hat keine Appearance.")
        default_trim = _extract_default_trim_allowance(item)
        entry = _MaterialEntry(
            item_id=item.id,
            item_type=item.type,
            name=item.name,
            appearance_name=item.appearance,
            default_trim_allowance_mm=default_trim,
        )
        entries.append(entry)

    if not entries:
        raise RuntimeError("Catalog enthaelt keine Eintraege.")

    entries.sort(key=lambda entry: (entry.type, entry.name, entry.id))
    _material_entries = entries
    _material_by_id = {entry.id: entry for entry in entries}
    _material_label_to_id = {}
    _material_id_to_label = {}
    for entry in entries:
        label = _format_material_label(entry)
        _material_label_to_id[label] = entry.id
        _material_id_to_label[entry.id] = label


def _extract_default_trim_allowance(item):
    raw = (item.properties or {}).get("sheet_default_trim_allowance")
    if raw in (None, ""):
        return 0.0
    try:
        numeric = float(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Catalog-Eintrag '{item.id}' hat ungueltige sheet_default_trim_allowance: {raw}"
        ) from exc
    if numeric < 0:
        raise RuntimeError(
            f"Catalog-Eintrag '{item.id}' hat negative sheet_default_trim_allowance: {raw}"
        )
    return numeric


def _format_material_label(entry):
    return f"{entry.name} [{entry.id}]"


def _refresh_inputs_from_selected_body(inputs):
    body = _read_selected_body(inputs)
    if not body:
        _set_input_value(inputs, _INPUT_SIZE, "-")
        _set_dropdown_value(inputs, _INPUT_MATERIAL, "")
        _set_input_value(inputs, _INPUT_TRIM_ALLOWANCE, "")
        return

    _set_input_value(inputs, _INPUT_SIZE, _format_body_size(body))
    material_id = str(_get_attr(body, ATTR_KEY_MATERIAL_ID, "") or "").strip()
    trim_allowance = str(_get_attr(body, ATTR_KEY_TRIM_ALLOWANCE_MM, "") or "").strip()

    _set_dropdown_value(inputs, _INPUT_MATERIAL, material_id)
    if trim_allowance:
        _set_input_value(inputs, _INPUT_TRIM_ALLOWANCE, trim_allowance)
        return
    if material_id:
        _set_input_value(
            inputs,
            _INPUT_TRIM_ALLOWANCE,
            _format_trim_allowance(_material_default_trim_allowance(material_id)),
        )
        return
    _set_input_value(inputs, _INPUT_TRIM_ALLOWANCE, "")


def _write_body_attribute_or_raise(body, key, value):
    ok, reason = _set_attr(body, key, value)
    if ok:
        return
    hint = ""
    if _is_body_likely_read_only(body):
        hint = " Body wirkt schreibgeschuetzt."
    raise RuntimeError(f"Attribut '{key}' konnte nicht gespeichert werden ({reason}).{hint}")


def _set_attr(entity, key, value):
    if not entity or not key:
        return False, "ungueltige Eingabe"

    targets = []
    try:
        native = getattr(entity, "nativeObject", None)
        if native:
            targets.append(native)
    except Exception:
        pass
    targets.append(entity)

    last_error = "kein Zielobjekt"
    seen = set()
    for target in targets:
        if not target:
            continue
        marker = id(target)
        if marker in seen:
            continue
        seen.add(marker)
        try:
            attrs = getattr(target, "attributes", None)
            if attrs is None:
                last_error = "keine Attributes-Sammlung"
                continue
            attrs.add(ATTRIBUTE_GROUP, key, str(value))
            return True, ""
        except Exception as exc:
            last_error = str(exc)
            print(f"Properties: set_attr fehlgeschlagen ({key}) auf Target: {exc}")

    token = _get_entity_token(entity)
    if token:
        ok, reason = _set_design_level_attr(token, key, value)
        if ok:
            return True, ""
        last_error = reason

    return False, last_error


def _get_attr(entity, key, default=None):
    if not entity or not key:
        return default
    try:
        target = _resolve_attr_target(entity)
        attrs = getattr(target, "attributes", None)
        if attrs is None:
            token = _get_entity_token(entity)
            if token:
                return _get_design_level_attr(token, key, default)
            return default
        attr = attrs.itemByName(ATTRIBUTE_GROUP, key)
        if attr:
            return attr.value
        token = _get_entity_token(entity)
        if token:
            return _get_design_level_attr(token, key, default)
        return default
    except Exception:
        token = _get_entity_token(entity)
        if token:
            return _get_design_level_attr(token, key, default)
        return default


def _read_material_dropdown_value(inputs):
    label = _read_dropdown_value(inputs, _INPUT_MATERIAL, "")
    if not label or label == _MATERIAL_NONE_LABEL:
        return ""
    material_id = _material_label_to_id.get(label, "")
    if not material_id:
        raise RuntimeError(f"Unbekannter Material-Dropdown-Wert: '{label}'")
    return material_id


def _material_default_trim_allowance(material_id):
    entry = _material_by_id.get(material_id)
    if not entry:
        raise RuntimeError(f"Material '{material_id}' ist nicht im Catalog vorhanden.")
    return float(entry.default_trim_allowance_mm)


def _parse_trim_allowance(raw_value):
    text = str(raw_value or "").strip().replace(",", ".")
    if not text:
        raise RuntimeError("Fräszulage fehlt.")
    try:
        numeric = float(text)
    except ValueError as exc:
        raise RuntimeError(f"Fräszulage ist keine Zahl: '{raw_value}'") from exc
    if numeric < 0:
        raise RuntimeError("Fräszulage muss >= 0 sein.")
    return numeric


def _format_trim_allowance(value):
    numeric = float(value)
    if abs(numeric - round(numeric)) < 1e-9:
        return str(int(round(numeric)))
    text = f"{numeric:.3f}".rstrip("0").rstrip(".")
    return text


def _find_appearance_by_name(name):
    app = adsk.core.Application.get()
    if not app:
        raise RuntimeError("Fusion Application nicht verfuegbar.")

    wanted = str(name or "").strip().lower()
    if not wanted:
        return None

    def _scan(appearances):
        if not appearances:
            return None
        for idx in range(appearances.count):
            candidate = appearances.item(idx)
            candidate_name = str(getattr(candidate, "name", "") or "").strip().lower()
            if candidate_name == wanted:
                return candidate
        return None

    design = adsk.fusion.Design.cast(app.activeProduct) if app else None
    found = _scan(getattr(design, "appearances", None) if design else None)
    if found:
        return found

    libraries = getattr(app, "materialLibraries", None)
    if not libraries:
        return None
    for li in range(libraries.count):
        library = libraries.item(li)
        found = _scan(getattr(library, "appearances", None))
        if found:
            return found
    return None


def _apply_material_appearance_or_raise(body, material_id):
    entry = _material_by_id.get(material_id)
    if not entry:
        raise RuntimeError(f"Material '{material_id}' ist nicht im Catalog vorhanden.")

    appearance = _find_appearance_by_name(entry.appearance_name)
    if not appearance:
        raise RuntimeError(
            f"Appearance '{entry.appearance_name}' aus Material '{material_id}' wurde in Fusion nicht gefunden."
        )

    target = _resolve_attr_target(body)
    if not target:
        raise RuntimeError("Body fuer Appearance-Zuweisung nicht verfuegbar.")
    try:
        target.appearance = appearance
    except Exception as exc:
        raise RuntimeError(f"Appearance konnte nicht gesetzt werden: {exc}") from exc


def _read_selected_body(inputs):
    try:
        sel = adsk.core.SelectionCommandInput.cast(inputs.itemById(_INPUT_BODY))
        if not sel or sel.selectionCount < 1:
            return None
        entity = sel.selection(0).entity
        body = adsk.fusion.BRepBody.cast(entity)
        if not body:
            return None

        native = adsk.fusion.BRepBody.cast(getattr(body, "nativeObject", None))
        if native:
            return native
        return body
    except Exception as exc:
        print(f"Properties: Koerperauswahl konnte nicht gelesen werden: {exc}")
    return None


def _is_body_likely_read_only(body):
    try:
        if getattr(body, "isReadOnly", False):
            return True
    except Exception:
        pass
    try:
        if getattr(body, "assemblyContext", None):
            native = getattr(body, "nativeObject", None)
            if native is None:
                return True
    except Exception:
        pass
    return False


def _get_entity_token(entity):
    try:
        token = getattr(entity, "entityToken", None)
        if token:
            return str(token)
    except Exception:
        pass
    return None


def _get_design_attrs_collection():
    try:
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct) if app else None
        if not design:
            return None
        root = getattr(design, "rootComponent", None)
        if root:
            attrs = getattr(root, "attributes", None)
            if attrs is not None:
                return attrs
        return getattr(design, "attributes", None)
    except Exception:
        return None


def _build_design_attr_name(token, key):
    return f"body_token::{token}::{key}"


def _set_design_level_attr(token, key, value):
    attrs = _get_design_attrs_collection()
    if attrs is None:
        return False, "keine Design-Attributes"
    try:
        attrs.add(ATTRIBUTE_GROUP, _build_design_attr_name(token, key), str(value))
        return True, ""
    except Exception as exc:
        print(f"Properties: Design-Attr set fehlgeschlagen ({key}): {exc}")
        return False, str(exc)


def _get_design_level_attr(token, key, default=None):
    attrs = _get_design_attrs_collection()
    if not attrs:
        return default
    try:
        attr = attrs.itemByName(ATTRIBUTE_GROUP, _build_design_attr_name(token, key))
        return attr.value if attr else default
    except Exception:
        return default


def _diagnose_attribute_context(body):
    parts = []
    try:
        body_type = body.objectType if body else "-"
        parts.append(f"BodyType={body_type}")
    except Exception:
        parts.append("BodyType=<Fehler>")

    try:
        body_attrs = getattr(body, "attributes", None)
        parts.append(f"BodyAttrs={'ja' if body_attrs is not None else 'nein'}")
    except Exception:
        parts.append("BodyAttrs=<Fehler>")

    try:
        native = getattr(body, "nativeObject", None) if body else None
        native_type = native.objectType if native else "-"
        parts.append(f"NativeType={native_type}")
        native_attrs = getattr(native, "attributes", None) if native else None
        parts.append(f"NativeAttrs={'ja' if native_attrs is not None else 'nein'}")
    except Exception:
        parts.append("NativeAttrs=<Fehler>")

    try:
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct) if app else None
        root = getattr(design, "rootComponent", None) if design else None
        root_attrs = getattr(root, "attributes", None) if root else None
        parts.append(f"RootAttrs={'ja' if root_attrs is not None else 'nein'}")
    except Exception:
        parts.append("RootAttrs=<Fehler>")

    return ", ".join(parts)


def _read_string_input(inputs, input_id, fallback):
    try:
        string_item = adsk.core.StringValueCommandInput.cast(inputs.itemById(input_id))
        if string_item:
            value = (string_item.value or "").strip()
            return value if value else fallback

        text_item = adsk.core.TextBoxCommandInput.cast(inputs.itemById(input_id))
        if not text_item:
            return fallback
        value = (text_item.text or "").strip()
        return value if value else fallback
    except Exception:
        return fallback


def _set_input_value(inputs, input_id, value):
    try:
        string_item = adsk.core.StringValueCommandInput.cast(inputs.itemById(input_id))
        if string_item:
            string_item.value = str(value if value is not None else "")
            return
        text_item = adsk.core.TextBoxCommandInput.cast(inputs.itemById(input_id))
        if text_item:
            text_item.text = str(value if value is not None else "")
    except Exception as exc:
        print(f"Properties: Input '{input_id}' konnte nicht gesetzt werden: {exc}")


def _read_dropdown_value(inputs, input_id, fallback):
    try:
        dd = adsk.core.DropDownCommandInput.cast(inputs.itemById(input_id))
        if not dd or not dd.selectedItem:
            return fallback
        value = (dd.selectedItem.name or "").strip()
        return value if value else fallback
    except Exception:
        return fallback


def _set_dropdown_value(inputs, input_id, value):
    try:
        dd = adsk.core.DropDownCommandInput.cast(inputs.itemById(input_id))
        if not dd:
            return
        fallback_label = _MATERIAL_NONE_LABEL
        wanted_label = ""
        value_text = str(value or "").strip()
        if value_text:
            wanted_label = _material_id_to_label.get(value_text, "")

        chosen_label = wanted_label if wanted_label else fallback_label
        for i in range(dd.listItems.count):
            item = dd.listItems.item(i)
            if (item.name or "").strip() == chosen_label:
                item.isSelected = True
                return
        if dd.listItems.count > 0:
            dd.listItems.item(0).isSelected = True
    except Exception as exc:
        print(f"Properties: Dropdown '{input_id}' konnte nicht gesetzt werden: {exc}")


def _format_body_size(body):
    try:
        bbox = body.boundingBox
        if not bbox:
            return "-"
        dx = abs(bbox.maxPoint.x - bbox.minPoint.x)
        dy = abs(bbox.maxPoint.y - bbox.minPoint.y)
        dz = abs(bbox.maxPoint.z - bbox.minPoint.z)
        dims_mm = sorted([dx * 10.0, dy * 10.0, dz * 10.0], reverse=True)
        return f"{dims_mm[0]:.1f} x {dims_mm[1]:.1f} x {dims_mm[2]:.1f} mm"
    except Exception as exc:
        print(f"Properties: Groesse konnte nicht berechnet werden: {exc}")
        return "-"


def _get_or_create_panel(workspace):
    global _active_panel_id

    primary = workspace.toolbarPanels.itemById(PRIMARY_PANEL_ID)
    if primary:
        _active_panel_id = PRIMARY_PANEL_ID
        return primary

    for panel_id in PANEL_IDS:
        candidate = workspace.toolbarPanels.itemById(panel_id)
        if candidate:
            _active_panel_id = panel_id
            return candidate

    tab = workspace.toolbarTabs.itemById(CUSTOM_TAB_ID)
    if not tab:
        return None

    panel = tab.toolbarPanels.itemById(CUSTOM_PANEL_ID)
    if panel:
        _active_panel_id = CUSTOM_PANEL_ID
        return panel

    panel = tab.toolbarPanels.add(CUSTOM_PANEL_ID, CUSTOM_PANEL_NAME, "", False)
    _active_panel_id = CUSTOM_PANEL_ID
    return panel


def start():
    global _command_created_handler, _is_started
    if _is_started:
        return

    app = adsk.core.Application.get()
    ui = app.userInterface
    cmd_def = ui.commandDefinitions.itemById(COMMAND_ID)
    if not cmd_def:
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            COMMAND_ID, COMMAND_NAME, COMMAND_TOOLTIP, COMMAND_RESOURCES
        )

    _command_created_handler = _CommandCreatedHandler()
    cmd_def.commandCreated.add(_command_created_handler)
    _handlers.append(_command_created_handler)

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    if not workspace:
        ui.messageBox("Properties: Workspace nicht gefunden.")
        return

    panel = _get_or_create_panel(workspace)
    if not panel:
        ui.messageBox("Properties: Panel 'Aendern' konnte nicht aufgeloest werden.")
        return

    control = panel.controls.itemById(COMMAND_ID)
    if not control:
        control = panel.controls.addCommand(cmd_def)
    if control:
        try:
            control.isPromotedByDefault = True
            control.isPromoted = True
            control.isVisible = True
        except Exception:
            pass

    _is_started = True
    print(f"Properties: Command registriert in Panel '{_active_panel_id}'.")


def stop():
    global _command_created_handler, _is_started, _active_panel_id
    app = adsk.core.Application.get()
    ui = app.userInterface

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    if workspace and _active_panel_id:
        panel = workspace.toolbarPanels.itemById(_active_panel_id)
        if panel:
            control = panel.controls.itemById(COMMAND_ID)
            if control:
                control.deleteMe()

    cmd_def = ui.commandDefinitions.itemById(COMMAND_ID)
    if cmd_def and _command_created_handler:
        try:
            cmd_def.commandCreated.remove(_command_created_handler)
        except Exception:
            pass
        _command_created_handler = None
    if cmd_def:
        cmd_def.deleteMe()

    _handlers.clear()
    _is_started = False
    _active_panel_id = None
