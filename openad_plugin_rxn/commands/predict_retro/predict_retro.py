# TO DO: set defaults
# # Variables
# val = "val"
# availability_pricing_threshold = 0
# available_smiles = None
# exclude_smiles = None
# exclude_substructures = None
# exclude_target_molecule = True
# fap = 0.6
# max_steps = 5
# nbeams = 10
# pruning_steps = 2
# ai_model = "2020-07-01"

import py3Dmol
from rdkit import Chem
from time import sleep
from rdkit.Chem import AllChem
from IPython.display import display

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.smols.smol_cache import create_analysis_record, save_result
from openad.smols.smol_functions import canonicalize, valid_smiles
from openad.helpers.spinner import spinner
from openad.helpers.output import output_text, output_error, output_success
from openad.helpers.jupyter import jup_display_input_molecule, parse_using_clause

# Plugin
from openad_plugin_rxn.plugin_params import PLUGIN_KEY
from openad_plugin_rxn.rxn_helper import RXNHelper

rxn_helper = RXNHelper()

USING_PARAMS_DEFAULTS = {
    "availability_pricing_threshold": 0,
    "available_smiles": None,
    "exclude_smiles": None,
    "exclude_substructures": None,
    "exclude_target_molecule": True,
    "fap": 0.6,
    "max_steps": 5,
    "nbeams": 10,
    "pruning_steps": 2,
    "ai_model": "2020-07-01",
}


def _collect_reactions_from_retrosynthesis(tree: dict) -> list[str]:
    """
    Collect all reactions from the retrosynthesis tree.
    """

    reactions = []
    if tree.get("children", []):
        smiles_input = ".".join([node["smiles"] for node in tree["children"]])
        smiles_output = tree["smiles"]
        reactions.append(
            AllChem.ReactionFromSmarts(f"{smiles_input}>>{smiles_output}", useSmiles=True)  # pylint: disable=no-member
        )

    # Loop recursively
    for node in tree["children"]:
        reactions.extend(_collect_reactions_from_retrosynthesis(node))

    return reactions


def _collect_reactions_from_retrosynthesis_text(tree: dict) -> list[str]:
    """
    Collect all reactions from retrosynthesis tree
    """

    # print(tree)

    reactions = []
    if tree.get("children", []):
        smiles_input = " + ".join([node["smiles"] for node in tree["children"]])
        smiles_output = tree["smiles"]
        reactions.append(f"{smiles_input} --->> {smiles_output}")

    # Loop recursively
    for node in tree["children"]:
        reactions.extend(_collect_reactions_from_retrosynthesis_text(node))

    return reactions


def spinner_countdown(s):
    spinner.start(f"Waiting {s}s before retrying")
    sleep(1)
    if s > 1:
        spinner_countdown(s - 1)
    else:
        spinner.stop()
        return True


