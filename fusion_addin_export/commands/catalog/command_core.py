import adsk.core

import export_config as config
from shared.catalog import CATALOG_TYPES, CatalogItem, CatalogLoadError, load_catalog, save_catalog, upsert_catalog_item

_handlers = []
_active_panel_id = None
_is_started = False
_command_created_handler = None

_INPUT_SELECTION = "diygc_catalog_selection"
_INPUT_ID = "diygc_catalog_id"
_INPUT_TYPE = "diygc_catalog_type"
_INPUT_NAME = "diygc_catalog_name"
_INPUT_APPEARANCE = "diygc_catalog_appearance"
_INPUT_NEW_ENTRY = "diygc_catalog_new_entry"
_INPUT_LIST = "diygc_catalog_list"


class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        event_args = adsk.core.CommandCreatedEventArgs.cast(args)
        cmd = event_args.command
        inputs = cmd.commandInputs

        selection = inputs.addDropDownCommandInput(
            _INPUT_SELECTION,
            "Vorhandene Eintraege",
            adsk.core.DropDownStyles.TextListDropDownStyle,
        )
        selection.listItems.add("(Neu anlegen)", True)

        inputs.addBoolValueInput(_INPUT_NEW_ENTRY, "Neuen Eintrag anlegen", True, "", True)
        inputs.addStringValueInput(_INPUT_ID, "ID", "")

        type_input = inputs.addDropDownCommandInput(
            _INPUT_TYPE,
            "Typ",
            adsk.core.DropDownStyles.TextListDropDownStyle,
        )
        for i, item_type in enumerate(sorted(CATALOG_TYPES)):
            type_input.listItems.add(item_type, i == 0)

        inputs.addStringValueInput(_INPUT_NAME, "Name", "")
        inputs.addStringValueInput(_INPUT_APPEARANCE, "Appearance", "")
        list_box = inputs.addTextBoxCommandInput(_INPUT_LIST, "Kataloguebersicht", "-", 12, True)
        list_box.isFullWidth = True

        _populate_existing_items(selection)
        _refresh_list_overview(inputs)
        _sync_inputs(inputs)

        on_input_changed = _InputChangedHandler()
        cmd.inputChanged.add(on_input_changed)
        _handlers.append(on_input_changed)

        on_execute = _CommandExecuteHandler()
        cmd.execute.add(on_execute)
        _handlers.append(on_execute)


class _InputChangedHandler(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        try:
            event_args = adsk.core.InputChangedEventArgs.cast(args)
            command = event_args.firingEvent.sender if event_args else None
            inputs = command.commandInputs if command else None
            if not inputs:
                return
            _sync_inputs(inputs)
        except Exception as exc:
            print(f"Catalog-InputChanged-Fehler: {exc}")


class _CommandExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        app = adsk.core.Application.get()
        ui = app.userInterface if app else None
        if not app or not ui:
            print("Catalog: App/UI nicht verfuegbar.")
            return
        try:
            event_args = adsk.core.CommandEventArgs.cast(args)
            command = event_args.command if event_args else None
            inputs = command.commandInputs if command else None
            if not inputs:
                ui.messageBox("Catalog-Fehler: Keine Command-Inputs verfuegbar.")
                return

            created, saved_item = _save_from_inputs(inputs)
            action = "angelegt" if created else "aktualisiert"
            ui.messageBox(f"Katalogeintrag gespeichert ({action}):\n{saved_item.id}")
            _refresh_list_overview(inputs)
            _refresh_selection_after_save(inputs, saved_item.id)
            _sync_inputs(inputs)
        except CatalogLoadError as exc:
            ui.messageBox(f"Katalog konnte nicht gespeichert werden:\n{exc}")
        except ValueError as exc:
            ui.messageBox(f"Ungueltige Eingabe:\n{exc}")
        except Exception as exc:
            print(f"Catalog-Execute-Fehler: {exc}")
            ui.messageBox(f"Katalogspeicherung fehlgeschlagen:\n{exc}")


def _load_catalog_data():
    return load_catalog()


def _save_from_inputs(inputs):
    catalog = _load_catalog_data()
    is_new = _read_bool(inputs, _INPUT_NEW_ENTRY, True)
    item_id = _read_string(inputs, _INPUT_ID)
    item_type = _read_dropdown(inputs, _INPUT_TYPE)
    item_name = _read_string(inputs, _INPUT_NAME)
    appearance = _read_string(inputs, _INPUT_APPEARANCE)

    if not item_id:
        raise ValueError("ID darf nicht leer sein.")
    if not item_type:
        raise ValueError("Typ darf nicht leer sein.")
    if item_type not in CATALOG_TYPES:
        raise ValueError(f"Typ nicht unterstuetzt: {item_type}")
    if not item_name:
        raise ValueError("Name darf nicht leer sein.")
    if not appearance:
        raise ValueError("Appearance darf nicht leer sein.")

    existing = catalog.get(item_id)
    if is_new and existing is not None:
        raise ValueError(f"ID existiert bereits: {item_id}")
    if not is_new and existing is None:
        raise ValueError(f"Eintrag mit ID nicht gefunden: {item_id}")

    new_item = CatalogItem.from_dict(
        {
            "id": item_id,
            "type": item_type,
            "name": item_name,
            "appearance": appearance,
        }
    )
    next_catalog = upsert_catalog_item(catalog, new_item)
    save_catalog(next_catalog)
    return existing is None, new_item


def _refresh_selection_after_save(inputs, selected_id):
    selection = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_SELECTION))
    if not selection:
        return
    _populate_existing_items(selection, selected_id=selected_id)


