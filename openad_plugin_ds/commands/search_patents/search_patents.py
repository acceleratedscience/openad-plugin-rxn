import numpy as np
import pandas as pd

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.smols.smol_cache import create_analysis_record, save_result
from openad.smols.smol_functions import canonicalize, valid_smiles, valid_inchi
from openad.helpers.output_msgs import msg
from openad.helpers.files import save_df_as_csv
from openad.helpers.jupyter import jup_display_input_molecule
from openad.helpers.output import output_success, output_error, output_table

# Plugin
from openad_plugin_ds.plugin_msg import msg as plugin_msg
from openad_plugin_ds.plugin_params import PLUGIN_KEY

# Deep Search
from deepsearch.chemistry.queries.molecules import PatentsWithMoleculesQuery, MolId, MolIdType


def search_patents_containing_molecule(cmd_pointer, cmd: dict):
    """
    Searches for patents that contain mentions of a given molecule.

    Parameters
    ----------
    cmd_pointer
        The command pointer object
    cmd: dict
        Parser inputs from pyparsing as a dictionary
    """

    # Define the DeepSearch API
    api = cmd_pointer.login_settings["toolkits_api"][cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)]

    # Parse identifier
    identifier = cmd["identifier"][0]

    result_type = ""
    resp = None

    # Fetch results from API
    try:
        if valid_smiles(identifier) is True:
            identifier = canonicalize(identifier) or identifier
            query = PatentsWithMoleculesQuery(
                molecules=[MolId(type=MolIdType.SMILES, value=identifier)],
                num_items=20,
            )
            result_type = "SMILES"
        elif valid_inchi(identifier) is True:
            query = PatentsWithMoleculesQuery(
                molecules=[MolId(type=MolIdType.INCHI, value=identifier)],
                num_items=20,
            )
            result_type = "InChI"
        else:
            query = PatentsWithMoleculesQuery(
                molecules=[MolId(type=MolIdType.INCHIKEY, value=identifier)],
                num_items=20,
            )
            result_type = "InChIKey"

        resp = api.queries.run(query)
        # raise Exception('This is a test error')
    except Exception as err:  # pylint: disable=broad-exception-caught
        output_error(plugin_msg("err_deepsearch", err), return_val=False)
        return

    # Compile results
    results_table = []
    for doc in resp.outputs["patents"]:
        result = {"Patent ID": ""}
        for ident in doc["identifiers"]:
            if ident["type"] == "patentid":
                result["Patent ID"] = ident["value"]
        results_table.append(result)

    # No results found
    # results_table = [] # Keep here for testing
    if not results_table:
        return output_error(plugin_msg("err_no_patents_found", result_type, identifier), return_val=False)

    # Success
    output_success(
        plugin_msg("success_patents_found", len(results_table), result_type, identifier), return_val=False, pad_top=1
    )

    df = pd.DataFrame(results_table)
    df = df.fillna("")  # Replace NaN with empty string

    # Save results as analysis records that can be merged
    # with the molecule working set in a follow up comand:
    # `enrich mols with analysis`
    save_result(
        create_analysis_record(
            identifier,
            PLUGIN_KEY,
            "Patents_Containing_Molecule",
            "",
            results_table,
        ),
        cmd_pointer=cmd_pointer,
    )

    # Display image of the input molecule in Jupyter Notebook
    if GLOBAL_SETTINGS["display"] == "notebook":
        jup_display_input_molecule(identifier)

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
