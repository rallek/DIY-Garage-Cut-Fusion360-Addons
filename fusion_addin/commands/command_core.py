import adsk.core

import config

_handlers = []
_active_panel_id = None


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
    global _active_panel_id
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

    on_command_created = _CommandCreatedHandler()
    cmd_def.commandCreated.add(on_command_created)
    _handlers.append(on_command_created)

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
    global _active_panel_id
    app = adsk.core.Application.get()
    ui = app.userInterface

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

    cmd_def = ui.commandDefinitions.itemById(config.COMMAND_ID)
    if cmd_def:
        cmd_def.deleteMe()

    _handlers.clear()
    _active_panel_id = None