def _populate_existing_items(dropdown, selected_id=None):
    dropdown.listItems.clear()
    dropdown.listItems.add("(Neu anlegen)", selected_id is None)
    catalog = _load_catalog_data()
    for item in sorted(catalog.items, key=lambda x: x.id.lower()):
        label = f"{item.id} | {item.type} | {item.name}"
        is_selected = selected_id == item.id
        dropdown.listItems.add(label, is_selected)


def _sync_inputs(inputs):
    selection = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_SELECTION))
    if not selection or not selection.selectedItem:
        return

    selected_text = selection.selectedItem.name or ""
    selected_id = selected_text.split("|", 1)[0].strip() if "|" in selected_text else ""
    is_new_mode = _read_bool(inputs, _INPUT_NEW_ENTRY, True)
    selected_item = _load_catalog_data().get(selected_id) if selected_id else None

    if selected_item and not is_new_mode:
        _set_string(inputs, _INPUT_ID, selected_item.id)
        _set_dropdown(inputs, _INPUT_TYPE, selected_item.type)
        _set_string(inputs, _INPUT_NAME, selected_item.name)
        _set_string(inputs, _INPUT_APPEARANCE, selected_item.appearance)
    elif selected_item and is_new_mode:
        _set_string(inputs, _INPUT_ID, "")
        _set_string(inputs, _INPUT_NAME, "")
        _set_string(inputs, _INPUT_APPEARANCE, "")
    elif not selected_item:
        _set_bool(inputs, _INPUT_NEW_ENTRY, True)

    _refresh_list_overview(inputs)


def _refresh_list_overview(inputs):
    box = adsk.core.TextBoxCommandInput.cast(inputs.itemById(_INPUT_LIST))
    if not box:
        return
    try:
        catalog = _load_catalog_data()
        if not catalog.items:
            box.text = "Keine Eintraege vorhanden."
            return
        lines = []
        for item in sorted(catalog.items, key=lambda x: x.id.lower()):
            lines.append(f"{item.id} | {item.type} | {item.name} | {item.appearance}")
        box.text = "\n".join(lines)
    except Exception as exc:
        box.text = f"Katalog kann nicht geladen werden: {exc}"


def _read_string(inputs, input_id):
    item = adsk.core.StringValueCommandInput.cast(inputs.itemById(input_id))
    if not item:
        return ""
    return (item.value or "").strip()


def _set_string(inputs, input_id, value):
    item = adsk.core.StringValueCommandInput.cast(inputs.itemById(input_id))
    if item:
        item.value = value or ""


def _read_bool(inputs, input_id, fallback):
    item = adsk.core.BoolValueCommandInput.cast(inputs.itemById(input_id))
    if not item:
        return fallback
    return bool(item.value)


def _set_bool(inputs, input_id, value):
    item = adsk.core.BoolValueCommandInput.cast(inputs.itemById(input_id))
    if item:
        item.value = bool(value)


def _read_dropdown(inputs, input_id):
    dd = adsk.core.DropDownCommandInput.cast(inputs.itemById(input_id))
    if not dd or not dd.selectedItem:
        return ""
    return (dd.selectedItem.name or "").strip()


def _set_dropdown(inputs, input_id, wanted):
    dd = adsk.core.DropDownCommandInput.cast(inputs.itemById(input_id))
    if not dd:
        return
    wanted_norm = (wanted or "").strip().lower()
    for i in range(dd.listItems.count):
        item = dd.listItems.item(i)
        if (item.name or "").strip().lower() == wanted_norm:
            item.isSelected = True
            return


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

    cmd_def = ui.commandDefinitions.itemById(config.CATALOG_COMMAND_ID)
    if not cmd_def:
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            config.CATALOG_COMMAND_ID,
            config.CATALOG_COMMAND_NAME,
            config.CATALOG_COMMAND_TOOLTIP,
            config.CATALOG_COMMAND_RESOURCES,
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

    control = panel.controls.itemById(config.CATALOG_COMMAND_ID)
    if not control:
        control = panel.controls.addCommand(cmd_def)

    if control:
        try:
            control.isPromotedByDefault = True
            control.isPromoted = False
        except Exception:
            pass


def stop():
    global _active_panel_id, _is_started, _command_created_handler
    app = adsk.core.Application.get()
    ui = app.userInterface
    cmd_def = ui.commandDefinitions.itemById(config.CATALOG_COMMAND_ID)

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
            control = panel.controls.itemById(config.CATALOG_COMMAND_ID)
            if control:
                control.deleteMe()

    if cmd_def:
        cmd_def.deleteMe()

    _handlers.clear()
    _active_panel_id = None
    _is_started = False
