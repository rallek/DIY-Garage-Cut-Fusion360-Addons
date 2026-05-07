import adsk.core

import config
from lib.attribute_helpers import get_attr, set_attr

_handlers = []
_command_created_handler = None
_is_started = False

_INPUT_BODY = "diygc_body_selection"
_INPUT_MATERIAL = "diygc_material_typ"
_INPUT_KANTEN = "diygc_kanten_info"
_INPUT_EXPORT_FLAG = "diygc_export_flag"
_INPUT_NOTIZ = "diygc_notiz"


class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        event_args = adsk.core.CommandCreatedEventArgs.cast(args)
        cmd = event_args.command
        inputs = cmd.commandInputs

        sel = inputs.addSelectionInput(_INPUT_BODY, "Koerper", "Einen Koerper auswaehlen")
        sel.addSelectionFilter("Bodies")
        sel.setSelectionLimits(1, 1)

        inputs.addStringValueInput(_INPUT_MATERIAL, "material_typ", "MDF")
        inputs.addStringValueInput(_INPUT_KANTEN, "kanten_info", "vorn_2mm;links_2mm")
        inputs.addStringValueInput(_INPUT_EXPORT_FLAG, "export_flag", "true")
        inputs.addStringValueInput(_INPUT_NOTIZ, "notiz", "Testlauf Issue #4")

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
            if not changed or changed.id != _INPUT_BODY:
                return

            command = event_args.firingEvent.sender
            inputs = command.commandInputs if command else None
            if not inputs:
                return

            body = _read_selected_body(inputs)
            if not body:
                return

            _set_input_value(inputs, _INPUT_MATERIAL, get_attr(body, config.ATTR_KEY_MATERIAL_TYP, "MDF"))
            _set_input_value(inputs, _INPUT_KANTEN, get_attr(body, config.ATTR_KEY_KANTEN_INFO, "vorn_2mm;links_2mm"))
            _set_input_value(inputs, _INPUT_EXPORT_FLAG, get_attr(body, config.ATTR_KEY_EXPORT_FLAG, "true"))
            _set_input_value(inputs, _INPUT_NOTIZ, get_attr(body, config.ATTR_KEY_NOTIZ, "Testlauf Issue #4"))
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

            values = {
                config.ATTR_KEY_MATERIAL_TYP: _read_string_input(inputs, _INPUT_MATERIAL, "MDF"),
                config.ATTR_KEY_KANTEN_INFO: _read_string_input(inputs, _INPUT_KANTEN, "vorn_2mm;links_2mm"),
                config.ATTR_KEY_EXPORT_FLAG: _read_string_input(inputs, _INPUT_EXPORT_FLAG, "true"),
                config.ATTR_KEY_NOTIZ: _read_string_input(inputs, _INPUT_NOTIZ, "Testlauf Issue #4"),
            }

            results = {}
            for key, value in values.items():
                results[key] = set_attr(body, key, value)

            readback = {
                config.ATTR_KEY_MATERIAL_TYP: get_attr(body, config.ATTR_KEY_MATERIAL_TYP, "-"),
                config.ATTR_KEY_KANTEN_INFO: get_attr(body, config.ATTR_KEY_KANTEN_INFO, "-"),
                config.ATTR_KEY_EXPORT_FLAG: get_attr(body, config.ATTR_KEY_EXPORT_FLAG, "-"),
                config.ATTR_KEY_NOTIZ: get_attr(body, config.ATTR_KEY_NOTIZ, "-"),
            }

            failed = [k for k, ok in results.items() if not ok]
            status = "Status: Werte geschrieben/gelesen."
            if failed:
                status = f"Status: Teilweise fehlgeschlagen (Schreiben): {', '.join(failed)}"

            ui.messageBox(
                "Eigenschaften gespeichert:\n"
                f"Namespace: {config.ATTRIBUTE_GROUP}\n"
                f"{status}\n"
                f"{config.ATTR_KEY_MATERIAL_TYP}: {readback[config.ATTR_KEY_MATERIAL_TYP]}\n"
                f"{config.ATTR_KEY_KANTEN_INFO}: {readback[config.ATTR_KEY_KANTEN_INFO]}\n"
                f"{config.ATTR_KEY_EXPORT_FLAG}: {readback[config.ATTR_KEY_EXPORT_FLAG]}\n"
                f"{config.ATTR_KEY_NOTIZ}: {readback[config.ATTR_KEY_NOTIZ]}"
            )
        except Exception as exc:
            print(f"Properties: Execute-Fehler: {exc}")
            ui.messageBox(f"Eigenschaften fehlgeschlagen:\n{exc}")


def _read_selected_body(inputs):
    try:
        sel = adsk.core.SelectionCommandInput.cast(inputs.itemById(_INPUT_BODY))
        if not sel or sel.selectionCount < 1:
            return None
        entity = sel.selection(0).entity
        if entity and "BRepBody" in ((entity.objectType or "")):
            native = getattr(entity, "nativeObject", None)
            return native if native else entity
    except Exception as exc:
        print(f"Properties: Koerperauswahl konnte nicht gelesen werden: {exc}")
    return None


def _read_string_input(inputs, input_id, fallback):
    try:
        item = adsk.core.StringValueCommandInput.cast(inputs.itemById(input_id))
        if not item:
            return fallback
        value = (item.value or "").strip()
        return value if value else fallback
    except Exception:
        return fallback


def _set_input_value(inputs, input_id, value):
    try:
        item = adsk.core.StringValueCommandInput.cast(inputs.itemById(input_id))
        if item:
            item.value = str(value if value is not None else "")
    except Exception as exc:
        print(f"Properties: Input '{input_id}' konnte nicht gesetzt werden: {exc}")


def start(panel):
    global _command_created_handler, _is_started
    if _is_started:
        return

    app = adsk.core.Application.get()
    ui = app.userInterface
    cmd_def = ui.commandDefinitions.itemById(config.PROPERTIES_COMMAND_ID)
    if not cmd_def:
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            config.PROPERTIES_COMMAND_ID,
            config.PROPERTIES_COMMAND_NAME,
            config.PROPERTIES_COMMAND_TOOLTIP,
            config.PROPERTIES_COMMAND_RESOURCES,
        )

    _command_created_handler = _CommandCreatedHandler()
    cmd_def.commandCreated.add(_command_created_handler)
    _handlers.append(_command_created_handler)

    control = panel.controls.itemById(config.PROPERTIES_COMMAND_ID)
    if not control:
        control = panel.controls.addCommand(cmd_def)
    if control:
        try:
            control.isPromotedByDefault = True
            control.isPromoted = True
        except Exception:
            pass

    _is_started = True


def stop(panel):
    global _command_created_handler, _is_started
    app = adsk.core.Application.get()
    ui = app.userInterface

    if panel:
        control = panel.controls.itemById(config.PROPERTIES_COMMAND_ID)
        if control:
            control.deleteMe()

    cmd_def = ui.commandDefinitions.itemById(config.PROPERTIES_COMMAND_ID)
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
