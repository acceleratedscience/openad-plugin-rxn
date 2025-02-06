import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2
from openad_tools.output import output_success
from openad_tools.helpers import confirm_prompt

# Plugin
from openad_plugin_rxn.plugin_grammar_def import reset, login
from openad_plugin_rxn.plugin_params import PLUGIN_NAME, PLUGIN_KEY, PLUGIN_NAMESPACE
from openad_plugin_rxn.plugin_login import RXNLoginManager


class PluginCommand:
    """Reset login"""

    category: str  # Category of command
    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.category = "System"
        self.index = 1
        self.name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        self.parser_id = f"plugin_{PLUGIN_KEY}_{self.name}"

    def add_grammar(self, statements: list, grammar_help: list):
        """Create the command definition & documentation"""

        # Command definition
        statements.append(
            py.Forward(py.CaselessKeyword(PLUGIN_NAMESPACE) + login + py.Optional(reset)("reset"))(self.parser_id)
        )

        # Command help
        grammar_help.append(
            help_dict_create_v2(
                plugin_name=PLUGIN_NAME,
                plugin_namespace=PLUGIN_NAMESPACE,
                category=self.category,
                command=f"{PLUGIN_NAMESPACE} login [ reset ]",
                description_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "description.txt"),
            )
        )

    def exec_command(self, cmd_pointer, parser):
        """Execute the command"""
        cmd = parser.as_dict()
        login_manager = RXNLoginManager(cmd_pointer)
        if "reset" in cmd:
            success = login_manager.reset()
            prompt_msg = "Would you like to log in again?" if success else "Would you like to log in?"
            if confirm_prompt(prompt_msg):
                login_manager.login()
        else:
            username = login_manager.is_logged_in()
            if username:
                output_success(f"You are already logged in to RXN as <reset>{username}</reset>")
            else:
                username = login_manager.login()
                if username:
                    output_success(f"You are now logged in to RXN as <reset>{username}</reset>")
