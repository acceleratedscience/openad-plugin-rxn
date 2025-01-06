import os
import json

# Load metadata from file
plugin_metadata = {}
try:
    metadata_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugin_metadata.json")
    with open(metadata_file, "r", encoding="utf-8") as f:
        plugin_metadata = json.load(f)
except Exception:  # pylint: disable=broad-except
    pass


# Displayed above the list of plugin commands in the help.
# - - -
# Keep this as short as possible, as it is also used to
# list all your plugin's commands.
PLUGIN_NAME = plugin_metadata.get("name")


# Snake case name of the plugin, only used internally.
PLUGIN_KEY = PLUGIN_NAME.lower().replace(" ", "_")


# Namespace for your plugin commands
# - - -
# A short string (2-3 chars max) that will be required in front of every command.
# Doubles as a shortcut to list all your plugin's commands.
PLUGIN_NAMESPACE = plugin_metadata.get("namespace")


# Clauses that are repeated across the descriptions of multiple commands.
CLAUSES = {
    "save_as": "Use the <cmd>save as</cmd> clause to save the results as a csv file in your current workspace.",
}
