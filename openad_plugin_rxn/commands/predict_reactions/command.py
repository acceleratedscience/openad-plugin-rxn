import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2

# OpenAD tools
from openad_tools.grammar_def import (
    molecule_identifier,
    list_quoted,
    str_quoted,
    str_strict_or_quoted,
    clause_using,
    clause_save_as,
)

# Plugin
from openad_plugin_rxn.plugin_grammar_def import (
    predict,
    topn,
    reaction_s,
    f_rom,
    clause_rich_output,
    clause_use_cache,
)
from openad_plugin_rxn.plugin_params import PLUGIN_NAME, PLUGIN_KEY, PLUGIN_NAMESPACE
from openad_plugin_rxn.commands.predict_reactions.predict_reactions import PredictReactions
from openad_plugin_rxn.commands.predict_reactions.description import description


class PluginCommand:
    """Predict reaction(s)..."""

    category: str  # Category of command
    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.category = "Prediction"
        self.index = 0
        self.name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        self.parser_id = f"plugin_{PLUGIN_KEY}_{self.name}"

    def add_grammar(self, statements: list, grammar_help: list):
        """Create the command definition & documentation"""

        # Command definition
        statements.append(
            py.Forward(
                py.CaselessKeyword(PLUGIN_NAMESPACE)
                + predict
                + py.Optional(topn)
                + reaction_s
                + (
                    # Multiple reactions
                    (
                        f_rom
                        + (
                            (py.Suppress("list") + list_quoted)("from_list")
                            | (py.Suppress("file") + str_quoted("from_file"))
                            | (py.Suppress("dataframe") + str_strict_or_quoted("from_df"))
                        )
                        |
                        # Single reaction
                        molecule_identifier("from_str")
                    )
                )
                + clause_using
                + clause_rich_output
                + clause_use_cache
                + clause_save_as
            )(self.parser_id)
        )

        # BACKWARD COMPATIBILITY WITH TOOLKIT COMMAND
        # -------------------------------------------
        # Original commands:
        #   - predict reaction in batch from list/file/dataframe ...  [ using (ai_model='<ai_model>') ] [ use_saved ]
        #   - predict reaction topn in batch from list/file/dataframe [ using (topn=<integer> ai_model='<ai_model>') ] [ use_saved ]
        # New command:
        #   - rxn predict reactions from list/file/dataframe ... [ USING (ai_model='<ai_model>' topn=<integer>) ] [ use cache ]
        # To be forwarded:
        #   - [ rxn ] predict reaction [ topn ] in batch from list/file/dataframe ... [ USING (topn=<integer>) ] [ use_saved ]
        statements.append(
            py.Forward(
                py.CaselessKeyword(PLUGIN_NAMESPACE)
                + predict
                + reaction_s
                + py.Optional(py.CaselessKeyword("topn")("topn"))
                + py.Optional(py.CaselessKeyword("in") + py.CaselessKeyword("batch"))
                + (
                    # Single reaction
                    str_quoted("from_str")
                    # Multiple reactions
                    | (
                        f_rom
                        + (
                            (py.Suppress("list") + list_quoted)("from_list")
                            | (py.Suppress("file") + str_quoted("from_file"))
                            | (py.Suppress("dataframe") + str_strict_or_quoted("from_df"))
                        )
                    )
                )
                + clause_using
                + clause_use_cache
                + clause_save_as
            )(self.parser_id)
        )

        # Command help
        # using_clause = "[ USING (ai_model='<ai_model>') ] [ use cache ]"
        clauses = "[ USING (ai_model='<ai_model>' topn=<integer>) ] [ rich ] [ use cache ]"
        grammar_help.append(
            help_dict_create_v2(
                plugin_name=PLUGIN_NAME,
                plugin_namespace=PLUGIN_NAMESPACE,
                category=self.category,
                command=[
                    f"{PLUGIN_NAMESPACE} predict reaction <smiles>.<smiles> {clauses}",
                    f"{PLUGIN_NAMESPACE} predict reactions from list ['<smiles>.<smiles>',...] {clauses}",
                    f"{PLUGIN_NAMESPACE} predict reactions from file '<filename.csv>' {clauses}",
                    f"{PLUGIN_NAMESPACE} predict reactions from dataframe <dataframe_name> {clauses}",
                    f"{PLUGIN_NAMESPACE} predict topn reactions <smiles>.<smiles> {clauses}",
                    f"{PLUGIN_NAMESPACE} predict topn reactions from list ['<smiles>.<smiles>',...] {clauses}",
                    f"{PLUGIN_NAMESPACE} predict topn reactions from file '<filename.csv>' {clauses}",
                    f"{PLUGIN_NAMESPACE} predict topn reactions from dataframe <dataframe_name> {clauses}",
                ],
                description=description,
            )
        )

    def exec_command(self, cmd_pointer, parser):
        """Execute the command"""
        cmd = parser.as_dict()
        predict_rections = PredictReactions(cmd_pointer, cmd)
        return predict_rections.run()
