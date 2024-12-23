import os
import json
import pickle
import string
import hashlib
import pandas as pd
from time import sleep

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.helpers.jupyter import parse_using_clause
from openad.helpers.output import output_error

# Plugin
from openad_plugin_rxn.plugin_params import PLUGIN_KEY

spinner_msg = [
    "",
    "this may take a minute",
    "Working on it",
    "Still working",
    "Hang tight",
    "Almost there",
    "Just a moment",
    "Seems like it's taking a while",
    "Apologies for the long wait",
]


class RXNPlugin:

    _RXN_VARS_TEMPLATE = {"current_project": None, "current_project_id": None}

    def __init__(self):
        pass

    # Utility functions
    # -----------------

    def get_dataframe_from_file(self, cmd_pointer, filename: str) -> pd.DataFrame:
        """
        Parse a CSV file and return is as a dataframe.
        """
        try:
            file_path = os.path.join(cmd_pointer.workspace_path(), filename)
            df = pd.read_csv(file_path)
            return df
        except FileNotFoundError as err:
            output_error(
                "File not found", "Path should be relative to your workspace", "Path: {filename}", err, return_val=False
            )
        except Exception as err:
            output_error("Something went wrong", err, return_val=False)

    def get_list_from_txt_file(self, cmd_pointer: dict, filename: str) -> list:
        """
        Parse TXT file and return the lines as a list.
        """
        try:
            file_path = os.path.join(cmd_pointer.workspace_path(), filename)
            with open(file_path) as f:
                content = f.read()
                lines = content.splitlines()
                return lines
        except FileNotFoundError as err:
            output_error(
                "File not found", "Path should be relative to your workspace", "Path: {filename}", err, return_val=False
            )
        except Exception as err:
            output_error("Something went wrong", err, return_val=False)

    def validate_reactions_list(self, reactions_list: list) -> bool:
        """
        Check if the reactions in a list are structured correctly.

        Returns False if more reactions are invalid than valid.
        """
        valid, invalid = self._validate_reactions_list(reactions_list)
        if invalid < valid:
            return True
        else:
            output_error(
                [
                    "File contains too many invalid reactions",
                    "Reactions should be one per line, in the format: <smiles>.<smiles>.<smiles>",
                    f"Invalid reactions: {invalid} / {valid + invalid}",
                ],
                return_val=False,
            )
            return False

    def _validate_reactions_list(self, reactions_list: list) -> tuple:
        valid = []
        invalid = []
        for reaction in reactions_list:
            smiles = reaction.split(".")
            smiles = [x for x in smiles if x]
            if len(smiles) > 1:
                valid.append(reaction)
            else:
                invalid.append(reaction)

        return len(valid), len(invalid)

    def get_column_as_list_from_dataframe(self, df, column_name) -> list:
        """
        Check a dataframe for a case-insensitive column name and return the values as a list.
        """
        columns = df.columns
        columns_lowercase = [column.lower() for column in columns]
        if column_name.lower() in columns_lowercase:
            index = columns_lowercase.index(column_name.lower())
            column = columns[index]
            return df[column].tolist()
        else:
            return []

    def get_print_str__reaction(self, reaction_smiles: str, input_smiles: list = None) -> str:
        """
        Get a clean, multiline representation of a reaction for display.

        Parameters
        ----------
        reaction_smiles : str
            The reaction SMILES string:
            AA.BB.CC>>DD
        input_smiles : list, optional
            A list of input SMILES strings, if available.
            - - -
            When predicting reactions, RXN will canonicalize
            your input SMILES, making it hard to tie input and
            output together. In this case, you can pass the
            original input smiles to display instead.

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

    def get_print_str_list__confidence(self, confidence):
        """
        Visualize the confidence score.

        Parameters:
            confidence (float): Confidence score between 0 and 1
        """

        output = []

        # Confidence color
        confidence_style_tags = self.get_confidence_style(confidence)
        confidence_color = self.get_confidence_style(confidence, return_color=True)

        # Parse confidence into a percentage
        confidence = round(confidence * 100, 2) if confidence or confidence == 0 else None

        # Output for Jupyter Notebook
        if GLOBAL_SETTINGS["display"] == "notebook":
            # Confidence meter
            confidence_meter = "".join(
                [
                    "<div style='width:300px;height:5px;background:#eee;'>",
                    f"<div style='background:{confidence_color};width:{confidence * 3}px;height:100%;'></div>",
                    "</div>",
                ]
            )

            # Confidence score in text
            confidence_str = (
                f"<span style='color:{confidence_color}'>{confidence}%</span> <span style='color:#ccc'>confidence</span>"
                if confidence
                else "<span style='color:#ccc'>Confidence: n/a</span>"
            )

            # Assemble
            output = [
                confidence_meter,
                confidence_str,
            ]

        # Output for CLI
        else:
            # Confidence meter
            confidence_meter = ["━" for _ in range(24)]
            confidence_meter.insert(0, confidence_style_tags[0])
            if confidence == 100:
                confidence_meter.append("━" + confidence_style_tags[1])
            else:
                confidence_meter.insert(round(confidence / 4), "╸" + confidence_style_tags[1])
            confidence_meter = "<soft>" + "".join(confidence_meter) + "</soft>"

            # Confidence score in text
            confidence_str = str(confidence).rstrip("0").rstrip(".") if confidence else None
            confidence_str = (
                f"{confidence_style_tags[0]}{confidence_str}%{confidence_style_tags[1]} <soft>confidence</soft>"
                if confidence
                else "<soft>Confidence: n/a</soft>"
            )

            # Assemble
            output = [
                confidence_meter,
                confidence_str,
            ]

        return output

    def get_confidence_style(self, confidence, return_color=False):
        """
        Return the appropriate style tags and color for a confidence score.

        Parameters
        ----------
        confidence : float
            The confidence score between 0 and 1.

        Returns
        -------
        tuple:
            confidence_style_tags, confidence_color
        """

        # Unknown confidence
        if confidence is None:
            if return_color:
                return "#ccc"
            else:
                return ["<soft>", "</soft>"]

        # High - green
        if confidence > 0.9:
            if return_color:
                return "#090"
            else:
                return ["<green>", "</green>"]

        # Medium - yellow
        if confidence > 0.5:
            if return_color:
                return "#dc0"
            else:
                return ["<yellow>", "</yellow>"]

        # Low - red
        else:
            if return_color:
                return "#d00"
            else:
                return ["<red>", "</red>"]

    #
    #
    #
    #

    def append_project(self, cmd_pointer, project_name, project_id):
        if not os.path.isdir(cmd_pointer.home_dir + "/RXN_Projects/"):
            os.mkdir(cmd_pointer.home_dir + "/RXN_Projects/")

        try:
            with open(cmd_pointer.home_dir + "/RXN_Projects/rxn_projects.pkl", "r") as handle:
                projects = json.loads(handle.read())
                handle.close()

        except Exception as e:
            projects = {}
        projects[project_name] = project_id

        try:
            with open(cmd_pointer.home_dir + "/RXN_Projects/rxn_projects.pkl", "w") as handle:
                json.dump(dict(projects), handle)
                handle.close()
        except Exception as e:
            # print(e)
            return False

        # print("Appending 3")
        import shutil
        from datetime import datetime

        shutil.copyfile(
            cmd_pointer.home_dir + "/RXN_Projects/rxn_projects.pkl",
            cmd_pointer.home_dir + "/RXN_Projects/rxn_projects_" + datetime.now().strftime("%Y-%m-%d_%H%M%S") + ".bup",
        )
        return True

    def get_all_projects(self, cmd_pointer):
        try:
            with open(cmd_pointer.home_dir + "/RXN_Projects/rxn_projects.pkl", "r") as handle:
                projects = json.loads(handle.read())
                handle.close()
        except:
            projects = {}

        return projects

    def get_project_id(self, cmd_pointer, project_name):
        try:
            with open(cmd_pointer.home_dir + "/RXN_Projects/rxn_projects.pkl", "r") as handle:
                projects = json.loads(handle.read())
                handle.close()
                result = projects[project_name]
        except Exception as e:
            # print(e)

            result = False

        return result

    def homogenize(self, smiles_list: list) -> str:
        smiles_list.sort()
        return ".".join(smiles_list)

    # Save a result to thge cache
    # /<workspace>/._openad/rxn_cache/rxn-<func_name>-<model_name>--<input_smiles>.result
    def store_result_cache(self, cmd_pointer, name, key, payload) -> bool:
        try:
            filename = f"rxn-{name}--{key}.result"
            cache_dir = self._get_cache_dir(cmd_pointer)
            with open(os.path.join(cache_dir, filename), "wb") as handle:
                pickle.dump(dict(payload), handle)
            return True
        except Exception as err:  # pylint: disable=broad-except
            output_error(["Failed to save result as cache", f"Data: {payload}", err], return_val=False)
            return False

    # Retrieve result from the cache
    def retrieve_result_cache(self, cmd_pointer, name, key):
        try:
            filename = f"rxn-{name}--{key}.result"
            cache_dir = self._get_cache_dir(cmd_pointer)
            with open(os.path.join(cache_dir, filename), "rb") as handle:
                result = pickle.load(handle)
            return result
        except Exception:  # pylint: disable=broad-except
            return False

    # Create the cache directories if they don't exist
    def _get_cache_dir(self, cmd_pointer):
        cache_dir = os.path.join(cmd_pointer.workspace_path(), "._openad", "rxn_cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    # sets the current project
    def set_current_project(self, cmd_pointer, project_name: str) -> bool:
        # projects = self.get_all_projects(cmd_pointer)
        # project_id=1
        # project_description=1
        # result = self.validate_project(cmd_pointer,project_name)
        result = self.get_project_id(cmd_pointer, project_name)
        # print("setting project")
        # print(result)
        if result != False:
            rxn_position = cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY) - 1
            # cmd_pointer.login_settings['session_vars'][rxn_position]['env_vars']= self._RXN_VARS_TEMPLATE
            cmd_pointer.login_settings["session_vars"][rxn_position]["current_project"] = project_name

            cmd_pointer.login_settings["session_vars"][rxn_position]["current_project_id"] = result
            # cmd_pointer.login_settings['session_vars'][rxn_position]['current_project_description']=result['description']
            rxn4chemistry_wrapper = cmd_pointer.login_settings["client"][
                cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
            ]
            # print('prj_id')
            # print(result)
            rxn4chemistry_wrapper.set_project(result)
            return result
        else:
            return False

    ### only for function checks not for login.py
    def sync_up_workspace_name(self, cmd_pointer, reset=False):
        name, id = self.get_current_project(cmd_pointer)
        # print("current_project: "+str(name)+" "+str(id))
        if name == cmd_pointer.settings["workspace"] and reset != True:
            return True

        try:
            result = self.set_current_project(cmd_pointer, cmd_pointer.settings["workspace"].upper())
        except BaseException as e:
            raise BaseException(
                "Unable to set current project due to API issue, check server connections Try Again: " + str(e)
            )

        if result == False:
            retries = 0
            while retries < 5 and result == False:
                if retries > 1:
                    sleep(3)
                retries = retries + 1

                # sys.stdout = open(os.devnull, "w")
                # sys.stderr = open(os.devnull, "w")

                try:
                    rxn4chemistry_wrapper = cmd_pointer.login_settings["client"][
                        cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
                    ]
                    sleep(3)

                    x = rxn4chemistry_wrapper.create_project(cmd_pointer.settings["workspace"])

                    if len(x) == 0:
                        continue
                    else:
                        self.append_project(
                            cmd_pointer, cmd_pointer.settings["workspace"].upper(), x["response"]["payload"]["id"]
                        )
                    # print('here')
                except BaseException as e:
                    print(e)
                    raise BaseException("Unable to create project :" + str(e))
                try:
                    sleep(3)
                    result = self.set_current_project(cmd_pointer, cmd_pointer.settings["workspace"])
                    # print(cmd_pointer.settings['workspace'])
                    # print(result)
                except BaseException as e:
                    # sys.stdout = sys.__stdout__
                    # sys.stderr = sys.__stderr__
                    raise BaseException(
                        "Unable to set current project due to API issue, check server connections Try Again: " + str(e)
                    )

            # sys.stdout = sys.__stdout__
            # sys.stderr = sys.__stderr__
            if result == False:
                if GLOBAL_SETTINGS["display"] == "notebook":
                    from IPython.display import display, Markdown

                    display(Markdown("Failed to setup RXN project for this Workspace "))
                else:
                    print("Failed to setup RXN project for this Workspace ")

            else:
                if GLOBAL_SETTINGS["display"] == "notebook":
                    from IPython.display import display, Markdown

                    display(Markdown("A new RXN Project has been setup for this Workspace"))
                else:
                    print("A new RXN Project has been setup for this Workspace ")
        else:
            if GLOBAL_SETTINGS["display"] == "notebook":
                from IPython.display import display, Markdown

                display(
                    Markdown("RXN Project has been set to " + cmd_pointer.settings["workspace"] + " for this Workspace")
                )

        return True

    def validate_project(self, cmd_pointer, project_name):
        # print("validate_project")
        # projects = self.get_all_projects(cmd_pointer)
        projects = self.get_all_projects(cmd_pointer)
        # print(projects)

        if project_name in projects["name"].values:
            result = projects[projects.name == project_name]
            # print(result)
            return {"name": result["name"], "id": result["id"]}
            # return {'name':result['name'][:1].item(),'id':result['id'][:1].item(),'description':result['description'][:1].item(),'attempts':result['attempts'][:1].item()}
        else:
            return False

    def get_current_project(self, cmd_pointer):
        rxn_position = cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY) - 1
        try:
            return (
                cmd_pointer.login_settings["session_vars"][rxn_position]["current_project"],
                cmd_pointer.login_settings["session_vars"][rxn_position]["current_project_id"],
            )
        except:
            return None, None

    # Note get
    def get_all_projects_old(self, cmd_pointer) -> pd.DataFrame:
        api_key = cmd_pointer.login_settings["toolkits_api"][cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)]

        rxn4chemistry_wrapper = cmd_pointer.login_settings["client"][
            cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
        ]
        # Prepare the data query
        source_list = []
        result = False
        retries = 0

        while result == False:
            try:
                x = rxn4chemistry_wrapper.list_all_projects(size=100)["response"]["payload"]["content"]
                # print(x)
                result = True
            except BaseException as e:
                retries = retries + 1
                sleep(2)
                if retries > 10:
                    raise BaseException("Unable to retrieve valid list of projects:" + str(e))

        df = self.pd.DataFrame(x)

        df = df[["name", "description", "id", "attempts"]]
        return df

    def output(self, text, cmd_pointer=None):
        if GLOBAL_SETTINGS["display"] == "notebook":
            from IPython.display import Markdown, display
        import re

        tags = {
            "h1": "\x1b[0m",  # Primary headers: default with yellow line below
            "h2": "\x1b[33m",  # Secondary headers: yellow
            "cmd": "\x1b[36m",  # Commands: cyan
            "error": "\x1b[31m",  # Errors: red
            "warning": "\x1b[33m",  # Warnings: yellow
            "success": "\x1b[32m",  # Success: green
            "link": "\x1b[4;94m",  # Links: undertline intense blue
            # 'edit': '\x1b[0;47;30m',  # Edit node: black on white
            "edit": "\x1b[7m",  # Edit node: reverse
            "editable": "\x1b[100m",  # Editable text: on_bright_black
            # Styles
            "reset": "\x1b[0m",
            "bold": "\x1b[1m",
            "soft": "\x1b[2m",
            "italic": "\x1b[3m",
            "underline": "\x1b[4m",
            "blink": "\x1b[5m",
            "reverse": "\x1b[7m",
            "hidden": "\x1b[8m",
            "strikethrough": "\x1b[9m",
            # Foreground colors - Regular
            "black": "\x1b[30m",
            "red": "\x1b[31m",
            "green": "\x1b[32m",
            "yellow": "\x1b[33m",
            "blue": "\x1b[34m",
            "magenta": "\x1b[35m",
            "cyan": "\x1b[36m",
            "white": "\x1b[37m",
            # Foreground colors - Intense (non-standard)
            "bright_black": "\x1b[90m",
            "bright_red": "\x1b[91m",
            "bright_green": "\x1b[92m",
            "bright_yellow": "\x1b[93m",
            "bright_blue": "\x1b[94m",
            "bright_magenta": "\x1b[95m",
            "bright_cyan": "\x1b[96m",
            "bright_white": "\x1b[97m",
            # Background colors - Regular
            "on_black": "\x1b[0;40m",
            "on_red": "\x1b[0;41m",
            "on_green": "\x1b[0;42m",
            "on_yellow": "\x1b[0;43m",
            "on_blue": "\x1b[0;44m",
            "on_magenta": "\x1b[0;45m",
            "on_cyan": "\x1b[0;46m",
            "on_white": "\x1b[0;47m",
            # Background colors - Intense (non-standard)
            "on_bright_black": "\x1b[100m",
            "on_bright_red": "\x1b[101m",
            "on_bright_green": "\x1b[102m",
            "on_bright_yellow": "\x1b[103m",
            "on_bright_blue": "\x1b[104m",
            "on_bright_magenta": "\x1b[105m",
            "on_bright_cyan": "\x1b[106m",
            "on_bright_white": "\x1b[107m",
            # Unused but useful as a reference
            # \x1b[7m - Reversed
        }

        def parse_tags(text: str):
            """
            Parse xml tags and return styled output:
            <red>lorem ipsum</red>
            """
            pattern = rf"(.*?)<({'|'.join(list(tags))})>(.*?)</\2>"
            return re.sub(pattern, lambda match: _replace(match, pattern), text)

        def _replace(match: object, pattern, parent_tag="reset"):
            """Replace regex matches with appropriate styling."""
            text_before = match.group(1)
            tag = match.group(2)
            inner_text = match.group(3)
            ansi_code_open = tags[tag]
            ansi_code_close = tags[parent_tag]
            ansi_code_reset = tags["reset"]

            # Replace any nested tags.
            if re.findall(pattern, inner_text):
                inner_text = re.sub(pattern, lambda match: _replace(match, pattern, tag), inner_text)

            return f"{text_before}{ansi_code_open}{inner_text}{ansi_code_reset}{ansi_code_close}"

        def strip_tags(text: str):
            """Recursively remove all XML tags."""

            # Strip any nested tags.
            def _strip(match: object, pattern):
                inner_text = match.group(2)
                if re.findall(pattern, inner_text):
                    inner_text = re.sub(pattern, lambda match: _strip(match, pattern), inner_text)
                return inner_text

            # Strip tags.
            text = text.replace("\n", "---LINEBREAK2---")
            pattern = rf"<({'|'.join(list(tags))})>(.*?)</\1>"
            text = re.sub(pattern, lambda match: _strip(match, pattern), text)
            return text.replace("---LINEBREAK2---", "\n")

        def tags_to_markdown(text: str):
            if text is None:
                return ""

            # Replace leading spaces with non-breaking spaces.
            text = re.sub(r"^( *)", "", text, flags=re.MULTILINE)

            # Replace line breaks so all text is parsed on one line.
            # Because html breaks (<br>) don't play well with headings,
            # and end of line characters don't play well with `code`
            # blocks, we have to do some trickery here.
            text = re.sub(
                r"(</h[123]>)(\n+)", lambda match: match.group(1) + len(match.group(2)) * "---LINEBREAKSOFT---", text
            )
            text = re.sub(
                r"(\n+)(<h[123]>)", lambda match: len(match.group(1)) * "---LINEBREAKSOFT---" + match.group(2), text
            )
            text = text.replace("\n", "---LINEBREAK3---")

            # Replace tags
            # We only replace <soft> and <underline> tags
            # when they don't appear inside <cmd> tags.
            text = re.sub(r"(?<!\<cmd\>)<soft>([^<]*)</soft>(?!\</cmd\>)", r'<span style="color: #ccc">\1</span>', text)
            text = re.sub(
                r"(?<!\<cmd\>)<underline>([^<]*)<\/underline>(?!\</cmd\>)",
                r'<span style="text-decoration: underline">\1</span>',
                text,
            )
            text = re.sub(r"<h1>(.*?)<\/h1>", r"## \1", text)
            text = re.sub(r"<h2>(.*?)<\/h2>", r"### \1", text)
            text = re.sub(r"<link>(.*?)<\/link>", r'<a target="_blank" href="\1">\1</a>', text)
            text = re.sub(r"<bold>(.*?)<\/bold>", r"**\1**", text)
            text = re.sub(r"<cmd>(.*?)<\/cmd>", r"`\1`", text)
            text = re.sub(r"<on_red>(.*?)<\/on_red>", r'<span style="background: #d00; color: #fff">\1</span>', text)
            text = re.sub(
                r"<on_green>(.*?)<\/on_green>", r'<span style="background: #0d0; color: #fff">\1</span>', text
            )
            text = re.sub(r"<success>(.*?)<\/success>", r'<span style=" color: #008000">\1</span>', text)
            text = re.sub(r"<fail>(.*?)<\/fail>", r'<span style=" color: #ff0000">\1</span>', text)

            # Escape quotes.
            text = text.replace("'", "'")

            # Replace all other tags
            text = strip_tags(text)

            # Restore line breaks.
            text = text.replace("---LINEBREAKSOFT---", "\n")
            text = text.replace("---LINEBREAK3---", "<br>")

            return text

        if GLOBAL_SETTINGS["display"] == "api":
            # API
            return strip_tags(text)
        elif GLOBAL_SETTINGS["display"] == "notebook":
            # Jupyter
            return Markdown(tags_to_markdown(text))
        else:
            # CLI
            print(parse_tags(str(text)))

    def parse_using_params(self, cmd, default_values):
        """
        Parse the parameters from the USING clause.
        """

        # Parse parameters from the USING clause
        using_params = parse_using_clause(
            cmd.get("using"),
            allowed=default_values.keys(),
        )

        # Assign default parameters
        for key, val in default_values.items():
            if key not in using_params:
                using_params[key] = val

        return using_params


# def generate_smiles_hash(smiles_string):
#     # Convert the SMILES string to bytes (required by hashlib)
#     bytes_smiles = smiles_string.encode("utf-8")

#     # Calculate the SHA-256 hash
#     sha256_hash = hashlib.sha256(bytes_smiles).hexdigest()

#     return sha256_hash


# def create_valid_filename_from_smiles(smiles_string):
#     # Generate the SHA-256 hash from the SMILES string
#     hash_value = generate_smiles_hash(smiles_string)

#     # Create the filename by adding the hash value and the .smiles extension
#     filename = hash_value + ".smiles"

#     return filename


# def format_filename(s):
#     """Take a string and return a valid filename constructed from the string.
#     Uses a whitelist approach: any characters not present in valid_chars are
#     removed. Also spaces are replaced with underscores.

#     Note: this method may produce invalid filenames such as ``, `.` or `..`
#     When I use this method I prepend a date string like '2009_01_15_19_46_32_'
#     and append a file extension like '.txt', so I avoid the potential of using
#     an invalid filename.
#     """
#     valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
#     filename = "".join(c for c in s if c in valid_chars)
#     filename = filename.replace(" ", "_")  # I don't like spaces in filenames.
#     filename = filename.replace("CON", "C0N")  # I don't like spaces in filenames.
#     return filename
