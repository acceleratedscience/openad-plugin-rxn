from rdkit import Chem
from time import sleep
from rdkit.Chem import AllChem
from rdkit.Chem.Draw import rdMolDraw2D
from IPython.display import display, HTML

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.smols.smol_functions import canonicalize, valid_smiles
from openad.helpers.spinner import spinner
from openad.helpers.output import output_text, output_error
from openad.plugins.style_parser import tags_to_markdown


# Plugin
from openad_plugin_rxn.plugin_params import PLUGIN_KEY
from openad_plugin_rxn.rxn_helper import RXNHelper

rxn_helper = RXNHelper()

USING_PARAMS_DEFAULTS = {
    "ai_model": "2020-08-10",
    "topn": 10,
}


def predict_reactions(cmd_pointer, cmd: dict):
    """Predicts Reactions in Batch from a list of Reaction Smiles Strings"""

    # Define the RXN API
    api = cmd_pointer.login_settings["client"][cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)]

    # Setup
    rxn_helper.sync_up_workspace_name(cmd_pointer)
    rxn_helper.get_current_project(cmd_pointer)

    # Parse command
    reactions_list = _parse_reactions_list(cmd_pointer, cmd)
    using_params = rxn_helper.parse_using_params(cmd, USING_PARAMS_DEFAULTS)
    no_cache = bool(cmd.get("no_cache"))

    # Set aside reactions that are invalid or cached
    reactions_to_be_skipped = _verify_reactions(cmd_pointer, using_params, no_cache, reactions_list)
    invalid_reactions_print_str = reactions_to_be_skipped.get("invalid_reactions_print_str", {})
    cached_reactions_print_str = reactions_to_be_skipped.get("cached_reactions_print_str", {})
    cached_reactions = reactions_to_be_skipped.get("cached_reactions", {})
    skip_count = reactions_to_be_skipped.get("count", {})

    # Run reaction query
    # ------------------
    if skip_count < len(reactions_list):
        # Sanitize the reaction list so invalid
        # reactions won't break the API call
        reactions_list_sanitized = [
            reaction for reaction in reactions_list if reaction not in invalid_reactions_print_str
        ]

        # Step 1 - Lauch the query & create task id
        task_id = _api_get_task_id(api, reactions_list_sanitized)
        if not task_id:
            return

        # Step 2 - Get the reaction results
        reaction_predictions = _api_get_results(api, task_id)
        if not reaction_predictions:
            return

        # Insert None values in the reaction_predictions list
        # at the same index where the invalid reactions were,
        # so indices match between reactions_list and reaction_predictions
        for reaction in reactions_list:
            if reaction in invalid_reactions_print_str:
                reaction_predictions.insert(reactions_list.index(reaction), None)

    # Loop through reaction results and assemble output print string
    for i, reaction in enumerate(reactions_list):
        # PRINT REACTION - INVALID REACTIONS
        if reaction in invalid_reactions_print_str:
            _display_reaction(None, invalid_reactions_print_str[reaction])
            continue

        # PRINT REACTION - CACHED REACTIONS
        if reaction in cached_reactions:
            prediction = cached_reactions[reaction]
            _display_reaction(prediction, cached_reactions_print_str[reaction])
            continue

        # Get newly generated prediction data
        prediction = reaction_predictions[i]

        # Save results as analysis records that can be merged
        # with the molecule working set in a follow up comand:
        # `enrich mols with analysis`
        input_smiles = reaction.split(".")
        input_smiles_key = rxn_helper.homogenize(input_smiles)
        rxn_helper.store_result_cache(
            cmd_pointer,
            name=f"predict-reaction-{using_params.get('ai_model')}",
            key=input_smiles_key,
            payload=prediction,
        )
        # RXN returns canonicalized smiles, so we create an additional
        # cache record with the rxn-canonicalized smiles as key.
        prediction_smiles = prediction.get("smiles", "").split(">>")[0].split(".")
        prediction_smiles_key = rxn_helper.homogenize(prediction_smiles)
        rxn_helper.store_result_cache(
            cmd_pointer,
            name=f"predict-reaction-{using_params.get('ai_model')}",
            key=prediction_smiles_key,
            payload=prediction,
        )

        # PRINT REACTION - NEWLY GENERATED REACTIONS
        index = i + 1 if len(reactions_list) > 1 else None  # Ignore index for single reaction
        header_print_str = _print_str__header(index)
        reaction_print_str = _print_str__reaction(input_smiles, prediction["smiles"])
        confidence_print_str = _print_str__confidence(prediction["confidence"])
        print_str = "\n".join([header_print_str, reaction_print_str, confidence_print_str])

        _display_reaction(prediction, print_str)

    if GLOBAL_SETTINGS["display"] == "api":
        return reaction_predictions["predictions"]


