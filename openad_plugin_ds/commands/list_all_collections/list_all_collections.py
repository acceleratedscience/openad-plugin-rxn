import pandas as pd
from datetime import datetime

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.helpers.jupyter import save_df_as_csv
from openad.helpers.general import pretty_nr, pretty_date
from openad.helpers.output import output_text, output_error, output_table

# Plugin
from openad_plugin_ds.plugin_msg import msg as plugin_msg
from openad_plugin_ds.plugin_params import PLUGIN_KEY


def list_all_collections(cmd_pointer, cmd: dict):
    """
    Display all collections.

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
    results_table = [
        {
            "Collection Name": c.name,
            "Collection Key": c.source.index_key,
            "Entries": pretty_nr(c.documents),
            "Domain": " / ".join(c.metadata.domain),
            "Type": c.metadata.type,
            "Created": c.metadata.created.strftime("%Y-%m-%d"),
            "created_timestamp": c.metadata.created,
            "Elastic ID": c.source.elastic_id,
            "Description": c.metadata.description,
        }
        for c in collections
    ]

    # No results found
    # results_table = [] # Keep here for testing
    if not results_table:
        return output_error(plugin_msg("err_no_collections_available"), return_val=False)

    # Print collections table
    df = pd.DataFrame(results_table)
    df = df.fillna("")  # Replace NaN with empty string
    df.pop("Description")  # Remove description column
    df.pop("created_timestamp")  # Remove created_timestamp column

    # Display results in CLI & Notebook
    if GLOBAL_SETTINGS["display"] != "api":

        # Print description of all collections
        if "details" in cmd:
            for collection in results_table:
                print_str = (
                    "\n".join(
                        [
                            f"<h1>{collection['Collection Name']}</h1>",
                            f"{collection['Description']}",
                            "<soft>---</soft>",
                            f"<yellow>Name     </yellow> {collection['Collection Name']}",
                            f"<yellow>Key      </yellow> {collection['Collection Key']}",
                            f"<yellow>Domain   </yellow> {collection['Domain']}",
                            f"<yellow>Type     </yellow> {collection['Type']}",
                            f"<yellow>Entries  </yellow> {collection['Entries']}",
                            f"<yellow>Created  </yellow> {pretty_date(collection['created_timestamp'].timestamp(), 'pretty', time=False)}",
                        ]
                    )
                    + "\n"
                )
                output_text(print_str, return_val=False, edge=True, width=80, pad=1)

        # Print table
        output_table(df, return_val=False)

        # Print command hints to see descriptions
        if "details" not in cmd:
            output_text(
                "\n\n".join(
                    [
                        "To see any particular collection's description, run:\n<cmd>ds list collection details '<collection_name_or_key>'</cmd>",
                        "To see all collections' descriptions at once, run:\n<cmd>ds list all collections details</cmd>",
                    ]
                ),
                pad_btm=1,
                return_val=False,
            )

    # Save results to file (prints success message)
    if "save_as" in cmd:
        results_file = str(cmd["results_file"])
        save_df_as_csv(cmd_pointer, df, results_file)

    # Return data for API
    if GLOBAL_SETTINGS["display"] == "api":
        return df
