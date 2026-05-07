import adsk.core
import os
import sys
import traceback

_ADDIN_DIR = os.path.dirname(os.path.abspath(__file__))
if _ADDIN_DIR not in sys.path:
    sys.path.insert(0, _ADDIN_DIR)

from commands import command_core


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        command_core.start()
    except Exception:
        if ui:
            ui.messageBox(f"Startfehler im Add-in:\n{traceback.format_exc()}")


def stop(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        command_core.stop()
    except Exception:
        if ui:
            ui.messageBox(f"Stoppfehler im Add-in:\n{traceback.format_exc()}")
