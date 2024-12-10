import pandas as pd

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.helpers.general import pretty_nr
from openad.helpers.jupyter import save_df_as_csv
from openad.helpers.output import output_error, output_table

# Plugin
from openad_plugin_ds.plugin_msg import msg as plugin_msg
from openad_plugin_ds.plugin_params import PLUGIN_KEY


def list_collections_for_domain(cmd_pointer, cmd: dict):
    """
    Display all collections from a given DeepSearch domain.

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
        # raise Exception("This is a test error")
    except Exception as err:  # pylint: disable=broad-exception-caught
        return output_error(plugin_msg("err_deepsearch", err))

    # Compile results table
    results_table = [
        {
            "Collection Name": c.name,
            "Collection Key": c.source.index_key,
            "Entries": pretty_nr(c.documents),
            "Domain": " / ".join(c.metadata.domain),
            "Type": c.metadata.type,
            "Created": c.metadata.created.strftime("%Y-%m-%d"),
            "Elastic ID": c.source.elastic_id,
        }
        for c in collections
    ]

    # Parse the requested domain(s)
    domain_list = cmd.get("domain_list") or [cmd.get("domain")]

    # Filter results down to the ones matching requested domain(s)
    filtered_list = []
    if len(domain_list) > 0:
        for x in results_table:
            i = 0
            for y in domain_list:
                if y.upper() in str(x["Domain"]).upper():
                    i = i + 1
            if i > 0:
                filtered_list.append(x)
        results_table = filtered_list

    # No results found
    # results_table = [] # Keep here for testing
    if not results_table:
        return output_error(plugin_msg("err_no_collection_found_by_domain", domain_list))

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
