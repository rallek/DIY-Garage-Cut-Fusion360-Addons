COMPANY_NAME = "DIYGarageCut"
ADDIN_NAME = "DIYGarageCutPropertiesAddin"

WORKSPACE_ID = "FusionSolidEnvironment"
PRIMARY_PANEL_ID = "SolidModifyPanel"
PANEL_IDS = [
    "SolidModifyPanel",
    "SolidToolsPanel",
    "SolidCreatePanel",
    "SolidScriptsAddinsPanel",
]
CUSTOM_TAB_ID = "SolidTab"
CUSTOM_PANEL_ID = f"{COMPANY_NAME}_{ADDIN_NAME}_Panel"
CUSTOM_PANEL_NAME = "DIY Garage Cut"
COMMAND_ID = f"{COMPANY_NAME}_{ADDIN_NAME}_PropertiesCommand"
COMMAND_NAME = "DIYGC Eigenschaften"
COMMAND_TOOLTIP = "Material und Fräszulage für einen Body setzen."
COMMAND_RESOURCES = "./Resources"

ATTRIBUTE_GROUP = f"{COMPANY_NAME}.part_metadata"
ATTR_KEY_MATERIAL_ID = "material_id"
ATTR_KEY_TRIM_ALLOWANCE_MM = "trim_allowance_mm"
ATTR_KEY_GRAIN_DIRECTION = "grain_direction"
ATTR_KEY_FRONT_REFERENCE = "front_reference"
ATTR_KEY_EDGE_FRONT = "edge_front"
ATTR_KEY_EDGE_BACK = "edge_back"
ATTR_KEY_EDGE_LEFT = "edge_left"
ATTR_KEY_EDGE_RIGHT = "edge_right"
ATTR_KEY_SURFACE_TOP_TEXT = "surface_top_text"
ATTR_KEY_SURFACE_BOTTOM_TEXT = "surface_bottom_text"
