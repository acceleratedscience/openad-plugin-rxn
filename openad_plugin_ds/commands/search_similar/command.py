"""
Example commands:
- ds search for similar molecules to CC(=CCC/C(=C/CO)/C)C
- ds search for similar molecules to 'C1(C(=C)C([O-])C1C)=O'
- ds search for similar molecules to CC1CCC2C1C(=O)OC=C2C save as 'similar_mols'
- ds search for similar molecules to CC1=CCC2CC1C2(C)C save as 'similar_mols.csv'
"""

import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2

# Plugin
from openad_grammar_def import molecules, molecule_identifier, clause_save_as
from openad_plugin_ds.plugin_grammar_def import search, f_or, similar, to
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY, CMD_NOTE, PLUGIN_NAMESPACE
from openad_plugin_ds.commands.search_similar.search_similar import search_similar_molecules
from openad_plugin_ds.commands.search_similar.description import description


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
                + clause_save_as
            )(self.parser_id)
        )

        # Command help
        grammar_help.append(
            help_dict_create_v2(
                plugin_name=PLUGIN_NAME,
                plugin_namespace=PLUGIN_NAMESPACE,
                category="Search Molecules",
                command=f"{PLUGIN_NAMESPACE} search for similar molecules to <smiles> [ save as '<filename.csv>' ]",
                description=description,
                note=CMD_NOTE,
            )
        )

    def exec_command(self, cmd_pointer, parser):
        """Execute the command"""

        cmd = parser.as_dict()
        return search_similar_molecules(cmd_pointer, cmd)
