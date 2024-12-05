"""
Example commands:
- ds search for patents containing molecule CC(C)(c1ccccn1)C(CC(=O)O)Nc1nc(-c2c[nH]c3ncc(Cl)cc23)c(C#N)cc1F
- ds search for patents containing molecule 'CC(C)(c1ccccn1)C(CC(=O)O)Nc1nc(-c2c[nH]c3ncc(Cl)cc23)c(C#N)cc1F' save as 'patents'
- ds search for patents containing molecule InChI=1S/C24H20ClFN6O2/c1-24(2,18-5-3-4-6-28-18)19(9-20(33)34)31-23-17(26)7-13(10-27)21(32-23)16-12-30-22-15(16)8-14(25)11-29-22/h3-8,11-12,19H,9H2,1-2H3,(H,29,30)(H,31,32)(H,33,34)
- ds search for patents containing molecule JUPUMSRQQQUOLP-UHFFFAOYSA-N save as 'patents'
- ds search for patents containing molecule 'JUPUMSRQQQUOLP-UHFFFAOYSA-N'
"""

import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2

# Plugin
from openad_grammar_def import molecule_identifier, molecule, clause_save_as
from openad_plugin_ds.plugin_grammar_def import search, f_or, patents, containing
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY, CMD_NOTE, PLUGIN_NAMESPACE
from openad_plugin_ds.commands.search_patents.search_patents import search_patents_containing_molecule
from openad_plugin_ds.commands.search_patents.description import description


class PluginCommand:
    """Search for patents containing a molecule command"""

    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.index = 3
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
                + patents
                + containing
                + molecule
                + molecule_identifier("identifier")
                + clause_save_as
            )(self.parser_id)
        )

        # Command help
        grammar_help.append(
            help_dict_create_v2(
                category=PLUGIN_NAME,
                command=f"{PLUGIN_NAMESPACE} search for patents containing molecule <smiles> | <inchi> | <inchikey> [ save as '<filename.csv>' ]",
                description=description,
                note=CMD_NOTE,
            )
        )

    def exec_command(self, cmd_pointer, parser):
        """Execute the command"""

        cmd = parser.as_dict()
        return search_patents_containing_molecule(cmd_pointer, cmd)
