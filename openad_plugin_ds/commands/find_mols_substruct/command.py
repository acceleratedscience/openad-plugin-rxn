import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2
from openad.helpers.output import output_error, output_warning, output_text, output_success, output_table

# Plugin
from openad_grammar_def import molecules, molecule_identifier, clause_save_as
from openad_plugin_ds.plugin_grammar_def import find, w_ith, substructure
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY, CMD_NOTE, PLUGIN_NAMESPACE

from openad_plugin_ds.commands.find_mols_substruct.find_mols_substruct import find_substructure_molecules
from openad_plugin_ds.commands.find_mols_substruct.description import description

# Login
from openad_plugin_ds.plugin_login import login


class PluginCommand:
    """Find molecules with substructure..."""

    category: str  # Category of command
    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.category = "Molecules"
        self.index = 1
        self.name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        self.parser_id = f"plugin_{PLUGIN_KEY}_{self.name}"

    def add_grammar(self, statements: list, grammar_help: list):
        """Create the command definition & documentation"""

        # Command definition
        statements.append(
            py.Forward(
                py.Word(PLUGIN_NAMESPACE)
                + find
                + molecules
                + w_ith
                + substructure
                + molecule_identifier("smiles")
                + clause_save_as
            )(self.parser_id)
        )

        # Command help
        grammar_help.append(
            help_dict_create_v2(
                plugin_name=PLUGIN_NAME,
                plugin_namespace=PLUGIN_NAMESPACE,
                category=self.category,
                command=f"{PLUGIN_NAMESPACE} find molecules with substructure <smiles> [ save as '<filename.csv>' ]",
                description=description,
                note=CMD_NOTE,
            )
        )

    def exec_command(self, cmd_pointer, parser):
        """Execute the command"""

        # Login
        login(cmd_pointer)

        # Execute
        cmd = parser.as_dict()
        return find_substructure_molecules(cmd_pointer, cmd)
