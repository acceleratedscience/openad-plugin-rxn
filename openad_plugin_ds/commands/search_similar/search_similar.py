# Example command:
# search for similar molecules to 'C1(C(=C)C([O-])C1C)=O'


import pandas as pd
from rdkit import Chem
from IPython.display import display, HTML
from deepsearch.chemistry.queries.molecules import MoleculeQuery
from deepsearch.chemistry.queries.molecules import MolQueryType

# OpenAD tools
from openad.helpers.files import save_df_as_csv
from openad.smols.smol_cache import create_analysis_record, save_result
from openad.smols.smol_functions import valid_smiles
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.helpers.output import output_text, output_success, output_error, output_table
from openad.helpers.output_msgs import msg
from openad.helpers.general import load_tk_module
from openad.smols.smol_functions import canonicalize

# Plugin tools
from openad_plugin_ds.plugin_msg import msg
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY


def search_similar_molecules(cmd_pointer, parser):
    """
    Search for molecules similar to a given molecule.

    Parameters
    ----------
    cmd_pointer:
        The command pointer object
    parser:
        Parser inputs from pyparsing
    """

    # Fetch results from DeepSearch API
    api = cmd_pointer.login_settings["toolkits_api"][cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)]
    smiles = parser.as_dict()["smiles"][0]
    try:
        query = MoleculeQuery(
            query=canonicalize(smiles),
            query_type=MolQueryType.SIMILARITY,
        )

        resp = api.queries.run(query)
        # raise Exception('This is a test error')
    except Exception as err:  # pylint: disable=broad-exception-caught
        output_error(msg("err_deepsearch", err), return_val=False)
        return False

    # Parse results into a table/dataframe
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
    df = pd.DataFrame(results_table)
    df = df.fillna("")  # Replace NaN with empty string

    # Print error/success message
    if len(results_table) == 0:
        return output_error("No similar molecules found.")
    else:
        output_success(
            [
                f"We found <yellow>{len(results_table)}</yellow> molecules similar to the provided SMILES.",
                f"Input: {smiles}",
            ],
            return_val=False,
            pad_top=1,
        )

    # Save results as analysis records that can be merged
    # with the molecule working set in a follow up comand:
    # `enrich mols with analysis`
    save_result(
        create_analysis_record(
            canonicalize(smiles),
            PLUGIN_KEY,
            "Similar_Molecules",
            "",
            results_table,
        ),
        cmd_pointer=cmd_pointer,
    )

    # Jupyter Notebook display
    if GLOBAL_SETTINGS["display"] == "notebook":
        # Display images of the input molecule
        if valid_smiles(smiles):
            try:
                mol_rdkit = Chem.MolFromSmiles(smiles)  # pylint: disable=no-member
                # raise Exception('This is a test error')
            except Exception as err:  # pylint: disable= broad-exception-caught
                output_error(msg("err_rdkit_smiles", err), return_val=False)
                return False

            mol_drawer = Chem.Draw.MolDraw2DSVG(300, 300)  # pylint: disable=no-member
            mol_drawer.DrawMolecule(mol_rdkit)
            mol_drawer.FinishDrawing()
            mol_svg = mol_drawer.GetDrawingText()
            img_html = f'<div style="width:300px; height: 300px; margin: 30px 0; border: solid 1px #ddd; display: inline-block; padding: 32px; position: relative"><div style="position: absolute; top: 8px; left: 8px; font-size: 12px; line-height: 12px; color: #999;">INPUT MOLECULE</div>{mol_svg}</div>'
            display(HTML(img_html))

    # Display results in CLI & Notebook
    output_table(df, return_val=False)

    # Save results to file (prints success message)
    if "save_as" in parser:
        results_file = str(parser["results_file"])
        save_df_as_csv(cmd_pointer, df, results_file)

    # Return data for API
    if GLOBAL_SETTINGS["display"] == "api":
        return df
