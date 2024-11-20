# Example command:
# search for similar molecules to 'C1(C(=C)C([O-])C1C)=O'

import numpy as np
from rdkit.Chem import PandasTools
from rdkit import Chem
import pandas as pd
from deepsearch.chemistry.queries.molecules import MoleculeQuery
from deepsearch.chemistry.queries.molecules import MolQueryType

# OpenAD tools
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


def search_similar_molecules(cmd_pointer, parser: dict):
    """
    Search for molecules similar to a given molecule.

    Parameters
    ----------
    cmd_pointer:
        The command pointer object
    parser:
        Parser inputs from pyparsing
    """

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

    if "save_as" in parser:
        results_file = str(parser["results_file"])
        df = pd.DataFrame(results_table)
        if not results_file.endswith(".csv"):
            results_file = results_file + ".csv"
        df.to_csv(
            cmd_pointer.workspace_path(cmd_pointer.settings["workspace"].upper()) + "/" + results_file, index=False
        )
        df = df.replace(np.nan, "", regex=True)
        output_success(msg("success_file_saved", results_file), return_val=False, pad_top=1)

    output_success(
        [
            f"We found <yellow>{len(results_table)}</yellow> molecules similar to the provided SMILES",
            f"Input: {smiles}",
        ],
        return_val=False,
        pad_top=1,
    )

    # Save analysis result that can be merged with molecule working set
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

    df = pd.DataFrame(results_table)

    if GLOBAL_SETTINGS["display"] == "notebook":
        from IPython.display import display

        if valid_smiles(smiles):
            try:
                smiles_mol = Chem.MolFromSmiles(smiles)  # pylint: disable=no-member
                # raise Exception('This is a test error')
            except Exception as err:  # pylint: disable= broad-exception-caught
                output_error(msg("err_rdkit_smiles", err), return_val=False)
                return False

            mol_img = Chem.Draw.MolToImage(smiles_mol, size=(200, 200))
            display(mol_img)

        PandasTools.AddMoleculeColumnToFrame(df, smilesCol="SMILES")
        col = df.pop("ROMol")
        df.insert(0, col.name, col)
        col = df.pop("SMILES")
        df.insert(1, col.name, col)
        # return output_table(df, is_data=True).data
        return df

    return output_table(df, is_data=True)