def _get_reaction_image(reaction_smiles: str) -> Chem.rdChemReactions.ChemicalReaction:
    """
    Fetch reaction image from a smiles reaction string, for Jupyter Notebook.

    Parameters
    ----------
    reaction_smiles : str
        Reaction smiles string
        Format: smiles.smiles.smiles>>smiles
        Example: BrBr.OCCc1cccc2cc3ccccc3cc12>>BrCCc1cccc2c(Br)c3ccccc3cc12
    """
    reaction = AllChem.ReactionFromSmarts(reaction_smiles, useSmiles=True)

    # Set drawing options
    width, height = 800, 200
    draw_options = rdMolDraw2D.MolDrawOptions()
    draw_options.bondLineWidth = 1.0

    # Create drawer
    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)  # Width and height in pixels
    drawer.SetDrawOptions(draw_options)

    # Draw reaction
    drawer.DrawReaction(reaction)
    drawer.FinishDrawing()
    svg = drawer.GetDrawingText()

    return svg


def _parse_reactions_list(cmd_pointer, cmd):
    """
    Parse the reactions list from the command.
    """
    from_list = []

    # Form string
    if cmd.get("from_str"):
        from_list = [cmd.get("from_str")]

    # From file
    elif cmd.get("from_file"):
        react_frame = rxn_helper.get_dataframe_from_file(cmd_pointer, cmd.get("from_file"))
        from_list = rxn_helper.get_column_as_list_from_dataframe(react_frame, "reactions")
        if not from_list:
            return output_error("No Provided reactions, file should have column 'reactions'")

    # From dataframe
    elif cmd.get("from_dataframe"):
        react_frame = cmd_pointer.api_variables[cmd["from_dataframe"]]
        from_list = rxn_helper.get_column_as_list_from_dataframe(react_frame, "reactions")
        if not from_list:
            return output_error("No Provided reactions, data frame should have column 'reactions'")

    # From list
    elif cmd.get("from_list"):
        from_list = cmd["from_list"]

    return from_list


def _print_str__header(index: int = None, flag: str = "", html: bool = False):
    """
    Get the header for a single reaction print.
    """

    # Index
    index_str = " Result" if index is None else f" #{index}"

    # Flag
    if flag == "cached":
        flag = (
            "<span style='opacity:.3'> - [ CACHED ]</span>"
            if GLOBAL_SETTINGS["display"] == "notebook"
            else " <reverse> CACHED </reverse>"
        )
    elif flag == "failed":
        flag = (
            "<span style='color:#d00'> - [ FAILED ]</span>"
            if GLOBAL_SETTINGS["display"] == "notebook"
            else " <on_red> FAILED </on_red>"
        )

    # Assemble for Jupyter Notebook
    if GLOBAL_SETTINGS["display"] == "notebook":
        output = [f"<h3><u>Reaction{index_str}</u>{flag}</h3>"]

    # Assemble for CLI
    else:
        output = [
            f"<yellow>Reaction{index_str}</yellow>{flag}",
            "————————————————————————————",
        ]

    return "\n".join(output)


def _print_str__reaction(input_smiles: list, reaction_smiles: str):
    """
    Get a clean, multiline string representation of a reaction.

    Input:
        AA.BB.CC>>DD

    Output:
        +  AA
        +  BB
        +  CC
           -------------------------
        => DD
    """

    # Deconstruct
    reaction_in_out = reaction_smiles.split(">>")
    reaction_input = reaction_in_out[0]
    reaction_output = reaction_in_out[1]

    # Note: RXN will canonicalize the input SMILES,
    # making it hard to tie input and output together.
    # Hence, we use the original innput smiles in our
    # reaction display. If we ever want to change that,
    # simply uncomment the block below.

    # # Parse input smiles
    # input_smiles = []
    # for smiles in reaction_input.split("."):
    #     input_smiles.append(smiles)

    # Assemble
    reaction_input_print = "<soft>+</soft>  " + "\n<soft>+</soft>  ".join(input_smiles)
    output = [
        reaction_input_print,
        "   <soft>-------------------------</soft>",
        f"<soft>=></soft> <success>{reaction_output}</success>",
    ]

    # Turn into HTML for Jupyter Notebook
    if GLOBAL_SETTINGS["display"] == "notebook":
        output = "<br>".join(output) + "<br>"
        output = tags_to_markdown(output)
        return output
    else:
        return "\n".join(output)


