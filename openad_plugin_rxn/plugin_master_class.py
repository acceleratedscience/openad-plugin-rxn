import os
import pickle
import pandas as pd

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS

# OpenAD tools
from openad_tools.pyparsing import parse_using_clause
from openad_tools.output import output_text, output_error, output_success

# Plugin
from openad_plugin_rxn.plugin_msg import msg
from openad_plugin_rxn.plugin_login import RXNLoginManager
from openad_plugin_rxn.plugin_params import PLUGIN_KEY

spinner_msg = [
    "",
    "this may take a minute",
    "Working on it",
    "Still working",
    "Hang tight",
    "Almost there",
    "Just a moment",
    "Seems like it's taking a while",
    "Apologies for the long wait",
]


class RXNPlugin:
    cmd_pointer = None
    login_manager = None
    api = None

    def __init__(self, cmd_pointer):
        self.cmd_pointer = cmd_pointer

        # Login
        self.login_manager = RXNLoginManager(cmd_pointer)
        self.login_manager.login()

        # Define the RXN API
        self._init_api()

    def _init_api(self):
        if not self.api:
            self.api = self.cmd_pointer.login_settings["client"][
                self.cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
            ]

        # In case you're offline
        if not self.api:
            output_error(msg("err_api_offline"), return_val=False)
            return

    # Utility functions
    # -----------------

    def parse_using_params(self, cmd, default_values):
        """
        Parse the parameters from the USING clause.
        """

        # Parse parameters from the USING clause
        using_params = parse_using_clause(
            cmd.get("using"),
            allowed=default_values.keys(),
        )

        # Assign default parameters
        for key, val in default_values.items():
            if key not in using_params:
                using_params[key] = val

        return using_params

    def get_dataframe_from_file(self, filename: str) -> pd.DataFrame:
        """
        Parse a CSV file and return is as a dataframe.
        """
        try:
            file_path = os.path.join(self.cmd_pointer.workspace_path(), filename)
            df = pd.read_csv(file_path)
            return df
        except FileNotFoundError as err:
            output_error(
                "File not found", "Path should be relative to your workspace", "Path: {filename}", err, return_val=False
            )
        except Exception as err:  # pylint: disable=broad-except
            output_error("Something went wrong", err, return_val=False)

    def get_list_from_txt_file(self, filename: str) -> list:
        """
        Parse TXT file and return the lines as a list.
        """
        try:
            file_path = os.path.join(self.cmd_pointer.workspace_path(), filename)
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()
                return lines
        except FileNotFoundError as err:
            output_error(
                "File not found", "Path should be relative to your workspace", "Path: {filename}", err, return_val=False
            )
        except Exception as err:  # pylint: disable=broad-except
            output_error("Something went wrong", err, return_val=False)

    def validate_reactions_list(self, reactions_list: list) -> bool:
        """
        Check if the reactions in a list are structured correctly.

        Returns False if more reactions are invalid than valid.
        """
        valid, invalid = self._validate_reactions_list(reactions_list)
        if invalid < valid:
            return True
        else:
            output_error(
                [
                    "File contains too many invalid reactions",
                    "Reactions should be one per line, in the format: <smiles>.<smiles>.<smiles>",
                    f"Invalid reactions: {invalid} / {valid + invalid}",
                ],
                return_val=False,
            )
            return False

    def _validate_reactions_list(self, reactions_list: list) -> tuple:
        valid = []
        invalid = []
        for reaction in reactions_list:
            smiles = reaction.split(".")
            smiles = [x for x in smiles if x]
            if len(smiles) > 1:
                valid.append(reaction)
            else:
                invalid.append(reaction)

        return len(valid), len(invalid)

    def get_column_as_list_from_dataframe(self, df, column_name) -> list:
        """
        Check a dataframe for a case-insensitive column name and return the values as a list.
        """
        columns = df.columns
        columns_lowercase = [column.lower() for column in columns]
        if column_name.lower() in columns_lowercase:
            index = columns_lowercase.index(column_name.lower())
            column = columns[index]
            return df[column].tolist()
        else:
            return []

    def get_print_str__reaction(self, reaction_smiles: str, input_smiles: list = None) -> str:
        """
        Get a clean, multiline representation of a reaction for display.

        Parameters
        ----------
        reaction_smiles : str
            The reaction SMILES string:
            AA.BB.CC>>DD
        input_smiles : list, optional
            A list of input SMILES strings, if available.
            - - -
            When predicting reactions, RXN will canonicalize
            your input SMILES, making it hard to tie input and
            output together. In this case, you can pass the
            original input smiles to display instead.

        Input:
            AA.BB.CC>>DD

        Output:
            +  AA
            +  BB
            +  CC
            -------------------------
            => DD
        """

        # Deconstruct
        reaction_in_out = reaction_smiles.split(">>")
        reaction_input = reaction_in_out[0]
        reaction_output = reaction_in_out[1]

        # Note: RXN will canonicalize the input SMILES,
        # making it hard to tie input and output together.
        # Hence, we use the original innput smiles in our
        # reaction display. If we ever want to change that,
        # simply uncomment the block below.

        # # Parse input smiles
        # input_smiles = []
        # for smiles in reaction_input.split("."):
        #     input_smiles.append(smiles)

        # Assemble
        reaction_input_print = "<soft>+</soft>  " + "\n<soft>+</soft>  ".join(input_smiles)
        output = [
            reaction_input_print,
            "   <soft>-------------------------</soft>",
            f"<soft>=></soft> <success>{reaction_output}</success>",
        ]

        # Turn into HTML for Jupyter Notebook
        if GLOBAL_SETTINGS["display"] == "notebook":
            output = "<br>".join(output) + "<br>"
            output = tags_to_markdown(output)
            return output
        else:
            return "\n".join(output)

    def get_print_str_list__confidence(self, confidence):
        """
        Visualize the confidence score.

        Parameters:
            confidence (float): Confidence score between 0 and 1
        """

        output = []

        # Confidence color
        confidence_style_tags = self.get_confidence_style(confidence)
        confidence_color = self.get_confidence_style(confidence, return_color=True)

        # Parse confidence into a percentage
        confidence = round(confidence * 100, 2) if confidence or confidence == 0 else None

        # Output for Jupyter Notebook
        if GLOBAL_SETTINGS["display"] == "notebook":
            # Confidence meter
            confidence_meter = "".join(
                [
                    "<div style='width:300px;height:5px;background:#eee;'>",
                    f"<div style='background:{confidence_color};width:{confidence * 3}px;height:100%;'></div>",
                    "</div>",
                ]
            )

            # Confidence score in text
            confidence_str = (
                f"<span style='color:{confidence_color}'>{confidence}%</span> <span style='color:#ccc'>confidence</span>"
                if confidence
                else "<span style='color:#ccc'>Confidence: n/a</span>"
            )

            # Assemble
            output = [
                confidence_meter,
                confidence_str,
            ]

        # Output for CLI
        else:
            # Confidence meter
            confidence_meter = ["━" for _ in range(24)]
            if round(confidence / 4) > 0:
                confidence_meter.insert(0, confidence_style_tags[0])
                if confidence == 100:
                    confidence_meter.append("━" + confidence_style_tags[1])
                else:
                    confidence_meter.insert(round(confidence / 4), "╸" + confidence_style_tags[1])
            confidence_meter = "<soft>" + "".join(confidence_meter) + "</soft>"

            # Confidence score in text
            confidence_str = str(confidence).rstrip("0").rstrip(".") if confidence else None
            confidence_str = (
                f"{confidence_style_tags[0]}{confidence_str}%{confidence_style_tags[1]} <soft>confidence</soft>"
                if confidence
                else "<soft>Confidence: n/a</soft>"
            )

            # Assemble
            output = [
                confidence_meter,
                confidence_str,
            ]

        return output

    def get_confidence_style(self, confidence, return_color=False):
        """
        Return the appropriate style tags and color for a confidence score.

        Parameters
        ----------
        confidence : float
            The confidence score between 0 and 1.

        Returns
        -------
        tuple:
            confidence_style_tags, confidence_color
        """

        # Unknown confidence
        if confidence is None:
            if return_color:
                return "#ccc"
            else:
                return ["<soft>", "</soft>"]

        # High - green
        if confidence > 0.9:
            if return_color:
                return "#090"
            else:
                return ["<green>", "</green>"]

        # Medium - yellow
        if confidence > 0.5:
            if return_color:
                return "#dc0"
            else:
                return ["<yellow>", "</yellow>"]

        # Low - red
        else:
            if return_color:
                return "#d00"
            else:
                return ["<red>", "</red>"]

    def get_flag(self, flag_text: str, trim: bool = False) -> str:
        """
        Turns a flag text into a styled flag for display.
        """
        flag_text = flag_text.upper()
        output = ""

        # Simple text flag for Jupyter Notebook
        if GLOBAL_SETTINGS["display"] == "notebook":
            output = f"<span style='opacity:.3'> - [ {flag_text} ]</span>"

        # SUCCESS
        if flag_text == "SUCCESS":
            output = f" <success> {flag_text} </success>"

        # FAILED
        if flag_text == "FAILED":
            output = f" <on_red> {flag_text} </on_red>"

        # CACHED / anything else
        output = f" <reverse> {flag_text} </reverse>"

        # Trim leading whitespace if required
        if trim:
            output = output.strip()

        return output

    def homogenize_smiles(self, smiles_list: list) -> str:
        """
        Sort and join a list of smiles so it can be compared.
        """
        smiles_list.sort()
        return ".".join(smiles_list)

    # Caching
    # -------

    def store_result_cache(self, name, key, payload) -> bool:
        """
        Save a result to the cache.

        /<workspace>/._openad/rxn_cache/rxn-<func_name>-<model_name>--<input_smiles>.result
        /<workspace>/._openad/rxn_cache/rxn-<func_name>-<model_name>-topn-<int>--<input_smiles>.result
        """
        try:
            filename = f"rxn-{name}--{key}.result"
            if len(filename) > 256:
                output_text("<soft>Result not cached, too complex</soft>")
                return
            cache_dir = self._get_cache_dir()
            with open(os.path.join(cache_dir, filename), "wb") as handle:
                pickle.dump({"payload": payload}, handle)
            return True
        except Exception as err:  # pylint: disable=broad-except
            output_error(["Failed to save result as cache", f"Data: {payload}", err], return_val=False)
            return False

    def retrieve_result_cache(self, name, key):
        """
        Retrieve result from the cache.
        """
        try:
            filename = f"rxn-{name}--{key}.result"
            cache_dir = self._get_cache_dir()
            with open(os.path.join(cache_dir, filename), "rb") as handle:
                result = pickle.load(handle)
            return result.get("payload")
        except Exception:  # pylint: disable=broad-except
            return False

    def clear_cache(self):
        """
        Clear the cache directory.
        """
        cache_dir = self._get_cache_dir()
        for file in os.listdir(cache_dir):
            os.remove(os.path.join(cache_dir, file))
        output_success("All cache files cleared", return_val=False)

    def _get_cache_dir(self):
        """
        Get the cache directory, create if it doesn't exist yet.
        """
        cache_dir = os.path.join(self.cmd_pointer.workspace_path(), "._openad", "rxn_cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
