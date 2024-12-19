import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2

# Plugin
from openad_grammar_def import list_quoted, str_quoted, str_strict_or_quoted
from openad_plugin_rxn.plugin_grammar_def import (
    predict,
    reaction_s,
    f_rom,
    clause_no_cache,
)
from openad_plugin_rxn.plugin_params import PLUGIN_NAME, PLUGIN_KEY, CMD_NOTE, PLUGIN_NAMESPACE

from openad_plugin_rxn.commands.predict_reactions.predict_reactions import predict_reactions
from openad_plugin_rxn.commands.predict_reactions.description import description

# Login
from openad_plugin_rxn.plugin_login import login


class PluginCommand:
    """Predict reaction(s)..."""

    category: str  # Category of command
    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.category = "General"
        self.index = 0
        self.name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        self.parser_id = f"plugin_{PLUGIN_KEY}_{self.name}"

    def add_grammar(self, statements: list, grammar_help: list):
        """Create the command definition & documentation"""

        # Command definition
        statements.append(
            py.Forward(
                py.Word(PLUGIN_NAMESPACE)
                + predict
                + reaction_s
                + (
                    # Single reaction
                    str_quoted("from_str")
                    # Multiple reactions
                    | (
                        f_rom
                        + (
                            (py.Suppress("list") + list_quoted)("from_list")
                            | (py.Suppress("file") + str_quoted)("from_file")
                            | (py.Suppress("dataframe") + str_strict_or_quoted)("from_df")
                        )
                    )
                )
                + clause_no_cache
            )(self.parser_id)
        )

        # Command help
        clauses_single = "[ USING (ai_model='<ai_model>') ] [ use saved ]"
        clauses_multiple = "[ USING (ai_model='<ai_model>' <topn>=<integer>) ] [ use saved ]"
        grammar_help.append(
            help_dict_create_v2(
                plugin_name=PLUGIN_NAME,
                plugin_namespace=PLUGIN_NAMESPACE,
                category=self.category,
                command=[
                    f"{PLUGIN_NAMESPACE} predict reaction '<smiles>.<smiles>' {clauses_single}",
                    f"{PLUGIN_NAMESPACE} predict reactions from list ['<smiles>.<smiles>',...] {clauses_multiple}",
                    f"{PLUGIN_NAMESPACE} predict reactions from file '<filename.csv>' {clauses_multiple}",
                    f"{PLUGIN_NAMESPACE} predict reactions from dataframe <dataframe_name> {clauses_multiple}",
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
        return predict_reactions(cmd_pointer, cmd)