def predict_retro(cmd_pointer, cmd: dict):
    """
    Perform RXN retrosynthesis prediction.

    Parameters
    ----------
    cmd_pointer:
        The command pointer object
    cmd: dict
        Parser inputs from pyparsing as a dictionary
    """

    # Setup
    rxn_helper.sync_up_workspace_name(cmd_pointer)
    rxn_helper.get_current_project(cmd_pointer)

    # Error messages
    err_msg_unknown = "Something went wrong"
    err_unresponsive_retries = "Server unresponsive, failed after 10 retries"
    err_msg_process_fail = "Failed to process"

    # Define the RXN API
    api = cmd_pointer.login_settings["client"][cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)]

    # Parse input SMILES
    input_smiles = cmd.get("smiles", [None])[0]
    if not input_smiles or not valid_smiles(input_smiles):
        return output_error(["Provided SMILES is invalid", f"Input SMILES: '{input_smiles}'"])
    input_smiles = canonicalize(input_smiles)

    # Make sure input SMILES is not a reaction
    if len(input_smiles.split(".")) > 1:
        return output_error(
            "Provided SMILES describes a reaction. Run <cmd>rxn predict reaction ?</cmd> to see how to predict reactions instead."
        )

    # Display image of the input molecule in Jupyter Notebook
    if GLOBAL_SETTINGS["display"] == "notebook":
        jup_display_input_molecule(input_smiles, "smiles")

    # Parse parameters from the USING clause
    using_params = rxn_helper.parse_using_params(cmd, USING_PARAMS_DEFAULTS)

    print(55, using_params)

    # STEP 1: Predict retrosynthesis
    # ------------------------------

    # Run query - retry up to 10 times upon fail
    retries = 0
    max_retries = 10
    status = False
    predict_retro_response = None
    while status is False:
        try:
            if retries == 0:
                spinner.start("Starting retrosynthesis")
            else:
                spinner.start(f"Starting retrosynthesis - retry #{retries}")

            # raise Exception("This is a test error")

            # Run query
            predict_retro_response = api.predict_automatic_retrosynthesis(
                input_smiles,
                availability_pricing_threshold=using_params.get("availability_pricing_threshold"),
                available_smiles=using_params.get("available_smiles"),
                exclude_smiles=using_params.get("exclude_smiles"),
                exclude_substructures=using_params.get("exclude_substructures"),
                exclude_target_molecule=using_params.get("exclude_target_molecule"),
                fap=using_params.get("fap"),
                max_steps=using_params.get("max_steps"),
                nbeams=using_params.get("nbeams"),
                pruning_steps=using_params.get("pruning_steps"),
                ai_model=using_params.get("ai_model"),
            )
            status = True

        # Fail - failed to connect
        except Exception as err:  # pylint: disable=broad-exception-caught
            sleep(2)
            retries = retries + 1
            if retries > max_retries:
                spinner.stop()
                return output_error([err_unresponsive_retries, err])

    # Fail - empty response
    if not predict_retro_response or not predict_retro_response.get("response", {}).get("payload"):
        spinner.stop()
        return output_error(["The server returned an empty response", predict_retro_response])

    # Fail - error from RXN
    rxn_error_msg = predict_retro_response.get("response", {}).get("payload", {}).get("errorMessage")
    if rxn_error_msg:
        return output_error(rxn_error_msg)

    print(103, "\n", predict_retro_response)

    retries = 0
    status = "NEW"
    previous_status = status
    predict_automatic_retrosynthesis_results = None
    while status != "SUCCESS":
        try:
            if status != previous_status:
                spinner.start("Processing retrosynthesis: " + status)
                previous_status = status

            predict_automatic_retrosynthesis_results = api.get_predict_automatic_retrosynthesis_results(
                predict_retro_response["prediction_id"]
            )
            if not predict_retro_response or not predict_retro_response.get("response", {}).get("payload"):
                output_error("Unable to find path for <yellow>{input_smiles}</yellow>", return_val=False)
                return
            status = predict_automatic_retrosynthesis_results["status"]
            sleep(5)

        except Exception as err:  # pylint: disable=broad-exception-caught
            if retries < 20:
                retries = retries + 1
                status = "Waiting"
                spinner_countdown(15)
            else:
                return output_error(
                    [
                        "Server unresponsive",
                        f"Unable to complete processing for prediction id <yellow>{predict_retro_response['prediction_id']}</yellow> after 20 retries",
                        f"Error: {err}",
                    ]
                )

    # print(222, "\n", predict_automatic_retrosynthesis_results)

    # STEP 2: Process results
    # -----------------------

    reactions_text = []
    try:
        for index, tree in enumerate(predict_automatic_retrosynthesis_results["retrosynthetic_paths"]):
            # print("outer")
            for reaction in _collect_reactions_from_retrosynthesis_text(tree):
                reactions_text.append(str(reaction))
                # print("inner")

    except Exception as err:  # pylint: disable=broad-exception-caught
        spinner.fail(err_msg_process_fail)
        output_error(
            ["Error while processing results: ", err],
            return_val=False,
        )
        return

    # Step 3: Display results
    # -----------------------

    num_results = 0
    try:
        spinner.succeed("Finished processing")
        results = {}
        i = 0
        for index, tree in enumerate(predict_automatic_retrosynthesis_results["retrosynthetic_paths"]):
            num_results = num_results + 1
            if num_results < 4 or GLOBAL_SETTINGS["VERBOSE"] == False:
                results[str(index)] = {"confidence": tree["confidence"], "reactions": []}

            output_text(
                f"Showing path <yellow>{index}</yellow> with confidence <yellow>{tree['confidence']}</yellow>",
                return_val=False,
            )

            for reaction in _collect_reactions_from_retrosynthesis(tree):
                if num_results < 4 or GLOBAL_SETTINGS["VERBOSE"] == False:
                    results[str(index)]["reactions"].append(reactions_text[i])
                output_success(f"Reaction: {reactions_text[i]}", return_val=False)
                i = i + 1
                if GLOBAL_SETTINGS["display"] == "notebook":
                    display(Chem.Draw.ReactionToImage(reaction))

        # Save results as analysis records that can be merged
        # with the molecule working set in a follow up comand:
        # `enrich mols with analysis`
        save_result(
            create_analysis_record(
                input_smiles,
                PLUGIN_KEY,
                "Predict_Retrosynthesis",
                using_params,
                results,
            ),
            cmd_pointer=cmd_pointer,
        )

    except Exception as err:  # pylint: disable=broad-exception-caught
        output_error(["Error while displaying results: ", err], return_val=False)
        return
    i = 0

    if GLOBAL_SETTINGS["display"] == "api":
        return results


