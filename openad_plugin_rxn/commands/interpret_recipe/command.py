import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2

# Plugin
from openad_grammar_def import str_quoted
from openad_plugin_rxn.plugin_grammar_def import interpret, recipe
from openad_plugin_rxn.plugin_params import PLUGIN_NAME, PLUGIN_KEY, CMD_NOTE, PLUGIN_NAMESPACE
from openad_plugin_rxn.commands.interpret_recipe.interpret_recipe import InterpretRecipe


class PluginCommand:
    """Interpret recipe..."""

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
            py.Forward(py.Word(PLUGIN_NAMESPACE) + interpret + recipe + str_quoted("recipe"))(self.parser_id)
        )

        # Command help
        grammar_help.append(
            help_dict_create_v2(
                plugin_name=PLUGIN_NAME,
                plugin_namespace=PLUGIN_NAMESPACE,
                category=self.category,
                command=f"{PLUGIN_NAMESPACE} interpret recipe '<recipe>' | '<recipe.txt>' ",
                description_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "description.txt"),
                note=CMD_NOTE,
            )
        )

    def exec_command(self, cmd_pointer, parser):
        """Execute the command"""
        cmd = parser.as_dict()
        interpret_recipe = InterpretRecipe(cmd_pointer, cmd)
        return interpret_recipe.run(cmd_pointer, cmd)
