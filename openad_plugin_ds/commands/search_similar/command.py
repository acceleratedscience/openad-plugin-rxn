import os
import datetime
import pandas as pd
import pyparsing as py

# Plugin architecture
from openad.core.help import help_dict_create_v2
from openad_grammar_def import save_as, molecules, molecule_identifier, quoted, opt_quoted
from openad_plugin_ds.plugin_grammar import search, f_or, similar, to, save, a_s
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY, CMD_NOTE, PLUGIN_NAMESPACE

# OpenAD tools
from openad.helpers.output import output_error, output_warning, output_text, output_success, output_table

# Local tools
from openad_plugin_ds.commands.search_similar.search_similar import search_similar_molecules
from openad_plugin_ds.commands.search_similar.description import description
from openad_plugin_ds.plugin_login import login


# login(cmd_pointer, PLUGIN_NAME, PLUGIN_KEY)


class PluginCommand:
    """Search for similar molecules command"""

    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.index = 0
        self.name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        self.parser_id = f"plugin_{PLUGIN_KEY}_{self.name}"

    def add_grammar(self, statements: list, grammar_help: list):
        """Create the command definition & documentation"""

        # Command definition
        statements.append(
            py.Forward(
                py.Word(PLUGIN_NAMESPACE)
                + search
                + f_or
                + similar
                + molecules
                + to
                + molecule_identifier("smiles")
                + save_as
            )(self.parser_id)
        )

        # Command help
        grammar_help.append(
            help_dict_create_v2(
                category=PLUGIN_NAME,
                command=f"{PLUGIN_NAMESPACE} search for similar molecules to <smiles> [ save as '<filename.csv>' ]",
                description=description,
                note=CMD_NOTE,
            )
        )

    def exec_command(self, cmd_pointer, parser):
        """Execute the command"""

        return search_similar_molecules(cmd_pointer, parser)
