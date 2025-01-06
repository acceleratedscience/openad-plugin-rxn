import os
import importlib.util

# OpenAD
from openad.helpers.plugins import reorder_commands_by_category_index, assemble_plugin_metadata


class OpenADPlugin:
    PLUGIN_OBJECTS = {}
    metadata = {}
    statements = []
    help = []

    def __init__(self):
        self.statements = []
        self.help = []
        plugin_commands = []

        # Load commands & help
        for command_name in os.listdir(os.path.dirname(os.path.abspath(__file__)) + "/commands"):
            plugin_dir = os.path.dirname(os.path.abspath(__file__)) + "/commands/" + command_name
            if not os.path.isdir(plugin_dir):
                continue
            if not os.path.exists(plugin_dir + "/command.py"):
                continue
            spec = importlib.util.spec_from_file_location(command_name, plugin_dir + "/command.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            plugin_class = module.PluginCommand()
            plugin_commands.append(plugin_class)

        # Reorder the commands by their index, per category
        plugin_commands = reorder_commands_by_category_index(plugin_commands)

        # Initialize the plugin objects in the correct order
        for plugin_class in plugin_commands:
            self.PLUGIN_OBJECTS[plugin_class.parser_id] = plugin_class
            self.PLUGIN_OBJECTS[plugin_class.parser_id].add_grammar(self.statements, self.help)

        # Assenble metadata
        self.metadata = assemble_plugin_metadata(os.path.dirname(os.path.abspath(__file__)), self.help)
