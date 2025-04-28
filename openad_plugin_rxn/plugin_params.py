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
    "save_as": "<cmd>save as</cmd>\n    Save the results as a csv file in your current workspace.",
    "use_cache": "<cmd>use cache</cmd>\n    Use cached results when available.",
    "rich_output": "<cmd>rich</cmd>\n    Display rich output. This will make your results easier to understand but will take up more vertical space.",
}
