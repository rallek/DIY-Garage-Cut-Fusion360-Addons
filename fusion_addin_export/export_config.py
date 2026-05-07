COMPANY_NAME = "DIYGarageCut"
ADDIN_NAME = "DIYGarageCutExportAddin"

WORKSPACE_ID = "FusionSolidEnvironment"
PRIMARY_PANEL_ID = "SolidScriptsAddinsPanel"
PANEL_IDS = [
    "SolidScriptsAddinsPanel",
    "SolidToolsPanel",
    "SolidModifyPanel",
    "SolidCreatePanel",
]
CUSTOM_TAB_ID = "SolidTab"
CUSTOM_PANEL_ID = f"{COMPANY_NAME}_{ADDIN_NAME}_Panel"
CUSTOM_PANEL_NAME = "DIY Garage Cut"
COMMAND_ID = f"{COMPANY_NAME}_{ADDIN_NAME}_ExportCommand"
COMMAND_NAME = "DIY Garage Cut Export"
COMMAND_TOOLTIP = "Exportiert sichtbare Bodies als CSV-Datei."
COMMAND_RESOURCES = "./Resources"
