import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2

# Plugin
from openad_grammar_def import molecules, list_quoted, str_quoted, str_strict, clause_save_as
from openad_plugin_ds.plugin_grammar_def import find, i_n, patents, f_rom, l_ist, file, dataframe
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY, CMD_NOTE, PLUGIN_NAMESPACE
from openad_plugin_ds.commands.find_mols_in_patents.find_mols_in_patents import find_molecules_in_patents
from openad_plugin_ds.commands.find_mols_in_patents.description import description

# Login
from openad_plugin_ds.plugin_login import login


class PluginCommand:
    """Find molecules in patents..."""

    category: str  # Category of command
    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.category = "Molecules"
        self.index = 2
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
                + i_n
                + patents
                + f_rom
                + (
                    (l_ist + list_quoted("list"))
                    | (file + str_quoted("filename"))
                    | (dataframe + str_strict("df_name"))
                )
                + clause_save_as
            )(self.parser_id)
        )

        # Command help
        grammar_help.append(
            help_dict_create_v2(
                plugin_name=PLUGIN_NAME,
                plugin_namespace=PLUGIN_NAMESPACE,
                category=self.category,
                command=[
                    f"""{PLUGIN_NAMESPACE} find molecules in patents from file '<filename.csv>' [ save as '<filename.csv>' ]""",
                    f"""{PLUGIN_NAMESPACE} find molecules in patents from list ['<patent_id>','<patent_id>',...] [ save as '<filename.csv>' ]""",
                    f"""{PLUGIN_NAMESPACE} find molecules in patents from dataframe <dataframe_name> [ save as '<filename.csv>' ]""",
                ],
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
        return find_molecules_in_patents(cmd_pointer, cmd)
