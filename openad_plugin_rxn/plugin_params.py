import os
import yaml


# Load metadata from file
plugin_metadata = {}
try:
    metadata_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugin_metadata.yaml")
    with open(metadata_file, "r", encoding="utf-8") as f:
        plugin_metadata = yaml.safe_load(f)
except Exception:  # pylint: disable=broad-except
    pass


PLUGIN_NAME = plugin_metadata.get("name")
PLUGIN_KEY = PLUGIN_NAME.lower().replace(" ", "_")  # snake_case name, for internal use
PLUGIN_NAMESPACE = plugin_metadata.get("namespace")
CLAUSES = {
    "save_as": "Use the <cmd>save as</cmd> clause to save the results as a csv file in your current workspace.",
}
