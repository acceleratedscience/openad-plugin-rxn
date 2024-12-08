import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2

# Plugin
from openad_grammar_def import molecule_identifier, molecule, clause_save_as
from openad_plugin_ds.plugin_grammar_def import find, patents, containing
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY, CMD_NOTE, PLUGIN_NAMESPACE
from openad_plugin_ds.commands.find_patents.find_patents import find_patents_containing_molecule
from openad_plugin_ds.commands.find_patents.description import description

# Login
from openad_plugin_ds.plugin_login import login


class PluginCommand:
    """Find patents containing molecule..."""

    category: str  # Category of command
    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.category = "Patents"
        self.index = 0
        self.name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        self.parser_id = f"plugin_{PLUGIN_KEY}_{self.name}"

    def add_grammar(self, statements: list, grammar_help: list):
        """Create the command definition & documentation"""

        # Command definition
        statements.append(
            py.Forward(
                py.Word(PLUGIN_NAMESPACE)
                + find
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
                plugin_name=PLUGIN_NAME,
                plugin_namespace=PLUGIN_NAMESPACE,
                category=self.category,
                command=f"{PLUGIN_NAMESPACE} find patents containing molecule <smiles> | <inchi> | <inchikey> [ save as '<filename.csv>' ]",
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
        return find_patents_containing_molecule(cmd_pointer, cmd)