def _print_str__reaction_invalid(input_smiles: list, invalid_smiles: list):
    """
    Get a clean, multiline string representation of an invalid reaction.

    Input:
        ['AA', 'BB', 'CC']
        ['BB']

    Output:
        +  AA
        +  Invalid: BB
        +  CC
           ------------
        => Skipped due to invalid SMILES
    """

    # Mark valid/invalid smiles
    for i, smiles in enumerate(input_smiles):
        input_smiles[i] = f"<error>✖ {smiles}</error>" if smiles in invalid_smiles else f"<success>✔</success> {smiles}"

    # Assemble
    reaction_input_print = "<soft>+</soft>  " + "\n<soft>+</soft>  ".join(input_smiles)
    output = [
        reaction_input_print,
        "   <soft>-------------------------</soft>",
        "<soft>=> Skipped due to invalid SMILES</soft>",
    ]

    # Turn into HTML for Jupyter Notebook
    if GLOBAL_SETTINGS["display"] == "notebook":
        output = "<br>".join(output) + "<br>"
        output = tags_to_markdown(output)
        return output
    else:
        return "\n".join(output)


def _print_str__confidence(confidence):
    """
    Visualize the confidence score.

    Parameters:
        confidence (float): Confidence score between 0 and 1
    """

    # Parse confidence
    confidence = round(confidence * 100, 2) if confidence or confidence == 0 else None

    # fmt: off
    confidence_style = (
        ["<soft>", "</soft>", "#ccc"] if confidence is None
        else ["<green>","</green>", "#090"] if confidence > 90
        else ["<yellow>","</yellow>", "#dc0"] if confidence > 70
        else ["<reset>","</reset>", "#333"] if confidence > 50
        else ["<red>","</red>", "#d00"]
    )
    # fmt: on

    # Output for Jupyter Notebook
    if GLOBAL_SETTINGS["display"] == "notebook":
        # Confidence meter
        confidence_meter = "".join(
            [
                "<div style='width:300px;height:5px;background:#eee;'>",
                f"<div style='background:{confidence_style[2]};width:{confidence * 3}px;height:100%;'></div>",
                "</div>",
            ]
        )

        # Confidence score in text
        confidence_str = (
            f"<span style='color:{confidence_style[2]}'>{confidence}%</span> <span style='color:#ccc'>confidence</span>"
            if confidence
            else "<span style='color:#ccc'>Confidence: n/a</span>"
        )

        # Assemble
        output = [
            confidence_meter,
            confidence_str,
        ]
        return "".join(output)

    # Output for CLI
    else:
        # Confidence meter
        confidence_meter = ["━" for _ in range(24)]
        confidence_meter.insert(0, confidence_style[0])
        confidence_meter.insert(round(confidence / 4), "╸" + confidence_style[1])
        confidence_meter = "   <soft>" + "".join(confidence_meter) + "</soft>"

        # Confidence score in text
        confidence_str = str(confidence).rstrip("0").rstrip(".") if confidence else None
        confidence_str = (
            f"   {confidence_style[0]}{confidence_str}%{confidence_style[1]} <soft>confidence</soft>"
            if confidence
            else "   <soft>Confidence: n/a</soft>"
        )

        # Assemble
        output = [
            confidence_meter,
            confidence_str,
            # "   -------------------------",
        ]
        return "\n".join(output)


def _api_get_task_id(api, reactions_list):
    """
    Launch a query and return the task ID.
    """
    retries = 0
    max_retries = 5
    try_again = True
    predict_reaction_batch_response = None
    while try_again is True:
        try:
            if retries == 0:
                spinner.start("Starting prediction")
            else:
                spinner.start(f"Starting prediction - retry #{retries}")

            # raise Exception("This is a test error")
            predict_reaction_batch_response = api.predict_reaction_batch(reactions_list)
            if not predict_reaction_batch_response:
                raise ValueError("Empty response from the server (get task_id)")
            if not predict_reaction_batch_response.get("task_id"):
                raise ValueError("No task_id returned")
            try_again = False

        except Exception as err:  # pylint: disable=broad-exception-caught
            sleep(2)
            retries = retries + 1
            if retries > max_retries:
                spinner.stop()
                output_error([f"Server unresponsive after {max_retries} retries", err], return_val=False)
                return False

    task_id = predict_reaction_batch_response.get("task_id")
    spinner.stop()
    output_text(f"<yellow>Task id:</yellow> <soft>{task_id}</soft>", return_val=False)
    return task_id


