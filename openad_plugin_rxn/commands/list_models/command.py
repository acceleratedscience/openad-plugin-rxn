import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2

# OpenAD tools
from openad_tools.grammar_def import clause_save_as

# Plugin
from openad_plugin_rxn.plugin_grammar_def import l_ist, models
from openad_plugin_rxn.plugin_params import PLUGIN_NAME, PLUGIN_KEY, PLUGIN_NAMESPACE
from openad_plugin_rxn.commands.list_models.list_models import ListModels
from openad_plugin_rxn.commands.list_models.description import description


class PluginCommand:
    """List rxn models"""

    category: str  # Category of command
    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.category = "General"
        self.index = 0
        self.name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        self.parser_id = f"plugin_{PLUGIN_KEY}_{self.name}"

    def add_grammar(self, statements: list, grammar_help: list):
        """Create the command definition & documentation"""

        # Command definition
        statements.append(
            py.Forward(py.CaselessKeyword(PLUGIN_NAMESPACE) + l_ist + models + clause_save_as)(self.parser_id)
        )

        # BACKWARD COMPATIBILITY WITH TOOLKIT COMMAND
        # -------------------------------------------
        # Original command:
        #   - list rxn models
        # New command:
        #   - rxn list models
        # To be forwarded:
        #   - [ rxn ] list rxn models
        statements.append(
            py.Forward(
                py.CaselessKeyword(PLUGIN_NAMESPACE) + l_ist + py.CaselessKeyword("rxn") + models + clause_save_as
            )(self.parser_id)
        )

        # Command help
        grammar_help.append(
            help_dict_create_v2(
                plugin_name=PLUGIN_NAME,
                plugin_namespace=PLUGIN_NAMESPACE,
                category=self.category,
                command=f"{PLUGIN_NAMESPACE} list models [ save as '<filename.csv>' ]",
                description=description,
            )
        )

    def exec_command(self, cmd_pointer, parser):
        """Execute the command"""
        cmd = parser.as_dict()
        list_models = ListModels(cmd_pointer, cmd)
        return list_models.run()
