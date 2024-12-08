import pandas as pd

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.smols.smol_cache import create_analysis_record, save_result
from openad.smols.smol_functions import canonicalize, valid_smiles
from openad.helpers.files import save_df_as_csv
from openad.helpers.output import output_success, output_error, output_table
from openad.helpers.jupyter import jup_display_input_molecule

# Plugin
from openad_plugin_ds.plugin_msg import msg as plugin_msg
from openad_plugin_ds.plugin_params import PLUGIN_KEY

# Deep Search
from deepsearch.chemistry.queries.molecules import MoleculeQuery, MolQueryType


def find_similar_molecules(cmd_pointer, cmd):
    """
    Search for molecules similar to a given molecule.

    Parameters
    ----------
    cmd_pointer:
        The command pointer object
    cmd: dict
        Parser inputs from pyparsing as a dictionary
    """

    # Define the DeepSearch API
    api = cmd_pointer.login_settings["toolkits_api"][cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)]

    # Parse identifier
    smiles = cmd["smiles"][0]
    if not valid_smiles(smiles):
        return output_error(plugin_msg("err_invalid_identifier"), return_val=False)
    else:
        canonical_smiles = canonicalize(smiles)

    # Fetch results from API
    try:
        query = MoleculeQuery(
            query=canonical_smiles,
            query_type=MolQueryType.SIMILARITY,
        )

        resp = api.queries.run(query)
        # raise Exception('This is a test error')
    except Exception as err:  # pylint: disable=broad-exception-caught
        output_error(plugin_msg("err_deepsearch", err), return_val=False)
        return False

    # Parse results
    results_table = []
    for row in resp.outputs["molecules"]:
        result = {
            "id": row["persistent_id"],
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

    # No results found
    if not results_table:
        return output_error("No similar molecules found.")

    # Success
    output_success(
        [
            f"We found <yellow>{len(results_table)}</yellow> molecules similar to the provided SMILES.",
            f"Input: {smiles}",
            f"Canonicalized Input: {canonical_smiles}",
        ],
        return_val=False,
        pad_top=1,
    )

    df = pd.DataFrame(results_table)
    df = df.fillna("")  # Replace NaN with empty string

    # Save results as analysis records that can be merged
    # with the molecule working set in a follow up comand:
    # `enrich mols with analysis`
    save_result(
        create_analysis_record(
            canonical_smiles,
            PLUGIN_KEY,
            "Similar_Molecules",
            "",
            results_table,
        ),
        cmd_pointer=cmd_pointer,
    )

    # Display image of the input molecule in Jupyter Notebook
    if GLOBAL_SETTINGS["display"] == "notebook":
        jup_display_input_molecule(canonical_smiles, "smiles")

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
