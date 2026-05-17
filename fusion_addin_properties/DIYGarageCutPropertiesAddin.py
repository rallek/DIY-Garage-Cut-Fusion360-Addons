import adsk.core
import importlib.util
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
    module_path = os.path.join(_ADDIN_DIR, "commands", "command_core.py")
    spec = importlib.util.spec_from_file_location("diygc_properties_command_core", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _COMMAND_MODULE = module
    return module


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        _load_command_module().start()
    except Exception:
        if ui:
            ui.messageBox(f"Startfehler im Properties-Add-in:\n{traceback.format_exc()}")


def stop(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        _load_command_module().stop()
    except Exception:
        if ui:
            ui.messageBox(f"Stoppfehler im Properties-Add-in:\n{traceback.format_exc()}")
