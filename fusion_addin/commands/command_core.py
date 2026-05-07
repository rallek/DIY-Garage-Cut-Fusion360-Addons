import adsk.core

import config

_handlers = []
_active_panel_id = None
_is_started = False
_command_created_handler = None
_marking_menu_handler = None


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
        ui = app.userInterface
        ui.messageBox("DIY Garage Cut Add-in Grundgeruest laeuft.")


class _MarkingMenuHandler(adsk.core.MarkingMenuEventHandler):
    def notify(self, args):
        try:
            event_args = adsk.core.MarkingMenuEventArgs.cast(args)
            app = adsk.core.Application.get()
            ui = app.userInterface

            # Auswahl robust aus activeSelections lesen (zuverlaessiger als manche Event-Felder).
            sels = ui.activeSelections
            if not sels or sels.count < 1:
                return

            first = sels.item(0).entity if sels.item(0) else None
            if not first:
                return

            obj_type = first.objectType or ""
            # Auch Proxy-Typen erlauben, die in Assemblies haeufig auftreten.
            is_supported = (
                "BRepBody" in obj_type
                or "Occurrence" in obj_type
                or "Component" in obj_type
            )
            if not is_supported:
                return

            cmd_def = ui.commandDefinitions.itemById(config.COMMAND_ID)
            if not cmd_def:
                return

            # In alle erreichbaren Menuebereiche einfuegen.
            menus = []
            if event_args.linearMarkingMenu:
                menus.append(event_args.linearMarkingMenu)
            if event_args.radialMarkingMenu:
                menus.append(event_args.radialMarkingMenu)

            for menu in menus:
                existing = menu.controls.itemById(config.COMMAND_ID)
                if not existing:
                    menu.controls.addCommand(cmd_def)
        except Exception:
            # Kontextmenue darf Fusion nicht stoeren.
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
    global _active_panel_id, _is_started, _command_created_handler, _marking_menu_handler
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
            "./Resources"
        )

    _command_created_handler = _CommandCreatedHandler()
    cmd_def.commandCreated.add(_command_created_handler)
    _handlers.append(_command_created_handler)

    _marking_menu_handler = _MarkingMenuHandler()
    ui.markingMenuDisplaying.add(_marking_menu_handler)
    _handlers.append(_marking_menu_handler)
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
            # Manche Fusion-Versionen erlauben diese Flags nicht in allen Panels.
            pass

def stop():
    global _active_panel_id, _is_started, _command_created_handler, _marking_menu_handler
    app = adsk.core.Application.get()
    ui = app.userInterface
    cmd_def = ui.commandDefinitions.itemById(config.COMMAND_ID)

    if _marking_menu_handler:
        try:
            ui.markingMenuDisplaying.remove(_marking_menu_handler)
        except Exception:
            pass
        _marking_menu_handler = None

    if cmd_def and _command_created_handler:
        try:
            cmd_def.commandCreated.remove(_command_created_handler)
        except Exception:
            pass
        _command_created_handler = None

    workspace = ui.workspaces.itemById(config.WORKSPACE_ID)
    if workspace:
        panel = None
        if _active_panel_id:
            panel = workspace.toolbarPanels.itemById(_active_panel_id)
            if not panel:
                tab = workspace.toolbarTabs.itemById(config.CUSTOM_TAB_ID)
                if tab:
                    panel = tab.toolbarPanels.itemById(_active_panel_id)
        if not panel:
            for panel_id in config.PANEL_IDS:
                candidate = workspace.toolbarPanels.itemById(panel_id)
                if candidate:
                    panel = candidate
                    break
        if not panel:
            tab = workspace.toolbarTabs.itemById(config.CUSTOM_TAB_ID)
            if tab:
                panel = tab.toolbarPanels.itemById(config.CUSTOM_PANEL_ID)
        if panel:
            control = panel.controls.itemById(config.COMMAND_ID)
            if control:
                control.deleteMe()

    if cmd_def:
        cmd_def.deleteMe()

    _handlers.clear()
    _active_panel_id = None
    _is_started = False