def _api_get_results(api, task_id):
    """
    Check on the status of a query and return the results.
    """
    retries = 0
    max_retries = 10
    try_again = True
    reaction_predictions = None
    while try_again is True:
        try:
            if retries == 0:
                spinner.start("Processing prediction")
            else:
                spinner.start(f"Processing prediction - retry #{retries}")

            # raise Exception("This is a test error")
            reaction_predictions = api.get_predict_reaction_batch_results(task_id)
            # print(11, f"--{task_id}--", reaction_predictions)
            if not reaction_predictions:
                raise ValueError("Empty response from the server (get reactions)")
            if not reaction_predictions.get("predictions"):
                raise ValueError("No predictions returned")
            try_again = False

        except Exception as err:  # pylint: disable=broad-exception-caught
            sleep(2)
            retries = retries + 1
            if retries > max_retries:
                spinner.stop()
                output_error([f"Server unresponsive after {max_retries} retries", err], return_val=False)
                return False

    spinner.succeed("Done")
    return reaction_predictions.get("predictions")


def _verify_reactions(cmd_pointer, using_params, no_cache, reactions_list):
    """
    Loop through reactions and store the ones that are either invalid or cached.
    """

    # Storage for invalid reactions and cached reactions
    invalid_reactions_print_str = {}
    cached_reactions_print_str = {}
    cached_reactions = {}

    # Loop
    for i, reaction in enumerate(reactions_list):
        # Ignore index for single reaction
        index = i + 1 if len(reactions_list) > 1 else None

        # Check for invalid SMILES
        input_smiles = reaction.split(".")
        invalid_smiles = []
        for smiles in input_smiles:
            if not valid_smiles(smiles):
                invalid_smiles.append(smiles)

        # REACTION IS INVALID --> store print str output
        if len(invalid_smiles) > 0:
            header_print_str = _print_str__header(index, flag="failed")
            reaction_print_str = _print_str__reaction_invalid(input_smiles, invalid_smiles)
            invalid_reactions_print_str[reaction] = "\n".join([header_print_str, reaction_print_str])
            continue

        # Check for cached results
        elif not no_cache:
            input_smiles_key = rxn_helper.homogenize(input_smiles)
            result_from_cache = rxn_helper.retrieve_result_cache(
                cmd_pointer,
                name=f"predict-reaction-{using_params.get('ai_model')}",
                key=input_smiles_key,
            )

            # REACTION IS CACHED --> store print str output
            if result_from_cache:
                header_print_str = _print_str__header(index, flag="cached")
                reaction_print_str = _print_str__reaction(input_smiles, result_from_cache["smiles"])
                confidence_print_str = _print_str__confidence(result_from_cache["confidence"])
                cached_reactions[reaction] = result_from_cache
                cached_reactions_print_str[reaction] = "\n".join(
                    [header_print_str, reaction_print_str, confidence_print_str]
                )
                continue

    return {
        "invalid_reactions_print_str": invalid_reactions_print_str,
        "cached_reactions_print_str": cached_reactions_print_str,
        "cached_reactions": cached_reactions,
        "count": len(invalid_reactions_print_str) + len(cached_reactions_print_str),
    }


def _display_reaction(prediction, print_str):
    """
    Display a reaction in the CLI or Jupyter Notebook.

    Parameters
    ----------
    prediction : dict
        Prediction data for the reaction, as returned by the API eg:
        {
            'confidence': 0.9797950224106948,
            'smiles': 'BrBr.c1ccc2cc3ccccc3cc2c1>>Brc1c2ccccc2cc2ccccc12',
            'photochemical': False,
            'thermal': False
        }
    print_str : str
        String representation of the reaction,
        pre-processed for Jupyter or CLI.
        (see _verify_reactions())
    """

    # Display in Jupyter Notebook
    if GLOBAL_SETTINGS["display"] == "notebook":
        # Open frame
        output = ['<div style="display:inline-block; border:solid 1px #ccc">']

        # Add image
        if prediction:
            output.append(_get_reaction_image(prediction["smiles"]))

        # Wrap text in padded div
        print_str = "<div style='padding: 32px'>" + print_str + "</div>"
        output.append(print_str)

        # Close frame
        output.append("</div>")

        # Print
        output = "".join(output)
        display(HTML(output))

    # Display in CLI
    elif not GLOBAL_SETTINGS["display"] == "api":
        output_text(print_str, pad=2, return_val=False)
