import adsk.core
import importlib
import os
import sys
import traceback

_ADDIN_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_ADDIN_DIR)
for _path in (_ADDIN_DIR, _REPO_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)
_COMMAND_MODULE = None


def _load_command_module():
    global _COMMAND_MODULE
    if _COMMAND_MODULE:
        return _COMMAND_MODULE
    _COMMAND_MODULE = importlib.import_module("commands.command_core")
    return _COMMAND_MODULE


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        _load_command_module().start()
    except Exception:
        if ui:
            ui.messageBox(f"Startfehler im Export-Add-in:\n{traceback.format_exc()}")


def stop(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        _load_command_module().stop()
    except Exception:
        if ui:
            ui.messageBox(f"Stoppfehler im Export-Add-in:\n{traceback.format_exc()}")
