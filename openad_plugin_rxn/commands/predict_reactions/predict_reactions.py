from time import sleep
from rdkit.Chem import AllChem
from rdkit.Chem.Draw import rdMolDraw2D
from IPython.display import display, HTML

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.smols.smol_functions import valid_smiles
from openad.helpers.spinner import spinner
from openad.helpers.output import output_text, output_error
from openad.plugins.style_parser import tags_to_markdown


# Plugin
from openad_plugin_rxn.plugin_params import PLUGIN_KEY
from openad_plugin_rxn.rxn_helper import RXNPlugin


class PredictReactions(RXNPlugin):
    """
    Predict reactions using the RXN api.

    Consumes a pyparsing dictionary with either:
    - A single reaction
    - A list of reactions
    - A txt or csv file containing a list of reactions
    - A dataframe containing a list of reactions.

    For example:
    { 'from_str': 'BrBr.c1ccc2cc3ccccc3cc2c1' }
    { 'from_list': ['BrBr.c1ccc2cc3ccccc3cc2c1', 'BrBr.c1ccc2cc3ccccc3cc2c1CCO'] }
    { 'from_file': 'my_reactions.txt' }
    { 'from_file': 'my_reactions.csv' }
    { 'from_df':   'my_reactions' }
    """

    cmd_pointer = None
    cmd = None

    # API
    api = None

    # Command
    reactions_list = []
    using_params = {}
    no_cache = False

    # Sorting
    cached_reactions = {}
    invalid_reactions = {}
    skip_count = 0  # Number of cached or invalid reactions that can be skipped
    reactions_list_sanitized = []  # Reactions list without invalid or cached reactions

    # Default parameters
    using_params_defaults = {
        "ai_model": "2020-08-10",
        "topn": 10,
    }

    def __init__(self, cmd_pointer, cmd):
        super().__init__()
        self.cmd_pointer = cmd_pointer
        self.cmd = cmd

    def run(self):
        if not self._setup():
            return

        # Run reaction query
        # ------------------
        if self.skip_count < len(self.reactions_list):
            # Sanitize the reaction list so invalid
            # reactions won't break the API call
            self.reactions_list_sanitized = [
                reaction
                for reaction in self.reactions_list
                if (reaction not in self.invalid_reactions and reaction not in self.cached_reactions)
            ]

            # Step 1 - Lauch the query & create task id
            task_id = self._api_get_task_id()
            if not task_id:
                return

            # Step 2 - Get the reaction results
            reaction_predictions = self._api_get_results(task_id)
            if not reaction_predictions:
                return

            # Insert None values in the reaction_predictions list
            # at the same index where the invalid reactions were,
            # so indices match between reactions_list and reaction_predictions
            for reaction in self.reactions_list:
                if reaction in self.invalid_reactions:
                    reaction_predictions.insert(self.reactions_list.index(reaction), None)

        # Loop through reaction results and print them
        for i, reaction in enumerate(self.reactions_list):
            # Ignore index for single reaction
            index = i + 1 if len(self.reactions_list) > 1 else None

            # PRINT REACTION - INVALID REACTIONS
            # ----------------------------------
            # if reaction in invalid_reactions_print_str: %%
            if reaction in self.invalid_reactions:
                self._display_reaction(index, reaction, invalid_smiles=self.invalid_reactions[reaction])
                continue

            # PRINT REACTION - CACHED REACTIONS
            # ---------------------------------
            if reaction in self.cached_reactions:
                cached_prediction = self.cached_reactions[reaction]
                self._display_reaction(index, reaction, cached_prediction, is_cached=True)
                continue

            # Get newly generated prediction data
            prediction = reaction_predictions[i]

            # Save result in cache
            # - - -
            # RXN returns canonicalized smiles, so we create two cache records:
            # one with the input smiles and one with the rxn-canonicalized smiles as key.
            # - - -
            # 1) Input smiles
            input_smiles = reaction.split(".")
            input_smiles_key = super().homogenize(input_smiles)
            super().store_result_cache(
                self.cmd_pointer,
                name=f"predict-reaction-{self.using_params.get('ai_model')}",
                key=input_smiles_key,
                payload=prediction,
            )
            # 2) Canonicalized smiles from RXN
            prediction_smiles = prediction.get("smiles", "").split(">>")[0].split(".")
            prediction_smiles_key = super().homogenize(prediction_smiles)
            super().store_result_cache(
                self.cmd_pointer,
                name=f"predict-reaction-{self.using_params.get('ai_model')}",
                key=prediction_smiles_key,
                payload=prediction,
            )

            # PRINT REACTION - NEWLY GENERATED REACTIONS
            # ------------------------------------------
            self._display_reaction(index, reaction, prediction)

        if GLOBAL_SETTINGS["display"] == "api":
            return reaction_predictions.get("predictions")
        else:
            return None

    def _setup(self):
        # Define the RXN API
        self.api = self.cmd_pointer.login_settings["client"][
            self.cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
        ]

        # Setup
        super().sync_up_workspace_name(self.cmd_pointer)
        super().get_current_project(self.cmd_pointer)

        # Parse command
        self.reactions_list = self._parse_reactions_list()
        self.using_params = super().parse_using_params(self.cmd, self.using_params_defaults)
        self.no_cache = bool(self.cmd.get("no_cache"))

        if not self.reactions_list:
            return False

        # Set aside reactions that are invalid or cached
        reactions_to_be_skipped = self._sort_reactions()
        self.cached_reactions = reactions_to_be_skipped.get("cached_reactions", {})
        self.invalid_reactions = reactions_to_be_skipped.get("invalid_reactions", {})
        self.skip_count = reactions_to_be_skipped.get("count", 0)

        return True

    def _parse_reactions_list(self):
        """
        Parse the reactions list from the command.
        """
        from_list = []

        # Form string
        if self.cmd.get("from_str"):
            from_list = [self.cmd.get("from_str")]

        # From file
        elif self.cmd.get("from_file"):
            from_file = self.cmd.get("from_file")
            if not from_file:
                return output_error("No file provided")
            else:
                ext = from_file.split(".")[-1]

                # CSV file
                if ext == "csv":
                    reactions_df = super().get_dataframe_from_file(self.cmd_pointer, from_file)
                    if reactions_df is None:
                        return
                    else:
                        from_list = super().get_column_as_list_from_dataframe(reactions_df, "reactions")
                        if not from_list:
                            return output_error("No reactions found in CSV file, file should have column 'reactions'")
                        super().validate_reactions_list(from_list)

                # TXT file
                elif ext == "txt":
                    from_list = super().get_list_from_txt_file(self.cmd_pointer, from_file)
                    if not from_list:
                        return output_error("No reactions found in TXT file, file seems to be empty")
                    super().validate_reactions_list(from_list)

                # Invalid file format
                else:
                    return output_error("Invalid file format", "Accepted formats are .csv or .txt")

        # From dataframe
        elif self.cmd.get("from_df"):
            reactions_df = self.cmd_pointer.get_df(self.cmd["from_df"])
            if reactions_df is None:
                return
            else:
                from_list = super().get_column_as_list_from_dataframe(reactions_df, "reactions")
                if not from_list:
                    return output_error(
                        ["No reactions found", "Dataframe should have a 'reactions' column"], return_val=False
                    )

        # From list
        elif self.cmd.get("from_list"):
            from_list = self.cmd["from_list"]

        return from_list

    def _sort_reactions(self):
        """
        Loop through reactions and single out the ones that are either invalid or cached.
        """

        # Storage for invalid reactions and cached reactions
        invalid_reactions = {}
        cached_reactions = {}

        # Loop
        for reaction in self.reactions_list:
            # Check for invalid SMILES
            input_smiles = reaction.split(".")
            invalid_smiles = []
            for smiles in input_smiles:
                if not valid_smiles(smiles):
                    invalid_smiles.append(smiles)

            # REACTION IS INVALID
            if len(invalid_smiles) > 0:
                invalid_reactions[reaction] = invalid_smiles
                continue

            # Check for cached results
            elif not self.no_cache:
                input_smiles_key = super().homogenize(input_smiles)
                result_from_cache = super().retrieve_result_cache(
                    self.cmd_pointer,
                    name=f"predict-reaction-{self.using_params.get('ai_model')}",
                    key=input_smiles_key,
                )

                # REACTION IS CACHED
                if result_from_cache:
                    cached_reactions[reaction] = result_from_cache
                    continue

        return {
            "invalid_reactions": invalid_reactions,
            "cached_reactions": cached_reactions,
            "count": len(invalid_reactions.keys()) + len(cached_reactions.keys()),
        }

    def _api_get_task_id(self):
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
                predict_reaction_batch_response = self.api.predict_reaction_batch(self.reactions_list)
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

    def _api_get_results(self, task_id):
        """
        Check on the status of a query and return the results.

        Parameters
        ----------
        task_id: str
            Task ID returned by the API in previous request.
        """
        retries = 0
        max_retries = 10
        try_again = True
        response = None
        while try_again is True:
            try:
                if retries == 0:
                    spinner.start("Processing prediction")
                else:
                    spinner.start(f"Processing prediction - retry #{retries}")

                # raise Exception("This is a test error")
                response = self.api.get_predict_reaction_batch_results(task_id)
                if not response:
                    raise ValueError("Empty response from the server (get reactions)")
                if not response.get("predictions"):
                    raise ValueError("No predictions returned")
                try_again = False

            except ValueError as err:  # pylint: disable=broad-exception-caught
                sleep(2)
                retries = retries + 1
                if retries > max_retries:
                    spinner.stop()
                    output_error([f"Server unresponsive after {max_retries} retries", err], return_val=False)
                    return False

        spinner.succeed("Done")
        return response.get("predictions")

    def _display_reaction(
        self,
        index: int,
        reaction: str,
        prediction: dict = None,
        invalid_smiles: list = [],
        is_cached: bool = False,
    ):
        """
        Display a reaction in the CLI or Jupyter Notebook.

        Parameters
        ----------
        index: int
            Index of the reaction in the list. None for single reactions.
        reaction : str
            Reaction smiles string as it was passed by the user.
        prediction: dict
            Prediction data for the reaction, as returned by the API eg:
            {
                'confidence': 0.9797950224106948,
                'smiles': 'BrBr.c1ccc2cc3ccccc3cc2c1>>Brc1c2ccccc2cc2ccccc12',
                'photochemical': False,
                'thermal': False
            }
        invalid_smiles: list
            List of invalid smiles in the reaction.
            This indicates the output type is an invalid reaction.
        is_cached: bool
            Wether the reaction was previously cached.
            This indicates the output type is a cached reaction.
        """

        print_str = self.__generate_print_str(index, reaction, prediction, invalid_smiles, is_cached)

        # Display in Jupyter Notebook
        if GLOBAL_SETTINGS["display"] == "notebook":
            # Open frame
            output = ['<div style="display:inline-block; border:solid 1px #ccc">']

            # Add image
            if prediction:
                output.append(self.__get_reaction_image(prediction["smiles"]))

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

    def __generate_print_str(
        self,
        index,
        reaction,
        prediction: dict = None,
        invalid_smiles: list = [],
        is_cached: bool = False,
    ):
        """
        Generate a print string for a single reaction.

        See _display_reaction() for parameters.
        """

        input_smiles = reaction.split(".")

        # Invalid reaction
        if invalid_smiles:
            header_print_str = self.___print_str__header(index, flag="failed")
            reaction_print_str = self.___print_str__reaction_invalid(input_smiles, invalid_smiles)
            print_str = "\n".join([header_print_str, reaction_print_str])

        # Cached reaction
        elif is_cached:
            header_print_str = self.___print_str__header(index, flag="cached")
            reaction_print_str = self.___print_str__reaction(input_smiles, prediction)
            confidence_print_str = self.___print_str__confidence(prediction.get("confidence"))
            print_str = "\n".join([header_print_str, reaction_print_str, confidence_print_str])

        # New reaction
        else:
            header_print_str = self.___print_str__header(index)
            reaction_print_str = self.___print_str__reaction(input_smiles, prediction)
            confidence_print_str = self.___print_str__confidence(prediction["confidence"])
            print_str = "\n".join([header_print_str, reaction_print_str, confidence_print_str])

        return print_str

    def ___print_str__header(self, index: int = None, flag: str = ""):
        """
        Get the header for a single reaction print.

        Parameters
        ----------
        index: int
            Index of the reaction in the list.
            Ignored for single reactions.
        flag: str
            Flag to indicate the status of the reaction
        """

        # Index
        index_str = " Result" if index is None else f" #{index}"

        # Flag
        if flag == "cached":
            flag = super().get_flag("cached")
        elif flag == "failed":
            flag = super().get_flag("failed")

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

    def ___print_str__reaction(self, input_smiles: list, prediction: dict):
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
        reaction_smiles = prediction.get("smiles")
        confidence = prediction.get("confidence")
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
        confidence_style_tags = super().get_confidence_style(confidence)
        reaction_input_print = "<soft>+</soft>  " + "\n<soft>+</soft>  ".join(input_smiles)
        output = [
            reaction_input_print,
            "   <soft>-------------------------</soft>",
            f"<soft>=></soft> {confidence_style_tags[0]}{reaction_output}{confidence_style_tags[1]}",
        ]

        # Turn into HTML for Jupyter Notebook
        if GLOBAL_SETTINGS["display"] == "notebook":
            output = "<br>".join(output) + "<br>"
            output = tags_to_markdown(output)
            return output
        else:
            return "\n".join(output)

    def ___print_str__reaction_invalid(self, input_smiles: list, invalid_smiles: list):
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
            input_smiles[i] = (
                f"<error>✖ {smiles}</error>" if smiles in invalid_smiles else f"<success>✔</success> {smiles}"
            )

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

    def ___print_str__confidence(self, confidence):
        """
        Visualize the confidence score.

        Parameters:
            confidence (float): Confidence score between 0 and 1
        """
        confidence_print_str_list = super().get_print_str_list__confidence(confidence)
        return "\n".join(confidence_print_str_list)

    def __get_reaction_image(self, reaction_smiles: str):
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
        drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
        drawer.SetDrawOptions(draw_options)

        # Draw reaction
        drawer.DrawReaction(reaction)
        drawer.FinishDrawing()
        svg = drawer.GetDrawingText()

        return svg
