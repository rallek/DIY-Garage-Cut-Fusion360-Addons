from . import catalog, export

_COMMAND_MODULES = (
    catalog,
    export,
    # Foundation only: future commands are present but not yet activated.
    # validate,
)


def start():
    for module in _COMMAND_MODULES:
        module.start()


def stop():
    for module in reversed(_COMMAND_MODULES):
        module.stop()
