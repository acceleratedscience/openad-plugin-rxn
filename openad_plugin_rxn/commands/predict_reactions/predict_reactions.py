import pandas as pd
from time import sleep
from rdkit.Chem import AllChem
from rdkit.Chem.Draw import rdMolDraw2D
from IPython.display import display, HTML

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.smols.smol_functions import valid_smiles
from openad.smols.smol_cache import create_analysis_record, save_result

# OpenAD tools
from openad_tools.spinner import spinner
from openad_tools.style_parser import tags_to_markdown
from openad_tools.output import output_text, output_error
from openad_tools.jupyter import save_df_as_csv

# Plugin
from openad_plugin_rxn.plugin_msg import msg
from openad_plugin_rxn.plugin_params import PLUGIN_KEY
from openad_plugin_rxn.plugin_master_class import RXNPlugin


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
    use_cache = False

    # Sorting
    cached_reactions = {}
    invalid_reactions = {}
    skip_count = 0  # Number of cached or invalid reactions that can be skipped
    reactions_list_sanitized = []  # Reactions list without invalid or cached reactions

    # Default parameters
    using_params_defaults = {
        "ai_model": "2020-08-10",
        "topn": None,
    }

    # Result
    reaction_predictions = None  # Prediction data as returned by the API
    output_data = None  # Prediction data formatted for API output / save_as file

    def __init__(self, cmd_pointer, cmd):
        """
        Parameters
        ----------
        cmd_pointer:
            The command pointer object
        cmd: dict
            Parser inputs from pyparsing as a dictionary
        """
        super().__init__(cmd_pointer)
        self.cmd = cmd

    def _setup(self):
        # Parse command
        self.reactions_list = self._parse_reactions_list()
        self.using_params = self.parse_using_params(self.cmd, self.using_params_defaults)
        self.use_cache = bool(self.cmd.get("use_cache"))

        if not self.reactions_list:
            return False

        # Set aside reactions that are invalid or cached
        reactions_to_be_skipped = self._sort_reactions()
        self.cached_reactions = reactions_to_be_skipped.get("cached_reactions", {})
        self.invalid_reactions = reactions_to_be_skipped.get("invalid_reactions", {})
        self.skip_count = reactions_to_be_skipped.get("count", 0)

        return True

    def run(self):
        """
        Run the command.
        """

        # In case you're offline
        if not self.api:
            output_error(msg("err_api_offline"), return_val=False)
            return

        # Setup
        if not self._setup():
            return

        self.output_data = []

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
            self.reaction_predictions = self._api_get_results(task_id)
            if not self.reaction_predictions:
                return

            # Insert None values in the reaction_predictions list at the
            # same index where the invalid or cached reactions were, so
            # indices match between reactions_list and reaction_predictions
            for reaction in self.reactions_list:
                if reaction in self.invalid_reactions or reaction in self.cached_reactions:
                    self.reaction_predictions.insert(self.reactions_list.index(reaction), None)

        # # For debugging
        # print("\nReactions:\n", self.reactions_list)
        # print("\nInvalid:\n", self.invalid_reactions)
        # print("\nCached:\n", self.cached_reactions)
        # print("\nPredictions:\n", self.reaction_predictions)

        # Loop through reaction results and print them
        for i, reaction in enumerate(self.reactions_list):
            # Ignore index for single reaction
            index = i + 1 if len(self.reactions_list) > 1 else None

            # PRINT REACTION - INVALID REACTIONS
            # ----------------------------------
            if reaction in self.invalid_reactions:
                invalid_smiles = self.invalid_reactions[reaction]
                self._add_to_output_data(
                    reaction,
                    error={
                        "message": "Invalid smiles",
                        "invalid_smiles": invalid_smiles,
                    },
                )
                self._display_reaction(index, reaction, invalid_smiles=invalid_smiles)
                continue

            # PRINT REACTION - CACHED REACTIONS
            # ---------------------------------
            if reaction in self.cached_reactions:
                cached_prediction = self.cached_reactions[reaction]
                self._add_to_output_data(
                    reaction,
                    cached_prediction,
                    from_cache=True,
                )
                self._display_reaction(index, reaction, cached_prediction, from_cache=True)
                continue

            # Get newly generated prediction data
            prediction = self.reaction_predictions[i]

            # Save result in cache
            # - - -
            # RXN returns canonicalized smiles, so we create two cache records:
            # one with the input smiles and one with the rxn-canonicalized smiles as key.
            # - - -
            # 1) Input smiles
            input_smiles = reaction.split(".")
            input_smiles_key = self.homogenize_smiles(input_smiles)
            topn = self.using_params.get("topn") or self._get_backward_compatible_topn()
            topn_str = "" if topn in [None, 0, "0"] else f"-topn-{topn}"
            self.store_result_cache(
                name=f"predict-reaction-{self.using_params.get('ai_model')}{topn_str}",
                key=input_smiles_key,
                payload=prediction,
            )
            # 2) Canonicalized smiles from RXN
            prediction_smiles = prediction.get("smiles", "").split(">>")[0].split(".")
            prediction_smiles_key = self.homogenize_smiles(prediction_smiles)
            self.store_result_cache(
                name=f"predict-reaction-{self.using_params.get('ai_model')}{topn_str}",
                key=prediction_smiles_key,
                payload=prediction,
            )

            # Save results as analysis records that can be merged
            # with the molecule working set in a follow up comand:
            # `enrich mols with analysis`
            output_smiles = prediction.get("smiles", "").split(">>")
            output_smiles = [output_smiles[1]] if len(output_smiles) > 1 else []
            all_smiles = input_smiles + output_smiles
            for smiles in all_smiles:
                save_result(
                    create_analysis_record(
                        smiles=smiles,
                        toolkit=PLUGIN_KEY,
                        function="predict_reaction",
                        parameters=self.using_params,
                        results={
                            "sources": input_smiles,
                            "result": output_smiles,
                        },
                    ),
                    self.cmd_pointer,
                )

            # PRINT REACTION - NEWLY GENERATED REACTIONS
            # ------------------------------------------
            self._add_to_output_data(
                reaction,
                prediction,
            )
            self._display_reaction(index, reaction, prediction)

        # Convert to DataFrame
        df = pd.DataFrame.from_dict(self.output_data)
        df = df.fillna("")  # Replace NaN with empty string

        # Ensure the input columns are always at the beginning
        # This may not be the case, eg. with:
        # ['BrBr.c1ccc2cc3ccccc3cc2c1CCO' , 'BrBr.c1ccc2cc3ccccc3cc2c1', 'BrBr.ABC.c1ccc2cc3ccccc3cc2c1']
        input_cols = []
        other_cols = []
        for col in df.columns:
            if col == "input" or col.startswith("input_"):
                input_cols.append(col)
            else:
                other_cols.append(col)
        rearranged_cols = input_cols + other_cols
        df = df.reindex(columns=rearranged_cols)

        # Save results to file (prints success message)
        if "save_as" in self.cmd:
            results_file = str(self.cmd["results_file"])
            save_df_as_csv(self.cmd_pointer, df, results_file)

        # Return data in API mode
        if GLOBAL_SETTINGS["display"] == "api":
            return df

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
                    reactions_df = self.get_dataframe_from_file(from_file)
                    if reactions_df is None:
                        return
                    else:
                        from_list = self.get_column_as_list_from_dataframe(reactions_df, "reactions")
                        if not from_list:
                            output_error(
                                "No reactions found in CSV file. Reactions should be stored in a column named 'Reactions'",
                                return_val=False,
                            )
                            return []
                        self.validate_reactions_list(from_list)

                # TXT file
                elif ext == "txt":
                    from_list = self.get_list_from_txt_file(from_file)
                    if not from_list:
                        return output_error("No reactions found in TXT file, file seems to be empty")
                    self.validate_reactions_list(from_list)

                # Invalid file format
                else:
                    return output_error("Invalid file format", "Accepted formats are .csv or .txt")

        # From dataframe
        elif self.cmd.get("from_df"):
            reactions_df = self.cmd_pointer.get_df(self.cmd["from_df"])
            if reactions_df is None:
                return
            else:
                from_list = self.get_column_as_list_from_dataframe(reactions_df, "reactions")
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
            elif self.use_cache:
                input_smiles_key = self.homogenize_smiles(input_smiles)
                topn = self.using_params.get("topn") or self._get_backward_compatible_topn()
                topn_str = "" if topn in [None, 0, "0"] else f"-topn-{topn}"
                result_from_cache = self.retrieve_result_cache(
                    name=f"predict-reaction-{self.using_params.get('ai_model')}{topn_str}",
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
        launch_job_response = None
        while try_again is True:
            try:
                if retries == 0:
                    spinner.start("Starting prediction")
                else:
                    spinner.start(f"Starting prediction - retry #{retries}")

                # raise Exception("This is a test error")
                ai_model = self.using_params.get("ai_model")
                topn = self.using_params.get("topn") or self._get_backward_compatible_topn()

                # Note: RXN provides a separate API endpoint for single reactions,
                # which returns a bit more data including an image, but we don't use
                # it as we have our own visualization methods.
                # - - -
                # launch_job_response = self.api.predict_reaction(self.reactions_list_sanitized[0], ai_model)
                # task_id = launch_job_response.get("prediction_id")
                # response = self.api.get_predict_reaction_results(task_id)

                if topn not in [None, 0, "0"]:
                    # Batch topn function - https://github.com/rxn4chemistry/rxn4chemistry/blob/9bfd050153ac754298353c1de52e45bb6bb9cf97/rxn4chemistry/core.py#L507
                    # This endpoint consumes reactions as lists instead of strings.
                    reactions_list_sanitized = [r.split(".") for r in self.reactions_list_sanitized]
                    launch_job_response = self.api.predict_reaction_batch_topn(reactions_list_sanitized, topn, ai_model)
                else:
                    # Regular batch function - https://github.com/rxn4chemistry/rxn4chemistry/blob/9bfd050153ac754298353c1de52e45bb6bb9cf97/rxn4chemistry/core.py#L436
                    launch_job_response = self.api.predict_reaction_batch(self.reactions_list_sanitized, ai_model)

                if not launch_job_response:
                    raise ValueError("Empty server response")
                if not launch_job_response.get("task_id"):
                    raise ValueError("No task_id returned")
                try_again = False

            except Exception as err:  # pylint: disable=broad-exception-caught
                sleep(2)
                retries = retries + 1
                if retries > max_retries:
                    spinner.stop()
                    output_error([f"Server unresponsive after {max_retries} retries", err], return_val=False)
                    return False

        task_id = launch_job_response.get("task_id")
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
                topn = self.using_params.get("topn") or self._get_backward_compatible_topn()
                if topn not in [None, 0, "0"]:
                    response = self.api.get_predict_reaction_batch_topn_results(task_id)
                else:
                    response = self.api.get_predict_reaction_batch_results(task_id)

                if not response:
                    raise Warning("Empty server response")
                if response.get("task_status") == "RUNNING":
                    raise Warning("Still running")
                if not response.get("predictions"):
                    if response.get("response", {}).get("payload", {}).get("task", {}).get("status") == "ERROR":
                        raise ValueError(response)
                    else:
                        raise Warning("No predictions returned")

                try_again = False

            # Still running, keep trying
            except Warning as err:  # pylint: disable=broad-exception-caught
                sleep(2)
                retries = retries + 1
                if retries > max_retries:
                    spinner.stop()
                    output_error([f"Server unresponsive after {max_retries} retries", err], return_val=False)
                    return False

            # Error, abort
            except ValueError as err:
                spinner.stop()
                output_error(["RXN API error", err], return_val=False)
                return False

        spinner.succeed("Done")
        return response.get("predictions")

    def _add_to_output_data(self, reaction, prediction=None, from_cache=False, error=None):
        """
        Add a reaction entry to the output data, which will be used to create a DataFrame.

        Parameters
        ----------
        reaction: str
            Reaction smiles string as it was passed by the user.
            AA.BB.CC
        prediction: dict
            Prediction data for the reaction, as returned by the API.
            {
                'confidence': 0.9999999999999999,
                'smiles': 'AA.BB.CC>>DD',
                'photochemical': False,
                'thermal': False
            }
        from_cache: bool
            Wether the reaction was previously cached.
        error: dict
            Error data for the reaction, if the reaction is invalid.
            {
                'message': 'Invalid smiles',
                'invalid_smiles': ['BrBr']
            }
        """

        # Separate input and output smiles
        prediction = prediction or {}
        input_smiles = reaction.split(".")
        prediction_smiles = prediction.get("smiles")
        output_smiles = (prediction_smiles or "").split(">>")
        output_smiles = output_smiles[1] if len(output_smiles) > 1 else None

        # Create entry
        new_entry = {"input": input_smiles}
        for i, inp in enumerate(input_smiles):
            new_entry[f"input_{i}"] = inp

        if error:
            new_entry["error_message"] = error.get("message")
            new_entry["invalid_smiles"] = error.get("invalid_smiles")
        else:
            new_entry["output"] = output_smiles
            new_entry["reaction"] = prediction_smiles
            new_entry["from_cache"] = bool(from_cache)

        # Unfold prediction data into the parent object, so one
        # dataframe row has all the data for a single reaction
        for key, value in prediction.items():
            if key != "smiles":
                new_entry[key] = value

        # Store entry
        self.output_data.append(new_entry)

    def _display_reaction(
        self,
        index: int,
        reaction: str,
        prediction: dict = None,
        from_cache: bool = False,
        invalid_smiles: list = None,
    ):
        """
        Display a reaction in the CLI or Jupyter Notebook.

        Parameters
        ----------
        index: int
            Index of the reaction in the list. None for single reactions.
        reaction: str
            Reaction smiles string as it was passed by the user.
            AA.BB.CC
        prediction: dict
            Prediction data for the reaction, as returned by the API.
            {
                'confidence': 0.9999999999999999,
                'smiles': 'AA.BB.CC>>DD',
                'photochemical': False,
                'thermal': False
            }
        from_cache: bool
            Wether the reaction was previously cached.
            This indicates the output type is a cached reaction.
        invalid_smiles: list
            List of invalid smiles in the reaction.
            This indicates the output type is an invalid reaction.
        """

        # Don't display anything in API mode
        if GLOBAL_SETTINGS["display"] == "api":
            return

        # Prediction results from topn queries are structured
        # differently and have their own display function
        is_topn_result = self.__is_topn_result(prediction)
        rich_output = "rich_output" in self.cmd
        print_str = ""
        if is_topn_result:
            print_str = self.__generate_print_str_topn(index, reaction, prediction, from_cache, rich_output)
        else:
            print_str = self.__generate_print_str(index, reaction, prediction, invalid_smiles, from_cache, rich_output)

        # Display in Jupyter Notebook
        if GLOBAL_SETTINGS["display"] == "notebook":
            # Open frame
            output = ['<div style="display:inline-block; border:solid 1px #ccc">']

            # Add image
            # Except for topn results, which shows a list of results instead of one
            if prediction and not self.__is_topn_result(prediction):
                output.append(self.__get_reaction_image(prediction.get("smiles")))

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
            pad = 2 if "rich_output" in self.cmd else 1
            output_text(print_str, pad=pad, nowrap=True, return_val=False)

    def __is_topn_result(self, prediction: dict) -> bool:
        """
        Determine if a prediction is a topn result or a regular batch result.

        Will always be false for invalid reactions, because prediction will be None.
        """
        return bool(prediction and prediction.get("results") and prediction.get("raw_results"))

    def __generate_print_str(
        self,
        index,
        reaction,
        prediction: dict = None,
        invalid_smiles: list = None,
        from_cache: bool = False,
        rich_output: bool = False,
    ):
        """
        Generate a rich print string for a single reaction.

        See _display_reaction() for parameters.
        """

        input_smiles = reaction.split(".")

        # Invalid reaction
        if invalid_smiles:
            header_print_str = self.___print_str__header(index, flag="failed")
            if rich_output:
                reaction_print_str = self.___print_str_rich__reaction_invalid(input_smiles, invalid_smiles)
            else:
                reaction_print_str = self.___print_str_basic__reaction_invalid(input_smiles, invalid_smiles)
            print_str = "\n".join([header_print_str, reaction_print_str])

        # Valid reaction
        else:
            flag = "cached" if from_cache else ""
            header_print_str = self.___print_str__header(index, flag)
            if rich_output:
                reaction_print_str = self.___print_str_rich__reaction(input_smiles, prediction)
                confidence_print_str = self.___print_str__confidence(prediction.get("confidence"))
                print_str = "\n".join([header_print_str, reaction_print_str, confidence_print_str])
            else:
                reaction_print_str = self.___print_str_basic__reaction(input_smiles, prediction)
                print_str = "\n".join([header_print_str, reaction_print_str])

        return print_str

    def __generate_print_str_topn(
        self,
        index,
        reaction,
        prediction: dict = None,
        from_cache: bool = False,
        rich_output: bool = False,
    ):
        """
        Generate a rich print string for a single reaction.

        See _display_reaction() for parameters.
        """

        input_smiles = reaction.split(".")

        # Note: invalid reactions get parsed by __generate_print_str()

        flag = "cached" if from_cache else ""
        header_print_str = self.___print_str__header(index, flag)
        if rich_output:
            reaction_print_str = self.___print_str_rich__reaction_topn(input_smiles, prediction)
        else:
            reaction_print_str = self.___print_str_basic__reaction_topn(input_smiles, prediction)
        print_str = "\n".join([header_print_str, reaction_print_str])

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
            flag = self.get_flag("cached")
        elif flag == "failed":
            flag = self.get_flag("failed")

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

    def ___print_str_basic__reaction(self, input_smiles: list, prediction: dict):
        """
        Get a basic string representation of a reaction.

        Parameters
        ----------
        input_smiles: list
            List of input smiles strings.
            Example:['AA', 'BB']
        prediction: dict
            prediction output from API.
            Example:
            {
                "confidence": 0.7777777777777777,
                "smiles": "AA.BB>>CC",
                "photochemical": False,
                "thermal": False,
            }

        Returns
        -------
        Smiles: AA.BB>>CC
        Reaction: AA + BB ----> CC
        Confidence: 78%
        """

        # Deconstruct
        reaction_smiles = prediction.get("smiles")
        confidence = prediction.get("confidence")
        reaction_in_out = reaction_smiles.split(">>")
        reaction_output = reaction_in_out[1]

        # Assemble
        confidence_bar = self.get_print_str_list__confidence(confidence)[0]
        confidence = f"{round(confidence * 100, 2)}%" if confidence else "n/a"
        reaction_input_str = " <soft>+</soft> ".join(input_smiles)
        reaction_output_str = f" <soft>----></soft> {reaction_output}"
        output = [
            f"<yellow>Smiles:    </yellow> {reaction_smiles}",
            f"<yellow>Reaction:  </yellow> {reaction_input_str}{reaction_output_str}",
            f"<yellow>Confidence:</yellow> <soft>{confidence}</soft>",  # + confidence_bar,
        ]

        # Turn into HTML for Jupyter Notebook
        if GLOBAL_SETTINGS["display"] == "notebook":
            output = "<br>".join(output) + "<br>"
            output = tags_to_markdown(output)
            return output
        else:
            return "\n".join(output)

    def ___print_str_rich__reaction(self, input_smiles: list, prediction: dict):
        """
        Get a clean, multiline string representation of a reaction.

        Parameters
        ----------
        input_smiles: list
            List of input smiles strings.
            Example:['AA', 'BB']
        prediction: dict
            prediction output from API.
            Example:
            {
                "confidence": 0.7777777777777777,
                "smiles": "AA.BB>>CC",
                "photochemical": False,
                "thermal": False,
            }

        Returns
        -------
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
        confidence_style_tags = self.get_confidence_style(confidence)
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

    def ___print_str_basic__reaction_topn(self, input_smiles: list, prediction: dict):
        """
        Get a clean, multiline string representation of a topn reaction.

        Parameters
        ----------
        input_smiles: list
            List of input smiles strings.
            Example:['AA', 'BB']
        prediction: dict
            prediction output from API.
            Example:
            {
                "results": [
                    {"confidence": 0.77777777777777777, "smiles": ["DD"]},
                    {"confidence": 0.66666666666666666, "smiles": ["EE"]},
                    {"confidence": 0.55555555555555555, "smiles": ["FF"]},
                ],
                "raw_results": [
                    {
                        "confidence": 0.77777777777777777,
                        "smiles": "DD",
                        "photochemical": False,
                        "thermal": False,
                    },
                    {
                        "confidence": 0.66666666666666666,
                        "smiles": "EE",
                        "photochemical": False,
                        "thermal": False,
                    },
                    {
                        "confidence": 0.55555555555555555,
                        "smiles": "FF",
                        "photochemical": False,
                        "thermal": False,
                    }
                ],
            }

        Returns
        -------
        Reaction: AA.BB.CC
        1 Conf. 77.77% DD
        2 Conf. 66.66% EE
        3 Conf. 55.55% FF
        """

        # Assemble
        reaction_smiles = ".".join(input_smiles)
        reaction_output_print = []
        results = prediction.get("results", [])
        for i, result in enumerate(results, start=1):
            output_smiles = result.get("smiles", [""])[0]
            confidence = result.get("confidence")
            confidence = f"{round(confidence * 100)}%" if confidence or confidence == 0 else None
            confidence = f"{confidence:<3}" if confidence is not None else "n/a "
            reaction_output_print.append(f"{i} <soft>Conf. {confidence}</soft> {output_smiles}")

        output = [
            f"<yellow>Smiles:</yellow> {reaction_smiles}",
            *reaction_output_print,
        ]

        # Turn into HTML for Jupyter Notebook
        if GLOBAL_SETTINGS["display"] == "notebook":
            output = "<br>".join(output) + "<br>"
            output = tags_to_markdown(output)
            return output
        else:
            return "\n".join(output)

    def ___print_str_rich__reaction_topn(self, input_smiles: list, prediction: dict):
        """
        Get a clean, multiline string representation of a topn reaction.

        Parameters
        ----------
        input_smiles: list
            List of input smiles strings.
            Example:['AA', 'BB']
        prediction: dict
            prediction output from API.
            Example:
            {
                "results": [
                    {"confidence": 0.77777777777777777, "smiles": ["DD"]},
                    {"confidence": 0.66666666666666666, "smiles": ["EE"]},
                    {"confidence": 0.55555555555555555, "smiles": ["FF"]},
                ],
                "raw_results": [
                    {
                        "confidence": 0.77777777777777777,
                        "smiles": "DD",
                        "photochemical": False,
                        "thermal": False,
                    },
                    {
                        "confidence": 0.66666666666666666,
                        "smiles": "EE",
                        "photochemical": False,
                        "thermal": False,
                    },
                    {
                        "confidence": 0.55555555555555555,
                        "smiles": "FF",
                        "photochemical": False,
                        "thermal": False,
                    }
                ],
            }

        Returns
        -------
            +  AA
            +  BB
            +  CC
               -------------------------
            => DD
               ━━━━━━━━━━━━━━━━━━╸━━━━━━
               77.77% confidence
               -------------------------
            => EE
               ━━━━━━━━━━━━━━━╸━━━━━━━━━
               66.66% confidence
               -------------------------
            => FF
               ━━━━━━━━━━━━╸━━━━━━━━━━━━
               55.55% confidence
        """

        # Assemble input
        reaction_input_print = "<soft>+</soft>  " + "\n<soft>+</soft>  ".join(input_smiles)

        # Assemble output
        reaction_output_print = []
        results = prediction.get("results", [])
        for i, result in enumerate(results, start=1):
            output_smiles = result.get("smiles", [""])[0]
            confidence = result.get("confidence", 0)
            confidence_print_str = self.___print_str__confidence(confidence)
            confidence_print_str = "   " + "\n   ".join(confidence_print_str.splitlines())
            confidence_style_tags = self.get_confidence_style(confidence)
            reaction_output_print.append("   <soft>-------------------------</soft>")
            reaction_output_print.append(
                f"<soft>{i}.</soft> {confidence_style_tags[0]}{output_smiles}{confidence_style_tags[1]}"
            )
            reaction_output_print.append(confidence_print_str)

        # Assemble final output
        output = [reaction_input_print] + reaction_output_print

        # Turn into HTML for Jupyter Notebook
        if GLOBAL_SETTINGS["display"] == "notebook":
            output = "<br>".join(output) + "<br>"
            output = tags_to_markdown(output)
            return output
        else:
            return "\n".join(output)

    def ___print_str_basic__reaction_invalid(self, input_smiles: list, invalid_smiles: list):
        """
        Get a simple string representation of an invalid reaction.

        Input:
            ['AA', 'BB', 'CC']
            ['BB']

        Output:
            Smiles: AA.BB>>CC
            Reaction: AA + BB ----> CC
            Invalid reaction
        """

        input_smiles = input_smiles if input_smiles else []
        invalid_smiles = invalid_smiles if invalid_smiles else []

        # Mark valid/invalid smiles
        input_smiles = [f"<error>{smiles}</error>" if smiles in invalid_smiles else smiles for smiles in input_smiles]

        # Assemble
        reaction_smiles = ".".join(input_smiles)
        reaction_print = " <soft>+</soft> ".join(input_smiles) + " <soft>----></soft> <error>error</error>"
        output = [
            # "<error>Invalid reaction</error>",
            f"<error>Smiles:    </error> {reaction_smiles}",
            f"<error>Reaction:  </error> {reaction_print}",
        ]

        # Turn into HTML for Jupyter Notebook
        if GLOBAL_SETTINGS["display"] == "notebook":
            output = "<br>".join(output) + "<br>"
            output = tags_to_markdown(output)
            return output
        else:
            return "\n".join(output)

    def ___print_str_rich__reaction_invalid(self, input_smiles: list, invalid_smiles: list):
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
        input_smiles = input_smiles if input_smiles else []
        invalid_smiles = invalid_smiles if invalid_smiles else []

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
        confidence_print_str_list = self.get_print_str_list__confidence(confidence)
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

    def _get_backward_compatible_topn(self):
        """
        Ensure backward compatibility with the toolkit command.

        If topn is present in the command, we set the value to 5 to match the toolkit behavior.
        """
        if "topn" in self.cmd:
            return 5
        else:
            return None
