import numpy as np
import pandas as pd

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.helpers.jupyter import save_df_as_csv
from openad.helpers.output import output_error, output_table

# Plugin
from openad_plugin_ds.plugin_msg import msg as plugin_msg
from openad_plugin_ds.plugin_params import PLUGIN_KEY


def list_all_domains(cmd_pointer, cmd: dict):
    """
    Display all available domains.

    Parameters
    ----------
    cmd_pointer : object
        The command pointer object.
    cmd : dict
        The command dictionary.
    """

    # Define the DeepSearch API
    api = cmd_pointer.login_settings["toolkits_api"][cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)]

    # Fetch list of collections
    try:
        collections = api.elastic.list()
        collections.sort(key=lambda c: c.name.lower())
        # raise Exception('This is a test error')
    except Exception as err:  # pylint: disable=broad-exception-caught
        output_error(plugin_msg("err_deepsearch", err), return_val=False)
        return False

    # Compile results table
    results_table = []
    _domains = []
    for c in collections:
        for domain in c.metadata.domain:
            if domain not in _domains:
                _domains.append(domain)
                results_table.append({"Domain": domain, "Collections": 1})
            else:
                for x in results_table:
                    if x["Domain"] == domain:
                        x["Collections"] = x["Collections"] + 1

    # No results found
    # results_table = [] # Keep here for testing
    if not results_table:
        return output_error(plugin_msg("no_collection_found_by_domain"), return_val=False)

    df = pd.DataFrame(results_table)
    df = df.fillna("")  # Replace NaN with empty string

    # Display results in CLI & Notebook
    if GLOBAL_SETTINGS["display"] != "api":
        output_table(df, return_val=False)

    # Save results to file (prints success message)
    if "save_as" in cmd:
        results_file = str(cmd["results_file"])
        save_df_as_csv(cmd_pointer, df, results_file)

    # Return data for API
    if GLOBAL_SETTINGS["display"] == "api":
        return df
