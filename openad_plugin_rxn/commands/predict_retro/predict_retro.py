from time import sleep
import pandas as pd
from IPython.display import display, HTML

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.smols.smol_cache import create_analysis_record, save_result
from openad.smols.smol_functions import canonicalize, valid_smiles
from openad.helpers.spinner import spinner
from openad.plugins.style_parser import strip_tags
from openad.helpers.output import output_text, output_error
from openad.helpers.general import get_print_width
from openad.helpers.jupyter import jup_display_input_molecule

# Plugin
from openad_plugin_rxn.plugin_msg import msg
from openad_plugin_rxn.plugin_params import PLUGIN_KEY
from openad_plugin_rxn.plugin_master_class import RXNPlugin


class PredictRetro(RXNPlugin):
    """
    Predict retrosynthesis pathways using the RXN API.
    """

    cmd_pointer = None
    cmd = None

    # API
    api = None

    # Command
    input_smiles = None
    using_params = {}
    use_cache = False

    # Error messages
    err_msg_unknown = "Something went wrong"
    err_unresponsive_retries = "Server unresponsive, failed after 10 retries"
    err_msg_process_fail = "Failed to process"

    # Default parameters
    using_params_defaults = {
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

    # Cached result
    result_from_cache = None

    # Debugging: skip API call and use placeholder result
    debug = False

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

    def run(self):
        """
        Run the command.
        """

        # In case you're offline
        if not self.api:
            output_error(msg("err_api_offline"), return_val=False)
            return

        # Setup
        success = self._parse_input()
        if not success:
            return

        # Check if result is in cache
        input_smiles_key = canonicalize(self.input_smiles)
        if self.use_cache:
            self.result_from_cache = self.retrieve_result_cache(
                name=f"predict-retro-{self.using_params.get('ai_model')}",
                key=input_smiles_key,
            )

        # Not in cache -> run the job
        if not self.result_from_cache:

            # STEP 1: Launch job and get task ID
            if self.debug:
                task_id = "123"
            else:
                task_id = self._api_get_task_id()
                if not task_id:
                    return

            # STEP 2: Get list of candidate retrosynthesis pathways from RXN API
            if self.debug:
                retrosynthetic_paths = self._get_placeholder_result()
            else:
                retrosynthetic_paths = self._api_get_results(task_id)
                if not retrosynthetic_paths:
                    return

            # Save result in cache
            self.store_result_cache(
                name=f"predict-retro-{self.using_params.get('ai_model')}",
                key=input_smiles_key,
                payload=retrosynthetic_paths,
            )

        # In cache -> use result
        else:
            retrosynthetic_paths = self.result_from_cache

        # STEP 3: Simplify resuls for display
        reactions_dict_list = self._simplify_results(retrosynthetic_paths)
        if not reactions_dict_list:
            return

        # Save results as analysis records that can be merged
        # with the molecule working set in a follow up comand:
        # `enrich mols with analysis`
        save_result(
            create_analysis_record(
                smiles=self.input_smiles,
                toolkit=PLUGIN_KEY,
                function="predict_retrosynthesis",
                parameters=self.using_params,
                results=reactions_dict_list,
            ),
            self.cmd_pointer,
        )

        # STEP 4: Display results or return data
        if GLOBAL_SETTINGS["display"] == "api":
            df = self._create_df_output(reactions_dict_list)
            return df
        else:
            self._display_results(reactions_dict_list)

    def _parse_input(self):
        """
        Parse the pyparsing dictionary input.
        """
        # Parse input SMILES
        self.input_smiles = self.cmd.get("smiles", [None])[0]
        if not self.input_smiles or not valid_smiles(self.input_smiles):
            output_error(["Provided SMILES is invalid", f"Input SMILES: '{self.input_smiles}'"], return_val=False)
            return False
        # self.input_smiles = canonicalize(self.input_smiles) # Makes it harder to tie input and output together

        # Make sure input SMILES is not a reaction
        if len(self.input_smiles.split(".")) > 1:
            output_error(
                "Provided SMILES describes a reaction. Run <cmd>rxn predict reaction ?</cmd> to see how to predict reactions instead.",
                return_val=False,
            )
            return False

        # Parse parameters from the USING clause
        self.using_params = self.parse_using_params(self.cmd, self.using_params_defaults)

        # Parse use_cache clause
        self.use_cache = bool(self.cmd.get("use_cache"))

        return True

    def _api_get_task_id(self):
        """
        Launch job and return task id.
        Retry up to 10 times upon failure.
        """
        retries = 0
        max_retries = 10
        status = False
        job_response = None
        while status is False:
            try:
                if retries == 0:
                    spinner.start("Starting retrosynthesis")
                else:
                    spinner.start(f"Starting retrosynthesis - retry #{retries}")

                # Run query
                # raise Exception("This is a test error")
                job_response = self.api.predict_automatic_retrosynthesis(
                    self.input_smiles,
                    availability_pricing_threshold=self.using_params.get("availability_pricing_threshold"),
                    available_smiles=self.using_params.get("available_smiles"),
                    exclude_smiles=self.using_params.get("exclude_smiles"),
                    exclude_substructures=self.using_params.get("exclude_substructures"),
                    exclude_target_molecule=self.using_params.get("exclude_target_molecule"),
                    fap=self.using_params.get("fap"),
                    max_steps=self.using_params.get("max_steps"),
                    nbeams=self.using_params.get("nbeams"),
                    pruning_steps=self.using_params.get("pruning_steps"),
                    ai_model=self.using_params.get("ai_model"),
                )
                status = True

            # Fail - failed to connect
            except Exception as err:  # pylint: disable=broad-exception-caught
                sleep(2)
                retries = retries + 1
                if retries > max_retries:
                    spinner.stop()
                    output_error([self.err_unresponsive_retries, err], return_val=False)
                    return

        # Fail - empty response
        if not job_response or not job_response.get("response", {}).get("payload"):
            spinner.stop()
            output_error(["The server returned an empty response", job_response], return_val=False)
            return

        if not job_response.get("prediction_id"):
            spinner.stop()
            output_error(["The server failed to provide a prediction ID", job_response], return_val=False)
            return

        # Fail - error from RXN
        rxn_error_msg = job_response.get("response", {}).get("payload", {}).get("errorMessage")
        if rxn_error_msg:
            spinner.stop()
            output_error(rxn_error_msg, return_val=False)
            return

        task_id = job_response.get("prediction_id")
        return task_id

    def _api_get_results(self, task_id):
        """
        Check the status of the job every 10 seconds and return the results when ready.

        Retry up to 30 times upon failure (5 minutes max).
        """
        retries = 0
        wait_seconds = 10
        max_retries = 30  # 5 minutes max
        try_again = True
        response = None

        while try_again:
            try:
                if retries == 0:
                    spinner.start("Processing retrosynthesis")

                # Run query
                # Note: there's an occasional bug with RXN:
                # 'NoneType' object has no attribute 'get'
                # This is non-fatal and will be caught by the except block
                response = self.api.get_predict_automatic_retrosynthesis_results(task_id)

                # Job ready
                if response.get("status") == "SUCCESS":
                    try_again = False
                    retrosynthetic_paths = response.get("retrosynthetic_paths")
                    spinner.succeed("Done")
                    if not retrosynthetic_paths:
                        raise Exception("No retrosynthetic paths found")  # pylint: disable=broad-exception-raised
                    return retrosynthetic_paths

                # Job not ready yet - count down and check again
                if retries < max_retries:
                    retries = retries + 1
                    spinner.countdown(
                        seconds=wait_seconds,
                        msg="Processing retrosynthesis - next check in {sec} seconds",
                        stop_msg="Processing retrosynthesis",
                    )

                # Took too long, we give up
                else:
                    raise TimeoutError()

            # Server took too long
            except TimeoutError:
                total_time_waited = retries * wait_seconds
                minutes = total_time_waited // 60
                seconds = total_time_waited % 60
                time_str = f"{minutes} minutes and {seconds} seconds" if minutes > 0 else f"{seconds} seconds"
                spinner.stop()
                output_error(
                    [
                        "Server unresponsive",
                        f"Unable to complete processing after {time_str}",
                    ],
                    return_val=False,
                )

            # Other errors
            except Exception as err:  # pylint: disable=broad-exception-caught
                spinner.stop()
                output_error(["Something went wrong", err], return_val=False)

    def _simplify_results(self, retrosynthetic_paths):
        """
        Simplify the RXN API result for display.

        See __parse_retrosynthesis_tree below for details.
        """
        reactions_dict_list = []
        try:
            for tree in retrosynthetic_paths:
                reactions_dict = self.__parse_retrosynthesis_tree(tree)
                reactions_dict_list.append(reactions_dict)
            return reactions_dict_list

        except Exception as err:  # pylint: disable=broad-exception-caught
            output_error([self.err_msg_process_fail, err], return_val=False)

    def __parse_retrosynthesis_tree(self, tree: dict) -> list[str]:
        """
        Organize the molecules from the retrosynthesis tree in a hierarchical dictionary.

        {
            _confidence: 1.0,
            'value': 'HHH'
            'children': [
                'GGG',
                {
                    _confidence: 1.0,
                    'value': 'FFF'
                    'children': [
                        'EEE',
                        {
                            _confidence: 1.0,
                            'value': 'DDD'
                            'children': [
                                'AAA',
                                'BBB',
                                'CCC',
                            ]
                        },
                    ]
                },
            ]
        }
        """
        key = tree.get("smiles")

        if tree.get("children"):
            output = {}
            output["value"] = key
            output["_confidence"] = tree.get("confidence")
            output["children"] = []
            for branch in tree.get("children"):
                value = self.__parse_retrosynthesis_tree(branch)
                output["children"].append(value)
            return output

        else:
            return key

    def _get_print_str_reaction_tree(self, mol_list: list) -> str:
        """
        Get a printable representation of the reaction tree.
        """
        if GLOBAL_SETTINGS["display"] == "notebook":
            return self.__get_print_str_reaction_tree_jup(mol_list, level=0)
        else:
            return self.__get_print_str_reaction_tree_cli(mol_list, level=0, max_width=None)

    def __get_print_str_reaction_tree_jup(self, mol_list: list, level=0) -> str:
        """
        Create printable reaction tree for Jupyter Notebook output.
        """
        output = []
        box_tags = ["<div style='border: solid 1px #ccc; padding: 12px 16px'>", "</div>"]
        plus = "<span style='color: #ccc'>+ </span>"

        for item in mol_list:
            if isinstance(item, str):
                # Add smiles
                smi_val = item
                smi_val = f"<div>{plus}{item}</div>"
                output.append(smi_val)
            elif isinstance(item, dict):
                # Parse confidence
                confidence = item.get("_confidence")
                confidence_color = self.get_confidence_style(confidence, return_color=True)

                # Add parent smiles
                smi_val = f"<div style='color:{confidence_color}'>{plus}{item.get('value')}</div>"
                output.append(smi_val)

                # Open box
                output.append(box_tags[0])

                # Add children
                output.append(self.__get_print_str_reaction_tree_jup(item.get("children", []), level=level + 1))

                # Add confidence
                confidence_print_str_list = self.get_print_str_list__confidence(confidence)
                confidence_print_str = "<br>" + "".join(confidence_print_str_list)
                output.append(confidence_print_str)

                # Close box
                output.append(box_tags[1])

        # Enclose parent in box
        if level == 0:
            output = [box_tags[0]] + output + [box_tags[1]]

        return "\n".join(output)

    def __get_print_str_reaction_tree_cli(self, mol_list: list, level=0, max_width=None) -> str:
        """
        Create printable reaction tree for CLI output.

        Uses UTF box drawing characters:
        https://www.w3schools.com/charsets/ref_utf_box.asp

        For Jupyter output, we use HTML

        HHH
        ├───────────────
        │ + GGG
        │ + FFF
        │   ├───────────────
        │   │ + EEE
        │   │ + DDD
        │   │   ├───────────────
        │   │   │ + AAA
        │   │   │ + BBB
        │   │   │ + CCC
        │   │   │ ━━━━━━━━━━━━━━━━━━━━━━━━╸
        │   │   │ 100% confidence
        │   │   └───────────────
        │   │  ━━━━━━━━━━━━━━━━━━━━╸━━━━
        │   │  83.5% confidence
        │   └─────────────
        │   ━━━━━━━━━━━━━━━━━━━━━━━━╸
        │   100% confidence
        └─────────────
        """
        output = ""
        prepend_str = "│   " * (level)
        prepend_str_mol = prepend_str[:-2] + "+ " if prepend_str else ""
        prepend_str = f"<soft>{prepend_str}</soft>"
        prepend_str_mol = f"<soft>{prepend_str_mol}</soft>"
        max_width = get_print_width(True) if not max_width else max_width
        for item in mol_list:
            if isinstance(item, str):
                # Add smiles
                smi_val = self.__line_break_smiles(item, max_width, prepend_str)
                output += f"{prepend_str_mol}{smi_val}\n"
            elif isinstance(item, dict):
                # Parse confidence
                confidence = item.get("_confidence")
                confidence_style_tags = self.get_confidence_style(confidence)

                # Add parent smiles
                smi_val = self.__line_break_smiles(item.get("value"), max_width, prepend_str)
                output += f"{prepend_str_mol}{confidence_style_tags[0]}{smi_val}{confidence_style_tags[1]}\n"
                output += f"{prepend_str}<soft>├─────────────────────────</soft>\n"

                # Add children
                output += self.__get_print_str_reaction_tree_cli(
                    item.get("children", []), level=level + 1, max_width=max_width
                )

                # Add confidence
                confidence_print_str_list = self.get_print_str_list__confidence(confidence)
                for confidence_print_str in confidence_print_str_list:
                    output += f"{prepend_str}<soft>│ </soft>{confidence_print_str}\n"

                # Close box
                output += f"{prepend_str}<soft>└──────────────────────────</soft>\n"

        return output

    def __line_break_smiles(self, smiles, max_width, prepend_str):
        """
        Break up a smiles string in multiple lines with each line appropriately prepended.

        Parameters
        ----------
        smiles : str
            The smiles string to break up.
        max_width : int
            The maximum width of the line, including the prepended string.
        prepend_str : str
            The string to prepend to each line.

        Input:
        |  AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA

        Output:
        |  AAAAAAAAAAAAAAAAAAAAAA
        |  AAAAAAAAAAAAAAAAAAAAAA
        |  AAAAAAAAAAAAAAAA
        """
        max_width = max_width - len(strip_tags(prepend_str))
        if max_width and len(smiles) > max_width:
            smiles_lines = [smiles[i : i + max_width] for i in range(0, len(smiles), max_width)]
            return f"\n{prepend_str}".join(smiles_lines)

        return smiles

    def _create_df_output(self, reactions_dict_list):
        """
        Turns the list of reaction trees into a dataframe for API output.

        Input:
        [{
            '_confidence': 1.0,
            'value': 'HHH',
            'children': [
                'GGG',
                {
                    '_confidence': 0.7,
                    'value': 'FFF',
                    'children': [
                        'EEE',
                        {
                            '_confidence': 0.6,
                            'value': 'DDD',
                            'children': [
                                'AAA',
                                'BBB',
                                'CCC',
                            ]
                        },
                    ]
                },
            ]
        },
        {
            '_confidence': 1.0,
            'value': 'RRR',
            'children': [
                'QQQ',
                {
                    '_confidence': 0.7,
                    'value': 'PPP',
                    'children': [
                        'OOO',
                        {
                            '_confidence': 0.6,
                            'value': 'NNN',
                            'children': [
                                'KKK',
                                'LLL',
                                'MMM',
                            ]
                        },
                    ]
                },
            ]
        }
        ]

        Output:
            Reaction    Result    Confidence    Step -1 Result    Step -1 Confidence    Step -2 Result    Step -1 Confidence    Step -3 Result
            1           HHH       100%          GGG
            1           HHH       100%          FFF               70%                   EEE
            1           HHH       100%          FFF               70%                   DDD               60%                   AAA
            1           HHH       100%          FFF               70%                   DDD               60%                   BBB
            1           HHH       100%          FFF               70%                   DDD               60%                   CCC
            2           RRR       100%          QQQ
            2           RRR       100%          PPP               70%                   OOO
            2           RRR       100%          PPP               70%                   NNN               60%                   KKK
            2           RRR       100%          PPP               70%                   NNN               60%                   LLL
            2           RRR       100%          PPP               70%                   NNN               60%                   MMM
        """

        def _parse_tree(row_base, tree_or_smiles, index, level):
            new_row = row_base.copy() if row_base else {"reaction_path_index": index}
            rows_output = []

            # Compound value
            if isinstance(tree_or_smiles, str):
                smiles = tree_or_smiles
                new_row[f"compound [step {level}]"] = smiles
                rows_output.append(new_row)

            # Compound value with its own reaction
            elif isinstance(tree_or_smiles, dict):
                tree = tree_or_smiles
                smiles = tree.get("value")
                confidence = tree.get("_confidence")
                children = tree.get("children", [])
                new_row[f"compound [step {level}]"] = smiles
                new_row[f"confidence [step {level}]"] = confidence
                for child in children:
                    new_rows = _parse_tree(new_row, child, index, level=level - 1)
                    rows_output.extend(new_rows)

            return rows_output

        parsed_data = []
        for index, tree in enumerate(reactions_dict_list, start=1):
            parsed_data.extend(_parse_tree(None, tree, index, level=0))

        df = pd.DataFrame(parsed_data)
        df.rename(columns={"compound [step 0]": "result", "confidence [step 0]": "confidence"}, inplace=True)
        df.fillna("", inplace=True)
        return df

    def _display_results(self, reactions_dict_list):
        """
        Loop through the print strings of each reactions and print the total output.
        """

        output = []

        # Optional CACHED flag
        flag = self.get_flag("cached") if self.result_from_cache else ""

        # Assemble results
        for i, reactions_dict in enumerate(reactions_dict_list):
            reaction_print_str = self._get_print_str_reaction_tree([reactions_dict])
            output.append("")
            output.append(f"<h1>Reaction Path #{i + 1}{flag}</h1>")
            output.append(reaction_print_str)

        # Print - Jupyter Notebook
        if GLOBAL_SETTINGS["display"] == "notebook":
            # Display image of the input molecule
            jup_display_input_molecule(self.input_smiles, "smiles")
            # Display reaction paths
            display(HTML("\n".join(output)))

        # Print - CLI
        else:
            output_text("\n".join(output))

    def _get_placeholder_result(self):
        """
        Return a placeholder result for debugging purposes.
        """

        return [
            {
                "id": "6765983abf97167d064c7c77",
                "metadata": {},
                "embed": {},
                "computedFields": {},
                "createdOn": "2024-12-20T16:15:54.620+00:00",
                "createdBy": "system",
                "modifiedOn": "2024-12-20T16:15:54.620+00:00",
                "modifiedBy": "system",
                "moleculeId": "64c0834767a117001f2feca8",
                "retrosynthesisId": "67659828bf97167d064c7be4",
                "sequenceId": "6765983abf97167d064c7c6e",
                "projectId": "66ffd98620ad5b594360efd7",
                "smiles": "BrCCc1cccc2c(Br)c3ccccc3cc12",
                "confidence": 1.0,
                "confidenceTag": None,
                "rclass": "Hydroxy to bromo",
                "hasFeedback": False,
                "feedback": None,
                "children": [
                    {
                        "id": "6765983abf97167d064c7c6f",
                        "metadata": {},
                        "embed": {},
                        "computedFields": {},
                        "createdOn": "2024-12-20T16:15:54.593+00:00",
                        "createdBy": "system",
                        "modifiedOn": "2024-12-20T16:15:54.593+00:00",
                        "modifiedBy": "system",
                        "moleculeId": "5eb31da4759cc0000175051c",
                        "retrosynthesisId": "67659828bf97167d064c7be4",
                        "sequenceId": "6765983abf97167d064c7c6e",
                        "projectId": "66ffd98620ad5b594360efd7",
                        "smiles": "BrC(Br)(Br)Br",
                        "confidence": 1.0,
                        "confidenceTag": None,
                        "rclass": "Undefined",
                        "hasFeedback": False,
                        "feedback": None,
                        "children": [],
                        "metaData": {"borderColor": "#28a30d", "count": 1},
                        "count": 1,
                        "custom": False,
                        "isConfidenceComputed": True,
                        "isFromFile": False,
                        "isTouched": False,
                        "isThermal": False,
                        "isPhotochemical": False,
                        "isExpandable": False,
                        "isEditable": False,
                        "isCommercial": True,
                        "isDeletable": False,
                        "isChildrenEditable": False,
                        "isChildrenDeletable": False,
                    },
                    {
                        "id": "6765983abf97167d064c7c70",
                        "metadata": {},
                        "embed": {},
                        "computedFields": {},
                        "createdOn": "2024-12-20T16:15:54.597+00:00",
                        "createdBy": "system",
                        "modifiedOn": "2024-12-20T16:15:54.597+00:00",
                        "modifiedBy": "system",
                        "moleculeId": "5eb27aae759cc0000174d3f8",
                        "retrosynthesisId": "67659828bf97167d064c7be4",
                        "sequenceId": "6765983abf97167d064c7c6e",
                        "projectId": "66ffd98620ad5b594360efd7",
                        "smiles": "ClCCl",
                        "confidence": 1.0,
                        "confidenceTag": None,
                        "rclass": "Undefined",
                        "hasFeedback": False,
                        "feedback": None,
                        "children": [],
                        "metaData": {"borderColor": "#28a30d", "count": 1},
                        "count": 1,
                        "custom": False,
                        "isConfidenceComputed": True,
                        "isFromFile": False,
                        "isTouched": False,
                        "isThermal": False,
                        "isPhotochemical": False,
                        "isExpandable": False,
                        "isEditable": False,
                        "isCommercial": True,
                        "isDeletable": False,
                        "isChildrenEditable": False,
                        "isChildrenDeletable": False,
                    },
                    {
                        "id": "6765983abf97167d064c7c76",
                        "metadata": {},
                        "embed": {},
                        "computedFields": {},
                        "createdOn": "2024-12-20T16:15:54.616+00:00",
                        "createdBy": "system",
                        "modifiedOn": "2024-12-20T16:15:54.616+00:00",
                        "modifiedBy": "system",
                        "moleculeId": "64c0835c67a117001f2fecc6",
                        "retrosynthesisId": "67659828bf97167d064c7be4",
                        "sequenceId": "6765983abf97167d064c7c6e",
                        "projectId": "66ffd98620ad5b594360efd7",
                        "smiles": "OCCc1cccc2c(Br)c3ccccc3cc12",
                        "confidence": 0.835,
                        "confidenceTag": None,
                        "rclass": "Bromination",
                        "hasFeedback": False,
                        "feedback": None,
                        "children": [
                            {
                                "id": "6765983abf97167d064c7c71",
                                "metadata": {},
                                "embed": {},
                                "computedFields": {},
                                "createdOn": "2024-12-20T16:15:54.600+00:00",
                                "createdBy": "system",
                                "modifiedOn": "2024-12-20T16:15:54.600+00:00",
                                "modifiedBy": "system",
                                "moleculeId": "5eb30c1d759cc0000174ffda",
                                "retrosynthesisId": "67659828bf97167d064c7be4",
                                "sequenceId": "6765983abf97167d064c7c6e",
                                "projectId": "66ffd98620ad5b594360efd7",
                                "smiles": "O=C1CCC(=O)N1Br",
                                "confidence": 1.0,
                                "confidenceTag": None,
                                "rclass": "Undefined",
                                "hasFeedback": False,
                                "feedback": None,
                                "children": [],
                                "metaData": {"borderColor": "#28a30d", "count": 1},
                                "count": 1,
                                "custom": False,
                                "isConfidenceComputed": True,
                                "isFromFile": False,
                                "isTouched": False,
                                "isThermal": False,
                                "isPhotochemical": False,
                                "isExpandable": False,
                                "isEditable": False,
                                "isCommercial": True,
                                "isDeletable": False,
                                "isChildrenEditable": False,
                                "isChildrenDeletable": False,
                            },
                            {
                                "id": "6765983abf97167d064c7c75",
                                "metadata": {},
                                "embed": {},
                                "computedFields": {},
                                "createdOn": "2024-12-20T16:15:54.613+00:00",
                                "createdBy": "system",
                                "modifiedOn": "2024-12-20T16:15:54.613+00:00",
                                "modifiedBy": "system",
                                "moleculeId": "64c0835c67a117001f2fecd0",
                                "retrosynthesisId": "67659828bf97167d064c7be4",
                                "sequenceId": "6765983abf97167d064c7c6e",
                                "projectId": "66ffd98620ad5b594360efd7",
                                "smiles": "OCCc1cccc2cc3ccccc3cc12",
                                "confidence": 1.0,
                                "confidenceTag": None,
                                "rclass": "Ester to alcohol reduction",
                                "hasFeedback": False,
                                "feedback": None,
                                "children": [
                                    {
                                        "id": "6765983abf97167d064c7c72",
                                        "metadata": {},
                                        "embed": {},
                                        "computedFields": {},
                                        "createdOn": "2024-12-20T16:15:54.603+00:00",
                                        "createdBy": "system",
                                        "modifiedOn": "2024-12-20T16:15:54.603+00:00",
                                        "modifiedBy": "system",
                                        "moleculeId": "5eb27acc759cc0000174d4b3",
                                        "retrosynthesisId": "67659828bf97167d064c7be4",
                                        "sequenceId": "6765983abf97167d064c7c6e",
                                        "projectId": "66ffd98620ad5b594360efd7",
                                        "smiles": "C1CCOC1",
                                        "confidence": 1.0,
                                        "confidenceTag": None,
                                        "rclass": "Undefined",
                                        "hasFeedback": False,
                                        "feedback": None,
                                        "children": [],
                                        "metaData": {"borderColor": "#28a30d", "count": 1},
                                        "count": 1,
                                        "custom": False,
                                        "isConfidenceComputed": True,
                                        "isFromFile": False,
                                        "isTouched": False,
                                        "isThermal": False,
                                        "isPhotochemical": False,
                                        "isExpandable": False,
                                        "isEditable": False,
                                        "isCommercial": True,
                                        "isDeletable": False,
                                        "isChildrenEditable": False,
                                        "isChildrenDeletable": False,
                                    },
                                    {
                                        "id": "6765983abf97167d064c7c73",
                                        "metadata": {},
                                        "embed": {},
                                        "computedFields": {},
                                        "createdOn": "2024-12-20T16:15:54.606+00:00",
                                        "createdBy": "system",
                                        "modifiedOn": "2024-12-20T16:15:54.606+00:00",
                                        "modifiedBy": "system",
                                        "moleculeId": "64c0835c67a117001f2fecd1",
                                        "retrosynthesisId": "67659828bf97167d064c7be4",
                                        "sequenceId": "6765983abf97167d064c7c6e",
                                        "projectId": "66ffd98620ad5b594360efd7",
                                        "smiles": "CCOC(=O)Cc1cccc2cc3ccccc3cc12",
                                        "confidence": 1.0,
                                        "confidenceTag": None,
                                        "rclass": "Undefined",
                                        "hasFeedback": False,
                                        "feedback": None,
                                        "children": [],
                                        "metaData": {
                                            "molecule2commercial": False,
                                            "molecule2expandable": True,
                                            "borderColor": "#ce4e04",
                                            "count": 1,
                                        },
                                        "count": 1,
                                        "custom": False,
                                        "isConfidenceComputed": True,
                                        "isFromFile": False,
                                        "isTouched": False,
                                        "isThermal": False,
                                        "isPhotochemical": False,
                                        "isExpandable": False,
                                        "isEditable": False,
                                        "isCommercial": False,
                                        "isDeletable": False,
                                        "isChildrenEditable": False,
                                        "isChildrenDeletable": False,
                                    },
                                    {
                                        "id": "6765983abf97167d064c7c74",
                                        "metadata": {},
                                        "embed": {},
                                        "computedFields": {},
                                        "createdOn": "2024-12-20T16:15:54.610+00:00",
                                        "createdBy": "system",
                                        "modifiedOn": "2024-12-20T16:15:54.610+00:00",
                                        "modifiedBy": "system",
                                        "moleculeId": "5fad29008937a90001252a8c",
                                        "retrosynthesisId": "67659828bf97167d064c7be4",
                                        "sequenceId": "6765983abf97167d064c7c6e",
                                        "projectId": "66ffd98620ad5b594360efd7",
                                        "smiles": "[Li][AlH4]",
                                        "confidence": 1.0,
                                        "confidenceTag": None,
                                        "rclass": "Undefined",
                                        "hasFeedback": False,
                                        "feedback": None,
                                        "children": [],
                                        "metaData": {"borderColor": "#28a30d", "count": 1},
                                        "count": 1,
                                        "custom": False,
                                        "isConfidenceComputed": True,
                                        "isFromFile": False,
                                        "isTouched": False,
                                        "isThermal": False,
                                        "isPhotochemical": False,
                                        "isExpandable": False,
                                        "isEditable": False,
                                        "isCommercial": True,
                                        "isDeletable": False,
                                        "isChildrenEditable": False,
                                        "isChildrenDeletable": False,
                                    },
                                ],
                                "metaData": {"molecule2commercial": False, "molecule2expandable": True, "count": 1},
                                "count": 1,
                                "custom": False,
                                "isConfidenceComputed": True,
                                "isFromFile": False,
                                "isTouched": False,
                                "isThermal": False,
                                "isPhotochemical": False,
                                "isExpandable": False,
                                "isEditable": False,
                                "isCommercial": False,
                                "isDeletable": False,
                                "isChildrenEditable": False,
                                "isChildrenDeletable": False,
                            },
                        ],
                        "metaData": {"molecule2commercial": False, "molecule2expandable": True, "count": 1},
                        "count": 1,
                        "custom": False,
                        "isConfidenceComputed": True,
                        "isFromFile": False,
                        "isTouched": False,
                        "isThermal": False,
                        "isPhotochemical": False,
                        "isExpandable": False,
                        "isEditable": False,
                        "isCommercial": False,
                        "isDeletable": False,
                        "isChildrenEditable": False,
                        "isChildrenDeletable": False,
                    },
                ],
                "metaData": {"molecule2commercial": False, "molecule2expandable": True},
                "count": None,
                "custom": False,
                "isConfidenceComputed": True,
                "isFromFile": False,
                "isTouched": False,
                "isThermal": False,
                "isPhotochemical": False,
                "isExpandable": False,
                "isEditable": False,
                "isCommercial": False,
                "isDeletable": False,
                "isChildrenEditable": False,
                "isChildrenDeletable": False,
            },
            {
                "id": "6765983abf97167d064c7c81",
                "metadata": {},
                "embed": {},
                "computedFields": {},
                "createdOn": "2024-12-20T16:15:54.665+00:00",
                "createdBy": "system",
                "modifiedOn": "2024-12-20T16:15:54.665+00:00",
                "modifiedBy": "system",
                "moleculeId": "64c0834767a117001f2feca8",
                "retrosynthesisId": "67659828bf97167d064c7be4",
                "sequenceId": "6765983abf97167d064c7c78",
                "projectId": "66ffd98620ad5b594360efd7",
                "smiles": "BrCCc1cccc2c(Br)c3ccccc3cc12",
                "confidence": 1.0,
                "confidenceTag": None,
                "rclass": "Hydroxy to bromo",
                "hasFeedback": False,
                "feedback": None,
                "children": [
                    {
                        "id": "6765983abf97167d064c7c79",
                        "metadata": {},
                        "embed": {},
                        "computedFields": {},
                        "createdOn": "2024-12-20T16:15:54.639+00:00",
                        "createdBy": "system",
                        "modifiedOn": "2024-12-20T16:15:54.639+00:00",
                        "modifiedBy": "system",
                        "moleculeId": "5eb31da4759cc0000175051c",
                        "retrosynthesisId": "67659828bf97167d064c7be4",
                        "sequenceId": "6765983abf97167d064c7c78",
                        "projectId": "66ffd98620ad5b594360efd7",
                        "smiles": "BrC(Br)(Br)Br",
                        "confidence": 1.0,
                        "confidenceTag": None,
                        "rclass": "Undefined",
                        "hasFeedback": False,
                        "feedback": None,
                        "children": [],
                        "metaData": {"borderColor": "#28a30d", "count": 1},
                        "count": 1,
                        "custom": False,
                        "isConfidenceComputed": True,
                        "isFromFile": False,
                        "isTouched": False,
                        "isThermal": False,
                        "isPhotochemical": False,
                        "isExpandable": False,
                        "isEditable": False,
                        "isCommercial": True,
                        "isDeletable": False,
                        "isChildrenEditable": False,
                        "isChildrenDeletable": False,
                    },
                    {
                        "id": "6765983abf97167d064c7c7a",
                        "metadata": {},
                        "embed": {},
                        "computedFields": {},
                        "createdOn": "2024-12-20T16:15:54.643+00:00",
                        "createdBy": "system",
                        "modifiedOn": "2024-12-20T16:15:54.643+00:00",
                        "modifiedBy": "system",
                        "moleculeId": "5eb27aae759cc0000174d3f8",
                        "retrosynthesisId": "67659828bf97167d064c7be4",
                        "sequenceId": "6765983abf97167d064c7c78",
                        "projectId": "66ffd98620ad5b594360efd7",
                        "smiles": "ClCCl",
                        "confidence": 1.0,
                        "confidenceTag": None,
                        "rclass": "Undefined",
                        "hasFeedback": False,
                        "feedback": None,
                        "children": [],
                        "metaData": {"borderColor": "#28a30d", "count": 1},
                        "count": 1,
                        "custom": False,
                        "isConfidenceComputed": True,
                        "isFromFile": False,
                        "isTouched": False,
                        "isThermal": False,
                        "isPhotochemical": False,
                        "isExpandable": False,
                        "isEditable": False,
                        "isCommercial": True,
                        "isDeletable": False,
                        "isChildrenEditable": False,
                        "isChildrenDeletable": False,
                    },
                    {
                        "id": "6765983abf97167d064c7c80",
                        "metadata": {},
                        "embed": {},
                        "computedFields": {},
                        "createdOn": "2024-12-20T16:15:54.661+00:00",
                        "createdBy": "system",
                        "modifiedOn": "2024-12-20T16:15:54.661+00:00",
                        "modifiedBy": "system",
                        "moleculeId": "64c0835c67a117001f2fecc6",
                        "retrosynthesisId": "67659828bf97167d064c7be4",
                        "sequenceId": "6765983abf97167d064c7c78",
                        "projectId": "66ffd98620ad5b594360efd7",
                        "smiles": "OCCc1cccc2c(Br)c3ccccc3cc12",
                        "confidence": 0.835,
                        "confidenceTag": None,
                        "rclass": "Bromination",
                        "hasFeedback": False,
                        "feedback": None,
                        "children": [
                            {
                                "id": "6765983abf97167d064c7c7b",
                                "metadata": {},
                                "embed": {},
                                "computedFields": {},
                                "createdOn": "2024-12-20T16:15:54.646+00:00",
                                "createdBy": "system",
                                "modifiedOn": "2024-12-20T16:15:54.646+00:00",
                                "modifiedBy": "system",
                                "moleculeId": "5eb30c1d759cc0000174ffda",
                                "retrosynthesisId": "67659828bf97167d064c7be4",
                                "sequenceId": "6765983abf97167d064c7c78",
                                "projectId": "66ffd98620ad5b594360efd7",
                                "smiles": "O=C1CCC(=O)N1Br",
                                "confidence": 1.0,
                                "confidenceTag": None,
                                "rclass": "Undefined",
                                "hasFeedback": False,
                                "feedback": None,
                                "children": [],
                                "metaData": {"borderColor": "#28a30d", "count": 1},
                                "count": 1,
                                "custom": False,
                                "isConfidenceComputed": True,
                                "isFromFile": False,
                                "isTouched": False,
                                "isThermal": False,
                                "isPhotochemical": False,
                                "isExpandable": False,
                                "isEditable": False,
                                "isCommercial": True,
                                "isDeletable": False,
                                "isChildrenEditable": False,
                                "isChildrenDeletable": False,
                            },
                            {
                                "id": "6765983abf97167d064c7c7f",
                                "metadata": {},
                                "embed": {},
                                "computedFields": {},
                                "createdOn": "2024-12-20T16:15:54.658+00:00",
                                "createdBy": "system",
                                "modifiedOn": "2024-12-20T16:15:54.658+00:00",
                                "modifiedBy": "system",
                                "moleculeId": "64c0835c67a117001f2fecd0",
                                "retrosynthesisId": "67659828bf97167d064c7be4",
                                "sequenceId": "6765983abf97167d064c7c78",
                                "projectId": "66ffd98620ad5b594360efd7",
                                "smiles": "OCCc1cccc2cc3ccccc3cc12",
                                "confidence": 1.0,
                                "confidenceTag": None,
                                "rclass": "Carboxylic acid to alcohol reduction",
                                "hasFeedback": False,
                                "feedback": None,
                                "children": [
                                    {
                                        "id": "6765983abf97167d064c7c7c",
                                        "metadata": {},
                                        "embed": {},
                                        "computedFields": {},
                                        "createdOn": "2024-12-20T16:15:54.649+00:00",
                                        "createdBy": "system",
                                        "modifiedOn": "2024-12-20T16:15:54.649+00:00",
                                        "modifiedBy": "system",
                                        "moleculeId": "5eb2f9a4759cc0000174f571",
                                        "retrosynthesisId": "67659828bf97167d064c7be4",
                                        "sequenceId": "6765983abf97167d064c7c78",
                                        "projectId": "66ffd98620ad5b594360efd7",
                                        "smiles": "B",
                                        "confidence": 1.0,
                                        "confidenceTag": None,
                                        "rclass": "Undefined",
                                        "hasFeedback": False,
                                        "feedback": None,
                                        "children": [],
                                        "metaData": {"borderColor": "#28a30d", "count": 1},
                                        "count": 1,
                                        "custom": False,
                                        "isConfidenceComputed": True,
                                        "isFromFile": False,
                                        "isTouched": False,
                                        "isThermal": False,
                                        "isPhotochemical": False,
                                        "isExpandable": False,
                                        "isEditable": False,
                                        "isCommercial": True,
                                        "isDeletable": False,
                                        "isChildrenEditable": False,
                                        "isChildrenDeletable": False,
                                    },
                                    {
                                        "id": "6765983abf97167d064c7c7d",
                                        "metadata": {},
                                        "embed": {},
                                        "computedFields": {},
                                        "createdOn": "2024-12-20T16:15:54.652+00:00",
                                        "createdBy": "system",
                                        "modifiedOn": "2024-12-20T16:15:54.652+00:00",
                                        "modifiedBy": "system",
                                        "moleculeId": "5eb27acc759cc0000174d4b3",
                                        "retrosynthesisId": "67659828bf97167d064c7be4",
                                        "sequenceId": "6765983abf97167d064c7c78",
                                        "projectId": "66ffd98620ad5b594360efd7",
                                        "smiles": "C1CCOC1",
                                        "confidence": 1.0,
                                        "confidenceTag": None,
                                        "rclass": "Undefined",
                                        "hasFeedback": False,
                                        "feedback": None,
                                        "children": [],
                                        "metaData": {"borderColor": "#28a30d", "count": 1},
                                        "count": 1,
                                        "custom": False,
                                        "isConfidenceComputed": True,
                                        "isFromFile": False,
                                        "isTouched": False,
                                        "isThermal": False,
                                        "isPhotochemical": False,
                                        "isExpandable": False,
                                        "isEditable": False,
                                        "isCommercial": True,
                                        "isDeletable": False,
                                        "isChildrenEditable": False,
                                        "isChildrenDeletable": False,
                                    },
                                    {
                                        "id": "6765983abf97167d064c7c7e",
                                        "metadata": {},
                                        "embed": {},
                                        "computedFields": {},
                                        "createdOn": "2024-12-20T16:15:54.655+00:00",
                                        "createdBy": "system",
                                        "modifiedOn": "2024-12-20T16:15:54.655+00:00",
                                        "modifiedBy": "system",
                                        "moleculeId": "64c0835c67a117001f2feccf",
                                        "retrosynthesisId": "67659828bf97167d064c7be4",
                                        "sequenceId": "6765983abf97167d064c7c78",
                                        "projectId": "66ffd98620ad5b594360efd7",
                                        "smiles": "O=C(O)Cc1cccc2cc3ccccc3cc12",
                                        "confidence": 1.0,
                                        "confidenceTag": None,
                                        "rclass": "Undefined",
                                        "hasFeedback": False,
                                        "feedback": None,
                                        "children": [],
                                        "metaData": {
                                            "molecule2commercial": False,
                                            "molecule2expandable": True,
                                            "borderColor": "#ce4e04",
                                            "count": 1,
                                        },
                                        "count": 1,
                                        "custom": False,
                                        "isConfidenceComputed": True,
                                        "isFromFile": False,
                                        "isTouched": False,
                                        "isThermal": False,
                                        "isPhotochemical": False,
                                        "isExpandable": False,
                                        "isEditable": False,
                                        "isCommercial": False,
                                        "isDeletable": False,
                                        "isChildrenEditable": False,
                                        "isChildrenDeletable": False,
                                    },
                                ],
                                "metaData": {"molecule2commercial": False, "molecule2expandable": True, "count": 1},
                                "count": 1,
                                "custom": False,
                                "isConfidenceComputed": True,
                                "isFromFile": False,
                                "isTouched": False,
                                "isThermal": False,
                                "isPhotochemical": False,
                                "isExpandable": False,
                                "isEditable": False,
                                "isCommercial": False,
                                "isDeletable": False,
                                "isChildrenEditable": False,
                                "isChildrenDeletable": False,
                            },
                        ],
                        "metaData": {"molecule2commercial": False, "molecule2expandable": True, "count": 1},
                        "count": 1,
                        "custom": False,
                        "isConfidenceComputed": True,
                        "isFromFile": False,
                        "isTouched": False,
                        "isThermal": False,
                        "isPhotochemical": False,
                        "isExpandable": False,
                        "isEditable": False,
                        "isCommercial": False,
                        "isDeletable": False,
                        "isChildrenEditable": False,
                        "isChildrenDeletable": False,
                    },
                ],
                "metaData": {"molecule2commercial": False, "molecule2expandable": True},
                "count": None,
                "custom": False,
                "isConfidenceComputed": True,
                "isFromFile": False,
                "isTouched": False,
                "isThermal": False,
                "isPhotochemical": False,
                "isExpandable": False,
                "isEditable": False,
                "isCommercial": False,
                "isDeletable": False,
                "isChildrenEditable": False,
                "isChildrenDeletable": False,
            },
            {
                "id": "6765983abf97167d064c7c8b",
                "metadata": {},
                "embed": {},
                "computedFields": {},
                "createdOn": "2024-12-20T16:15:54.711+00:00",
                "createdBy": "system",
                "modifiedOn": "2024-12-20T16:15:54.711+00:00",
                "modifiedBy": "system",
                "moleculeId": "64c0834767a117001f2feca8",
                "retrosynthesisId": "67659828bf97167d064c7be4",
                "sequenceId": "6765983abf97167d064c7c82",
                "projectId": "66ffd98620ad5b594360efd7",
                "smiles": "BrCCc1cccc2c(Br)c3ccccc3cc12",
                "confidence": 1.0,
                "confidenceTag": None,
                "rclass": "Hydroxy to bromo",
                "hasFeedback": False,
                "feedback": None,
                "children": [
                    {
                        "id": "6765983abf97167d064c7c83",
                        "metadata": {},
                        "embed": {},
                        "computedFields": {},
                        "createdOn": "2024-12-20T16:15:54.685+00:00",
                        "createdBy": "system",
                        "modifiedOn": "2024-12-20T16:15:54.685+00:00",
                        "modifiedBy": "system",
                        "moleculeId": "5eb31da4759cc0000175051c",
                        "retrosynthesisId": "67659828bf97167d064c7be4",
                        "sequenceId": "6765983abf97167d064c7c82",
                        "projectId": "66ffd98620ad5b594360efd7",
                        "smiles": "BrC(Br)(Br)Br",
                        "confidence": 1.0,
                        "confidenceTag": None,
                        "rclass": "Undefined",
                        "hasFeedback": False,
                        "feedback": None,
                        "children": [],
                        "metaData": {"borderColor": "#28a30d", "count": 1},
                        "count": 1,
                        "custom": False,
                        "isConfidenceComputed": True,
                        "isFromFile": False,
                        "isTouched": False,
                        "isThermal": False,
                        "isPhotochemical": False,
                        "isExpandable": False,
                        "isEditable": False,
                        "isCommercial": True,
                        "isDeletable": False,
                        "isChildrenEditable": False,
                        "isChildrenDeletable": False,
                    },
                    {
                        "id": "6765983abf97167d064c7c84",
                        "metadata": {},
                        "embed": {},
                        "computedFields": {},
                        "createdOn": "2024-12-20T16:15:54.688+00:00",
                        "createdBy": "system",
                        "modifiedOn": "2024-12-20T16:15:54.688+00:00",
                        "modifiedBy": "system",
                        "moleculeId": "5eb27aae759cc0000174d3f8",
                        "retrosynthesisId": "67659828bf97167d064c7be4",
                        "sequenceId": "6765983abf97167d064c7c82",
                        "projectId": "66ffd98620ad5b594360efd7",
                        "smiles": "ClCCl",
                        "confidence": 1.0,
                        "confidenceTag": None,
                        "rclass": "Undefined",
                        "hasFeedback": False,
                        "feedback": None,
                        "children": [],
                        "metaData": {"borderColor": "#28a30d", "count": 1},
                        "count": 1,
                        "custom": False,
                        "isConfidenceComputed": True,
                        "isFromFile": False,
                        "isTouched": False,
                        "isThermal": False,
                        "isPhotochemical": False,
                        "isExpandable": False,
                        "isEditable": False,
                        "isCommercial": True,
                        "isDeletable": False,
                        "isChildrenEditable": False,
                        "isChildrenDeletable": False,
                    },
                    {
                        "id": "6765983abf97167d064c7c8a",
                        "metadata": {},
                        "embed": {},
                        "computedFields": {},
                        "createdOn": "2024-12-20T16:15:54.707+00:00",
                        "createdBy": "system",
                        "modifiedOn": "2024-12-20T16:15:54.707+00:00",
                        "modifiedBy": "system",
                        "moleculeId": "64c0835c67a117001f2fecc6",
                        "retrosynthesisId": "67659828bf97167d064c7be4",
                        "sequenceId": "6765983abf97167d064c7c82",
                        "projectId": "66ffd98620ad5b594360efd7",
                        "smiles": "OCCc1cccc2c(Br)c3ccccc3cc12",
                        "confidence": 0.835,
                        "confidenceTag": None,
                        "rclass": "Bromination",
                        "hasFeedback": False,
                        "feedback": None,
                        "children": [
                            {
                                "id": "6765983abf97167d064c7c85",
                                "metadata": {},
                                "embed": {},
                                "computedFields": {},
                                "createdOn": "2024-12-20T16:15:54.691+00:00",
                                "createdBy": "system",
                                "modifiedOn": "2024-12-20T16:15:54.691+00:00",
                                "modifiedBy": "system",
                                "moleculeId": "5eb30c1d759cc0000174ffda",
                                "retrosynthesisId": "67659828bf97167d064c7be4",
                                "sequenceId": "6765983abf97167d064c7c82",
                                "projectId": "66ffd98620ad5b594360efd7",
                                "smiles": "O=C1CCC(=O)N1Br",
                                "confidence": 1.0,
                                "confidenceTag": None,
                                "rclass": "Undefined",
                                "hasFeedback": False,
                                "feedback": None,
                                "children": [],
                                "metaData": {"borderColor": "#28a30d", "count": 1},
                                "count": 1,
                                "custom": False,
                                "isConfidenceComputed": True,
                                "isFromFile": False,
                                "isTouched": False,
                                "isThermal": False,
                                "isPhotochemical": False,
                                "isExpandable": False,
                                "isEditable": False,
                                "isCommercial": True,
                                "isDeletable": False,
                                "isChildrenEditable": False,
                                "isChildrenDeletable": False,
                            },
                            {
                                "id": "6765983abf97167d064c7c89",
                                "metadata": {},
                                "embed": {},
                                "computedFields": {},
                                "createdOn": "2024-12-20T16:15:54.704+00:00",
                                "createdBy": "system",
                                "modifiedOn": "2024-12-20T16:15:54.704+00:00",
                                "modifiedBy": "system",
                                "moleculeId": "64c0835c67a117001f2fecd0",
                                "retrosynthesisId": "67659828bf97167d064c7be4",
                                "sequenceId": "6765983abf97167d064c7c82",
                                "projectId": "66ffd98620ad5b594360efd7",
                                "smiles": "OCCc1cccc2cc3ccccc3cc12",
                                "confidence": 1.0,
                                "confidenceTag": None,
                                "rclass": "Alkene hydration",
                                "hasFeedback": False,
                                "feedback": None,
                                "children": [
                                    {
                                        "id": "6765983abf97167d064c7c86",
                                        "metadata": {},
                                        "embed": {},
                                        "computedFields": {},
                                        "createdOn": "2024-12-20T16:15:54.694+00:00",
                                        "createdBy": "system",
                                        "modifiedOn": "2024-12-20T16:15:54.694+00:00",
                                        "modifiedBy": "system",
                                        "moleculeId": "5eb34bd2759cc00001752d1f",
                                        "retrosynthesisId": "67659828bf97167d064c7be4",
                                        "sequenceId": "6765983abf97167d064c7c82",
                                        "projectId": "66ffd98620ad5b594360efd7",
                                        "smiles": "B1C2CCCC1CCC2",
                                        "confidence": 1.0,
                                        "confidenceTag": None,
                                        "rclass": "Undefined",
                                        "hasFeedback": False,
                                        "feedback": None,
                                        "children": [],
                                        "metaData": {"borderColor": "#28a30d", "count": 1},
                                        "count": 1,
                                        "custom": False,
                                        "isConfidenceComputed": True,
                                        "isFromFile": False,
                                        "isTouched": False,
                                        "isThermal": False,
                                        "isPhotochemical": False,
                                        "isExpandable": False,
                                        "isEditable": False,
                                        "isCommercial": True,
                                        "isDeletable": False,
                                        "isChildrenEditable": False,
                                        "isChildrenDeletable": False,
                                    },
                                    {
                                        "id": "6765983abf97167d064c7c87",
                                        "metadata": {},
                                        "embed": {},
                                        "computedFields": {},
                                        "createdOn": "2024-12-20T16:15:54.698+00:00",
                                        "createdBy": "system",
                                        "modifiedOn": "2024-12-20T16:15:54.698+00:00",
                                        "modifiedBy": "system",
                                        "moleculeId": "5eb27acc759cc0000174d4b3",
                                        "retrosynthesisId": "67659828bf97167d064c7be4",
                                        "sequenceId": "6765983abf97167d064c7c82",
                                        "projectId": "66ffd98620ad5b594360efd7",
                                        "smiles": "C1CCOC1",
                                        "confidence": 1.0,
                                        "confidenceTag": None,
                                        "rclass": "Undefined",
                                        "hasFeedback": False,
                                        "feedback": None,
                                        "children": [],
                                        "metaData": {"borderColor": "#28a30d", "count": 1},
                                        "count": 1,
                                        "custom": False,
                                        "isConfidenceComputed": True,
                                        "isFromFile": False,
                                        "isTouched": False,
                                        "isThermal": False,
                                        "isPhotochemical": False,
                                        "isExpandable": False,
                                        "isEditable": False,
                                        "isCommercial": True,
                                        "isDeletable": False,
                                        "isChildrenEditable": False,
                                        "isChildrenDeletable": False,
                                    },
                                    {
                                        "id": "6765983abf97167d064c7c88",
                                        "metadata": {},
                                        "embed": {},
                                        "computedFields": {},
                                        "createdOn": "2024-12-20T16:15:54.701+00:00",
                                        "createdBy": "system",
                                        "modifiedOn": "2024-12-20T16:15:54.701+00:00",
                                        "modifiedBy": "system",
                                        "moleculeId": "64c0835c67a117001f2fecd2",
                                        "retrosynthesisId": "67659828bf97167d064c7be4",
                                        "sequenceId": "6765983abf97167d064c7c82",
                                        "projectId": "66ffd98620ad5b594360efd7",
                                        "smiles": "C=Cc1cccc2cc3ccccc3cc12",
                                        "confidence": 1.0,
                                        "confidenceTag": None,
                                        "rclass": "Undefined",
                                        "hasFeedback": False,
                                        "feedback": None,
                                        "children": [],
                                        "metaData": {
                                            "molecule2commercial": False,
                                            "molecule2expandable": True,
                                            "borderColor": "#ce4e04",
                                            "count": 1,
                                        },
                                        "count": 1,
                                        "custom": False,
                                        "isConfidenceComputed": True,
                                        "isFromFile": False,
                                        "isTouched": False,
                                        "isThermal": False,
                                        "isPhotochemical": False,
                                        "isExpandable": False,
                                        "isEditable": False,
                                        "isCommercial": False,
                                        "isDeletable": False,
                                        "isChildrenEditable": False,
                                        "isChildrenDeletable": False,
                                    },
                                ],
                                "metaData": {"molecule2commercial": False, "molecule2expandable": True, "count": 1},
                                "count": 1,
                                "custom": False,
                                "isConfidenceComputed": True,
                                "isFromFile": False,
                                "isTouched": False,
                                "isThermal": False,
                                "isPhotochemical": False,
                                "isExpandable": False,
                                "isEditable": False,
                                "isCommercial": False,
                                "isDeletable": False,
                                "isChildrenEditable": False,
                                "isChildrenDeletable": False,
                            },
                        ],
                        "metaData": {"molecule2commercial": False, "molecule2expandable": True, "count": 1},
                        "count": 1,
                        "custom": False,
                        "isConfidenceComputed": True,
                        "isFromFile": False,
                        "isTouched": False,
                        "isThermal": False,
                        "isPhotochemical": False,
                        "isExpandable": False,
                        "isEditable": False,
                        "isCommercial": False,
                        "isDeletable": False,
                        "isChildrenEditable": False,
                        "isChildrenDeletable": False,
                    },
                ],
                "metaData": {"molecule2commercial": False, "molecule2expandable": True},
                "count": None,
                "custom": False,
                "isConfidenceComputed": True,
                "isFromFile": False,
                "isTouched": False,
                "isThermal": False,
                "isPhotochemical": False,
                "isExpandable": False,
                "isEditable": False,
                "isCommercial": False,
                "isDeletable": False,
                "isChildrenEditable": False,
                "isChildrenDeletable": False,
            },
        ]
