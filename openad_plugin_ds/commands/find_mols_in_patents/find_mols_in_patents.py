import pandas as pd

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.helpers.h_data import col_from_df, csv_to_df
from openad.helpers.jupyter import save_df_as_csv
from openad.helpers.output import output_error, output_table, output_success, output_warning

# Plugin
from openad_plugin_ds.plugin_msg import msg as plugin_msg
from openad_plugin_ds.plugin_params import PLUGIN_KEY

# Deep Search
from deepsearch.chemistry.queries.molecules import MoleculesInPatentsQuery


def find_molecules_in_patents(cmd_pointer, cmd: dict):
    """
    Search for mentions of a given molecules in a list of patents.

    Parameters
    ----------
    cmd_pointer:
        The command pointer object
    cmd: dict
        Parser inputs from pyparsing as a dictionary
    """

    # Define the DeepSearch API
    api = cmd_pointer.login_settings["toolkits_api"][cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)]

    # Parse a list of patent ids from the input
    patent_id_list = None
    if "list" in cmd:
        patent_id_list = cmd["list"]
    elif "filename" in cmd or "df_name" in cmd:
        try:
            if "filename" in cmd:
                df = csv_to_df(cmd_pointer, cmd["filename"])
            else:
                df = cmd_pointer.api_variables[cmd["df_name"]]

            df.columns = df.columns.str.lower()
            patent_id_list = col_from_df(df, "patent id")
            if not patent_id_list:
                patent_id_list = col_from_df(df, "patent_id")
            if not patent_id_list:
                patent_id_list = col_from_df(df, "patentid")
            if not patent_id_list:
                raise ValueError("No patent ID column found (patent id, patent_id, patentid)")
            # raise Exception('This is a test error')
        except FileNotFoundError:
            output_error(plugin_msg("err_file_not_found", cmd["filename"]), return_val=False)
        except Exception as err:  # pylint: disable=broad-exception-caught
            src_type = "file" if "filename" in cmd else "dataframe"
            output_error([plugin_msg("err_no_patent_ids_found", src_type), err], return_val=False)
            return

    # Empty list
    if not patent_id_list:
        return

    # Fetch results from API
    try:
        query = MoleculesInPatentsQuery(
            patents=patent_id_list,
            num_items=20,
        )

        resp = api.queries.run(query)
        # raise Exception('This is a test error')
    except Exception as err:  # pylint: disable=broad-except
        output_error(plugin_msg("err_deepsearch", err), return_val=False)
        return

    # Compile results
    results_table = []
    for row in resp.outputs["molecules"]:
        result = {
            "Id": row["persistent_id"],
            "SMILES": "",
            "InChIKey": "",
            "InChI": "",
        }
        for ref in row["identifiers"]:
            if ref["type"] == "smiles":
                result["SMILES"] = ref["value"]
            if ref["type"] == "inchikey":
                result["InChIKey"] = ref["value"]
            if ref["type"] == "inchi":
                result["InChI"] = ref["value"]
        results_table.append(result)

    # List of patent IDs to print
    patent_list_output = "\n<reset>- " + "\n- ".join(patent_id_list) + "</reset>"

    # No results found
    if not results_table:
        output_warning(
            "No molecules found in the provided patents." + patent_list_output,
            return_val=False,
            pad_top=1,
        )
        return

    # Success
    output_success(
        f"We found {len(results_table)} molecules mentioned in the following patents:" + patent_list_output,
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
