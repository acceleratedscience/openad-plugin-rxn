import os
import pyparsing as py

# OpenAD
from openad.helpers.output import output_text, output_error
from openad.helpers.plugins import display_plugin_overview

# Plugin
from openad_plugin_rxn.plugin_params import PLUGIN_NAMESPACE, PLUGIN_NAME, PLUGIN_DESCRIPTION


class PluginCommand:
    """Plugin overview"""

    category: str = ""
    index: int = 0
    parser_id: str

    def __init__(self):
        self.parser_id = "plugin_overview"

    # def add_grammar(self, statements: list, grammar_help: list):
    #     statements.append(py.Forward(py.Word(PLUGIN_NAMESPACE))(self.parser_id))

    def exec_command(self, cmd_pointer, parser):
        # Open plugin_description.txt and display its contents.
        # try:
        #     description_file = os.path.join(
        #         os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "plugin_description.txt"
        #     )
        #     print(description_file)
        #     with open(description_file, "r", encoding="utf-8") as f:
        #         output_text(f.read())
        # except FileNotFoundError:
        #     output_error("No plugin description found")
        # except Exception as e:  # pylint: disable=broad-except
        #     output_error(["An error occurred reading the plugin's description", e])

        return display_plugin_overview(PLUGIN_NAME, PLUGIN_DESCRIPTION)
