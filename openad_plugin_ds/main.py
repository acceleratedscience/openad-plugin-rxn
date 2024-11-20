import os
import importlib.util

try:
    from openad_plugin_ds.plugin_login import login
except ImportError:
    login = None


class OpenADPlugin:
    PLUGIN_OBJECTS = {}
    statements = []
    help = []

    def __init__(self, cmd_pointer=None):
        self.statements = []
        self.help = []
        plugin_commands = []

        # Login if required
        if login:
            login(cmd_pointer)

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

            # Order the commands by their index
            help_index = plugin_class.index if hasattr(plugin_class, "index") else 1000
            plugin_commands.insert(help_index, plugin_class)

        # Initialize the plugin objects in the correct order
        for plugin_class in plugin_commands:
            self.PLUGIN_OBJECTS[plugin_class.parser_id] = plugin_class
            self.PLUGIN_OBJECTS[plugin_class.parser_id].add_grammar(self.statements, self.help)
