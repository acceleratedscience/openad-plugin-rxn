import os
import datetime
import pandas as pd
import pyparsing as py

# Plugin architecture
from openad.core.help import help_dict_create_v2

# from openad.core.grammar_def import opt_quoted
# from openad_plugin_ds.plugin_grammar import
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY, CMD_NOTE, PLUGIN_NAMESPACE

# OpenAD tools
from openad.helpers.output import output_error, output_warning, output_text, output_success, output_table

# Local tools
# ...


class PluginCommand:
    """Search for molecules in patents command"""

    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.index = 2
        self.name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        self.parser_id = f"plugin_{PLUGIN_KEY}_{self.name}"

    def add_grammar(self, statements: list, grammar_help: list):
        """Create the command definition & documentation"""

        # Command definition
        statements.append(py.Forward("TBD")(self.parser_id))

        # Command help
        grammar_help.append(
            help_dict_create_v2(
                category=PLUGIN_NAME,
                command=f"{PLUGIN_NAMESPACE} TBD",
                description_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "description.txt"),
                note=CMD_NOTE,
            )
        )

    def exec_command(self, cmd_pointer, parser):
        """Execute the command"""

        cmd = parser.as_dict()
        print("EXEC: ", cmd)

        # TBD
        pass
