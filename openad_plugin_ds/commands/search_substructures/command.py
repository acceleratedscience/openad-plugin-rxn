"""
Example commands:
- ds search for substructure instances of C1(C(=C)C([O-])C1C)=O
- ds search for substructure instances of 'C1=CCCCC1' save as 'my_mol'
"""

import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2
from openad.helpers.output import output_error, output_warning, output_text, output_success, output_table

# Plugin
from openad_grammar_def import molecule_identifier, clause_save_as
from openad_plugin_ds.plugin_grammar_def import search, f_or, substructure, instances, of
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY, CMD_NOTE, PLUGIN_NAMESPACE

from openad_plugin_ds.commands.search_substructures.search_substructures import search_substructure_molecules
from openad_plugin_ds.commands.search_substructures.description import description


class PluginCommand:
    """Search for substructures command"""

    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.index = 1
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
                + substructure
                + instances
                + of
                + molecule_identifier("smiles")
                + clause_save_as
            )(self.parser_id)
        )

        # Command help
        grammar_help.append(
            help_dict_create_v2(
                category=PLUGIN_NAME,
                command=f"{PLUGIN_NAMESPACE} search for substructure instances of <smiles> [ save as '<filename.csv>' ]",
                description=description,
                note=CMD_NOTE,
            )
        )

    def exec_command(self, cmd_pointer, parser):
        """Execute the command"""

        cmd = parser.as_dict()
        search_substructure_molecules(cmd_pointer, cmd)
