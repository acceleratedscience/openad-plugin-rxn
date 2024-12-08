import numpy as np
import pandas as pd

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.helpers.files import save_df_as_csv
from openad.helpers.output import output_error, output_table, output_success

# Plugin
from openad_plugin_ds.plugin_msg import msg as plugin_msg
from openad_plugin_ds.plugin_params import PLUGIN_KEY

# Deep Search
from deepsearch.cps.queries import DataQuery
from deepsearch.cps.client.components.queries import RunQueryError

# TQDM progress bar
if GLOBAL_SETTINGS["display"] == "notebook":
    from tqdm.notebook import tqdm
else:
    from tqdm import tqdm


def list_collections_containing(cmd_pointer, cmd: dict):
    """
    Searches all collections for instances a given string.

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

    # Search all collections for the given string, using tqdm to display a progress bar.
    results_table = []
    for c in (pbar := tqdm(collections, total=len(collections), bar_format="{l_bar}{bar}", leave=False)):
        pbar.set_description(f"Querying {c.name}")

        # print(c.metadata.description)

        # Search only on document collections
        if c.metadata.type != "Document":
            continue
        try:
            # Execute the query
            query = DataQuery(cmd["search_query"], source=[""], limit=0, coordinates=c.source)
            query_results = api.queries.run(query)
            if int(query_results.outputs["data_count"]) > 0:
                results_table.append(
                    {
                        "Domain": " / ".join(c.metadata.domain),
                        "Collection Name": c.name,
                        "Collection Key": c.source.index_key,
                        "Matches": query_results.outputs["data_count"],
                    }
                )
            # raise RunQueryError(task_id=1, message="This is a test error", error_type="err123", detail='aaa')
        except RunQueryError as err:
            output_error(plugin_msg("err_deepsearch", err), return_val=False)

            if err.error_type == "RuntimeError":
                # https://github.com/DS4SD/deepsearch-toolkit/blob/5ddfdb70fb5fedd13971e06b88e6930f2f431e45/deepsearch/cps/client/components/queries.py#L111
                if "too_many_nested_clauses" in err.message:
                    output_error(plugin_msg("err_runtime"), return_val=False, pad_top=1)

            return False

    # No results found
    # results_table = [] # Keep here for testing
    if not results_table:
        return output_error(plugin_msg("err_no_matching_collections", cmd["search_query"]), return_val=False)

    # Success
    output_success(
        plugin_msg("success_matching_collections", len(results_table), cmd["search_query"]),
        return_val=False,
        pad_top=1,
    )

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
