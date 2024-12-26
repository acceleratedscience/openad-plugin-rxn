import pandas as pd

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.helpers.jupyter import save_df_as_csv
from openad.helpers.output import output_table, output_error

# Plugin
from openad_plugin_rxn.plugin_params import PLUGIN_KEY

# Plugin
from openad_plugin_rxn.plugin_master_class import RXNPlugin


class ListModels(RXNPlugin):
    """
    List available RXN models.
    """

    def __init__(self, cmd_pointer, cmd: dict):
        """
        Parameters
        ----------
        cmd_pointer:
            The command pointer object
        cmd: dict
            Parser inputs from pyparsing as a dictionary
        """
        super().__init__(cmd_pointer)
        self.cmd = cmd

    def run(self):
        """
        Run the command.
        """

        # Load models
        try:
            all_models = self.api.list_models()
            # raise Exception('This is a test error')
        except Exception as err:  # pylint: disable=broad-exception-caught
            output_error(["Unable to load models", err], return_val=False)
            return

        # Compile results table
        output_models = []
        output_versions = []
        for _model in all_models:
            _versions_list = []
            for version in all_models[_model]:
                _versions_list.append(version["name"])

            output_models.append(_model)
            output_versions.append(_versions_list)
        res_dict = {"Models": output_models, "Versions": output_versions}

        # Convert to DataFrame
        df = pd.DataFrame.from_dict(res_dict)
        df = df.fillna("")  # Replace NaN with empty string

        # Display results in CLI & Notebook
        if GLOBAL_SETTINGS["display"] != "api":

            # Parse list of versions into a string
            df_print = df.copy()
            df_print["Versions"] = df_print["Versions"].apply(
                lambda x: "\n".join(x)  # pylint: disable=unnecessary-lambda
            )

            output_table(df_print, return_val=False)

        # Save results to file (prints success message)
        if "save_as" in self.cmd:
            results_file = str(self.cmd["results_file"])
            save_df_as_csv(self.cmd_pointer, df, results_file)

        # Return data for API
        if GLOBAL_SETTINGS["display"] == "api":
            return df
