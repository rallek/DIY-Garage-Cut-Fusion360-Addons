from . import catalog, export, validate

_COMMAND_MODULES = (
    catalog,
    validate,
    export,
)


def start():
    for module in _COMMAND_MODULES:
        module.start()


def stop():
    for module in reversed(_COMMAND_MODULES):
        module.stop()