# def _get_reaction_image(reaction_smiles: str) -> Chem.rdChemReactions.ChemicalReaction:
#     """
#     Get a reaction's image
#     """
#     return AllChem.ReactionFromSmarts(reaction_smiles, useSmiles=True)  # pylint: disable=no-member


# # Variables
# val = "val"
# availability_pricing_threshold = 0
# available_smiles = None
# exclude_smiles = None
# exclude_substructures = None
# exclude_target_molecule = True
# fap = 0.6
# max_steps = 5
# nbeams = 10
# pruning_steps = 2
# ai_model = "2020-07-01"

# if "availability_pricing_threshold" in cmd:
#     availability_pricing_threshold = int(cmd["availability_pricing_threshold"][val])
#     result_parameters["availability_pricing_threshold"] = availability_pricing_threshold
# if "available_smiles" in cmd:
#     available_smiles = cmd["available_smiles"][val]
#     result_parameters["available_smiles"] = available_smiles
# if "exclude_smiles" in cmd:
#     exclude_smiles = cmd["exclude_smiles"][val]
#     result_parameters["exclude_smiles"] = exclude_smiles
# if "exclude_substructures" in cmd:
#     exclude_substructures = cmd["exclude_substructures"][val]
#     result_parameters["exclude_substructures"] = exclude_substructures
# if "exclude_target_molecule" in cmd:
#     if cmd["exclude_substructures"][val].upper() == "TRUE":
#         exclude_target_molecule = True
#         result_parameters["exclude_target_molecule"] = exclude_target_molecule
# if "fap" in cmd:
#     fap = float(cmd["fap"][val])
#     result_parameters["fap"] = fap
# if "max_steps" in cmd:
#     max_steps = int(cmd["max_steps"][val])
#     result_parameters["max_steps"] = max_steps
# if "nbeams" in cmd:
#     nbeams = int(cmd["nbeams"][val])
#     result_parameters["nbeams"] = nbeams
# if "pruning_steps" in cmd:
#     pruning_steps = int(cmd["pruning_steps"][val])
#     result_parameters["pruning_steps"] = pruning_steps
# if "ai_model" in cmd:
#     ai_model = cmd["ai_model"][val]
#     result_parameters["ai_model"] = ai_model


# Render 3D molecule
# style = "stick"
# mol = Chem.MolFromSmiles(input_smiles)  # pylint: disable=no-member
# mol = Chem.AddHs(mol)  # pylint: disable=no-member
# AllChem.EmbedMolecule(mol)  # pylint: disable=no-member
# AllChem.MMFFOptimizeMolecule(mol, maxIters=200)  # pylint: disable=no-member
# mblock = Chem.MolToMolBlock(mol)  # pylint: disable=no-member

# view = py3Dmol.view(width=700, height=500)
# view.addModel(mblock, "mol")
# view.setStyle({style: {}})
# view.zoomTo()
# view.show()
# output_text("<green>Target Molecule:</green> " + input_smiles, return_val=False)
