import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2

# Plugin
from openad_grammar_def import str_quoted, list_quoted, clause_save_as
from openad_plugin_ds.plugin_grammar_def import display, collections, f_or, domain, domains
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY, CMD_NOTE, PLUGIN_NAMESPACE
from openad_plugin_ds.commands.display_collections_for_domain.display_collections_for_domain import (
    display_collections_for_domain,
)
from openad_plugin_ds.commands.display_collections_for_domain.description import description


class PluginCommand:
    """Display collections for domain command"""

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
        statements.append(
            py.Forward(
                py.Word(PLUGIN_NAMESPACE)
                + display
                + collections
                + f_or
                + (domain | domains)
                + (str_quoted("domain") | list_quoted("domain_list"))
                + clause_save_as
            )(self.parser_id)
        )

        # Command help
        # grammar_help.append(
        #     help_dict_create_v2(
        #         category=PLUGIN_NAME,
        #         command=f"""{PLUGIN_NAMESPACE} display collections for domain '<domain_name>' [ save as '<filename.csv>' ]""",
        #         description=description,
        #         note=CMD_NOTE,
        #     )
        # )
        # grammar_help.append(
        #     help_dict_create_v2(
        #         category=PLUGIN_NAME,
        #         command=f"""{PLUGIN_NAMESPACE} display collections for domains ['<domain_name>','<domain_name>',...] [ save as '<filename.csv>' ]""",
        #         description=description,
        #         note=CMD_NOTE,
        #     )
        # )
        grammar_help.append(
            help_dict_create_v2(
                plugin_name=PLUGIN_NAME,
                plugin_namespace=PLUGIN_NAMESPACE,
                category="Collections",
                command=[
                    f"""{PLUGIN_NAMESPACE} display collections for domain '<domain_name>' [ save as '<filename.csv>' ]""",
                    f"""{PLUGIN_NAMESPACE} display collections for domains ['<domain_name>','<domain_name>',...] [ save as '<filename.csv>' ]""",
                ],
                description=description,
                note=CMD_NOTE,
            )
        )

    def exec_command(self, cmd_pointer, parser):
        """Execute the command"""

        cmd = parser.as_dict()
        # print(cmd)
        return display_collections_for_domain(cmd_pointer, cmd)
