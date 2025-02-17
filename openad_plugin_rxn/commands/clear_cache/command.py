import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2

# Plugin
from openad_plugin_rxn.plugin_grammar_def import clear, cache
from openad_plugin_rxn.plugin_params import PLUGIN_NAME, PLUGIN_KEY, PLUGIN_NAMESPACE
from openad_plugin_rxn.plugin_master_class import RXNPlugin


class PluginCommand:
    """Clear cache"""

    category: str  # Category of command
    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.category = "System"
        self.index = 0
        self.name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        self.parser_id = f"plugin_{PLUGIN_KEY}_{self.name}"

    def add_grammar(self, statements: list, grammar_help: list):
        """Create the command definition & documentation"""

        # Command definition
        statements.append(py.Forward(py.CaselessKeyword(PLUGIN_NAMESPACE) + clear + cache)(self.parser_id))

        # Command help
        grammar_help.append(
            help_dict_create_v2(
                plugin_name=PLUGIN_NAME,
                plugin_namespace=PLUGIN_NAMESPACE,
                category=self.category,
                command=f"{PLUGIN_NAMESPACE} clear cache",
                description_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "description.txt"),
            )
        )

    def exec_command(self, cmd_pointer, parser):
        """Execute the command"""
        rxn_plugin = RXNPlugin(cmd_pointer)
        rxn_plugin.clear_cache()
