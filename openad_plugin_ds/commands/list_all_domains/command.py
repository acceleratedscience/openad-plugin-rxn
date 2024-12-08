import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2

# Plugin
from openad_grammar_def import clause_save_as
from openad_plugin_ds.plugin_grammar_def import l_ist, a_ll, domains
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY, CMD_NOTE, PLUGIN_NAMESPACE
from openad_plugin_ds.commands.list_all_domains.list_all_domains import list_all_domains
from openad_plugin_ds.commands.list_all_domains.description import description

# Login
from openad_plugin_ds.plugin_login import login


class PluginCommand:
    """List all domains..."""

    category: str  # Category of command
    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.category = "Collections"
        self.index = 1
        self.name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        self.parser_id = f"plugin_{PLUGIN_KEY}_{self.name}"

    def add_grammar(self, statements: l_ist, grammar_help: l_ist):
        """Create the command definition & documentation"""

        # Command definition
        statements.append(
            py.Forward(py.Word(PLUGIN_NAMESPACE) + l_ist + a_ll + domains + clause_save_as)(self.parser_id)
        )
        grammar_help.append(
            help_dict_create_v2(
                plugin_name=PLUGIN_NAME,
                plugin_namespace=PLUGIN_NAMESPACE,  # <reverse> {PLUGIN_NAME} </reverse>
                category=self.category,
                command=f"""{PLUGIN_NAMESPACE} list all domains [ save as '<filename.csv>' ]""",
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
        # print(cmd)
        return list_all_domains(cmd_pointer, cmd)
