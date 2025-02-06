import os
import json
import pandas as pd
import shutil
from time import sleep
from datetime import datetime
from requests.exceptions import MissingSchema, HTTPError

# OpenAD
from openad.helpers.credentials import load_credentials, get_credentials, write_credentials

# OpenAD tools
from openad_tools.output import output_text, output_success, output_warning, output_error

# Plugin
from openad_plugin_rxn.plugin_msg import msg
from openad_plugin_rxn.plugin_params import PLUGIN_KEY, PLUGIN_NAME
from rxn4chemistry import RXN4ChemistryWrapper


class RXNLoginManager:
    """
    Login manager for RXN
    """

    cmd_pointer = None
    cred_path = None
    RXN_VARS_TEMPLATE = {"current_project": None, "current_project_id": None}
    API_CONFIG_BLANK = {"host": "None", "auth": {"username": "None", "api_key": "None"}, "verify_ssl": "false"}
    DEFAULT_URL = "https://rxn.app.accelerate.science"
    api = None

    def __init__(self, cmd_pointer):
        """
        Parameters
        ----------
        cmd_pointer: object
            The command pointer object.
        """
        self.cmd_pointer = cmd_pointer
        self.cred_path = os.path.expanduser(f"{self.cmd_pointer.home_dir}/rxn_api.cred")

    def login(self):
        """Login to RXN"""

        # Check for credentials file
        login_reset = bool(not os.path.isfile(self.cred_path))

        # Already logged in
        if not login_reset and self._apikey_stored():
            # Link API to the project associated with your current workspace
            name, project_id = self.get_current_project()  # pylint: disable=unused-variable
            if name != self.cmd_pointer.settings["workspace"]:
                self._sync_workspace_rxn_project()
            return False

        # ------------------------------------------------

        # Prepare new login entry
        self.cmd_pointer.login_settings["toolkits"].append(PLUGIN_KEY)
        self.cmd_pointer.login_settings["toolkits_details"].append({"type": "config_file", "session": "handle"})
        self.cmd_pointer.login_settings["toolkits_api"].append(None)
        self.cmd_pointer.login_settings["client"].append(None)
        self.cmd_pointer.login_settings["expiry"].append(None)
        self.cmd_pointer.login_settings["session_vars"].append(self.RXN_VARS_TEMPLATE)

        try:
            # Initialize the API
            username = self._init_api()
            if not username:
                return False

            # Link API to the project associated with your current workspace
            self._sync_workspace_rxn_project()

            return username

        # Incorrect host
        except MissingSchema as err:
            output_error(["Incorrect API host, please try again", err], return_val=False)
            os.remove(self.cred_path)
            return False

        # Incorrect API key
        except HTTPError as err:
            err_msg = "Invalid API key, please try again"
            if bool(str(err)):
                err_msg = [err_msg, err]
            output_error(err_msg, return_val=False)
            os.remove(self.cred_path)

        # Other failure (eg. offline)
        except Exception as err:  # pylint: disable=broad-exception-caught
            output_error(["Failed to initialize the RXN API", err], return_val=False)
            return False

    def _init_api(self):
        if not self.api:
            # Get existing login credentials or prompt for new ones.
            config_file = self._get_creds()

            # Fix for defaults when automating rxn cred application
            if config_file["host"].strip() == "None":
                config_file["host"] = ""

            self.api = RXN4ChemistryWrapper(api_key=config_file["auth"]["api_key"], base_url=config_file["host"])

            # You're probably offline
            if not self.api:
                output_error(msg("err_api_offline"), return_val=False)
                return False

            # Test API
            else:
                # Will throw MissingSchema exception if the host is invalid
                response = self.api.current_user().get("response", {}) or {}
                username = response.get("payload", {}).get("email") if response else None

                # Response looks ok, store API credentials
                if username:
                    toolkit_index = self.cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
                    self.cmd_pointer.login_settings["toolkits_api"][toolkit_index] = config_file["auth"]["api_key"]
                    self.cmd_pointer.login_settings["client"][toolkit_index] = self.api
                    return username

                # Fail - invalid API key
                elif not response:
                    raise HTTPError()
                elif response.get("status") == 401:
                    raise HTTPError(response.get("message"))

    def _apikey_stored(self):
        if not PLUGIN_KEY in self.cmd_pointer.login_settings["toolkits"]:
            return False

        toolkit_index = self.cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
        api_key = self.cmd_pointer.login_settings["toolkits_api"][toolkit_index]
        return bool(api_key)

    def _get_creds(self):
        """
        Return existing login credentials or prompt for new ones.
        """
        api_config = load_credentials(self.cred_path)
        if api_config is None:
            output_text(
                "\n".join(
                    [
                        "<h1>RXN Authentication</h1>",
                        "To obtain your API key, visit:",
                        "<link>rxn.app.accelerate.science</link>",
                        "",
                        "For instructions, visit:",
                        "<link>github.com/acceleratedscience/openad-plugin-rxn#login</link>",
                    ]
                ),
                return_val=False,
                pad=2,
            )

            output_warning(
                ["Please provide your RXN credentials", f"Leave this blank to use the default: {self.DEFAULT_URL}"],
                return_val=False,
            )
            api_config = self.API_CONFIG_BLANK.copy()
            api_config = get_credentials(
                cmd_pointer=self.cmd_pointer, credentials=api_config, creds_to_set=["host", "auth:api_key"]
            )
            write_credentials(api_config, self.cred_path)
        return api_config

    def is_logged_in(self):
        """
        Check if you are logged in.
        """
        if self._apikey_stored():
            username = self._init_api()
            return username
        else:
            return False

    def reset(self):
        """
        Remove login credentials to trigger authentication reset.
        """
        if os.path.isfile(self.cred_path):
            os.remove(self.cred_path)
            output_success("You are logged out of RXN", return_val=False)
            return True
        else:
            output_warning("No login credentials found", return_val=False)
            return False

    # RXN project management
    # ----------------------
    # We create and store a separate project per workspace

    def _sync_workspace_rxn_project(self, reset=False):
        """
        Create or reuse an RXN project with the same name as your workspace, required to use the API.
        """

        # Check if you already have a project set up for this workspace,
        # and initialize the API wih it
        all_projects = self.__get_all_projects()
        workspace_name = self.cmd_pointer.settings["workspace"].upper()
        if workspace_name in all_projects:
            self.__set_current_project(workspace_name)
            return

        # Check if you already have a project set up.
        name, project_id = self.get_current_project()
        if name == self.cmd_pointer.settings["workspace"] and not reset:
            return

        # Create new project
        success = False
        retries = 0
        while retries < 5 and success is False:
            if retries > 1:
                sleep(3)
            retries += 1

            try:
                result = self.api.create_project(self.cmd_pointer.settings["workspace"])

                if len(result) == 0:
                    continue
                else:
                    self.__append_project(
                        self.cmd_pointer.settings["workspace"].upper(),
                        result["response"]["payload"]["id"],
                    )
            except Exception as err:  # pylint: disable=broad-exception-caught
                output_error(["Unable to create RXN project", "API may be offline", err], return_val=False)
                return

            try:
                sleep(3)
                success = self.__set_current_project(self.cmd_pointer.settings["workspace"].upper())
            except Exception as err:  # pylint: disable=broad-exception-caught
                output_error(["Unable to set RXN project", "API may be offline", err], return_val=False)
                return

        # Success
        output_text("<soft>A new RXN project has been setup for this workspace</soft>", return_val=False)
        return

    def __get_all_projects(self):
        """
        Get list of all your RXN projects.
        """
        try:
            with open(self.cmd_pointer.home_dir + "/RXN_Projects/rxn_projects.pkl", "r", encoding="utf-8") as handle:
                projects = json.loads(handle.read())
                handle.close()
        except Exception:  # pylint: disable=broad-exception-caught
            projects = {}

        return projects

    def __append_project(self, project_name, project_id):
        """
        Append newly created project to the list of projects.
        """
        if not os.path.isdir(self.cmd_pointer.home_dir + "/RXN_Projects/"):
            os.mkdir(self.cmd_pointer.home_dir + "/RXN_Projects/")

        try:
            with open(self.cmd_pointer.home_dir + "/RXN_Projects/rxn_projects.pkl", "r", encoding="utf-8") as handle:
                projects = json.loads(handle.read())
                handle.close()
        except Exception:  # pylint: disable=broad-exception-caught
            projects = {}
        projects[project_name] = project_id

        try:
            with open(self.cmd_pointer.home_dir + "/RXN_Projects/rxn_projects.pkl", "w", encoding="utf-8") as handle:
                json.dump(dict(projects), handle)
                handle.close()
        except Exception:  # pylint: disable=broad-exception-caught
            return False

        shutil.copyfile(
            self.cmd_pointer.home_dir + "/RXN_Projects/rxn_projects.pkl",
            self.cmd_pointer.home_dir
            + "/RXN_Projects/rxn_projects_"
            + datetime.now().strftime("%Y-%m-%d_%H%M%S")
            + ".bup",
        )
        return True

    def __set_current_project(self, project_name: str) -> bool:
        """
        Set the current RXN project, required to use API.
        """
        project_id = self.___get_project_id(project_name)
        if project_id is not False:
            rxn_position = self.cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
            self.cmd_pointer.login_settings["session_vars"][rxn_position]["current_project"] = project_name
            self.cmd_pointer.login_settings["session_vars"][rxn_position]["current_project_id"] = project_id

            try:
                self.api.set_project(project_id)
                return True
            except Exception as err:  # pylint: disable=broad-exception-caught
                output_error(["Failed to set API's project_id", err], return_val=False)
                return False

    def ___get_project_id(self, project_name):
        project_id = False
        try:
            with open(self.cmd_pointer.home_dir + "/RXN_Projects/rxn_projects.pkl", "r", encoding="utf-8") as handle:
                projects = json.loads(handle.read())
                handle.close()
                project_id = projects[project_name]
        except Exception:  # pylint: disable=broad-exception-caught
            pass

        return project_id

    def get_current_project(self):
        """
        Get your current RXN project.

        Returns
        -------
        name, id
        """
        rxn_position = self.cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
        try:
            return (
                self.cmd_pointer.login_settings["session_vars"][rxn_position]["current_project"],
                self.cmd_pointer.login_settings["session_vars"][rxn_position]["current_project_id"],
            )
        except Exception:  # pylint: disable=broad-except
            return None, None

    # Unused methods
    # ----------------

    def validate_project(self, project_name):
        """
        Validate if a project exists.
        """
        projects = self.__get_all_projects()
        if project_name in projects["name"].values:
            result = projects[projects.name == project_name]
            return {"name": result["name"], "id": result["id"]}
        else:
            return False

    def get_all_projects_v1(self) -> pd.DataFrame:
        """
        Get list of all your RXN projects (alt)
        """
        result = False
        retries = 0
        while result is False:
            try:
                result = self.api.list_all_projects(size=100)["response"]["payload"]["content"]
            except Exception as err:  # pylint: disable=broad-except
                if retries < 10:
                    sleep(2)
                    retries += 1
                else:
                    output_error(["Unable to retrieve list of projects", err], return_val=False)
                    return

        df = pd.DataFrame(result)
        df = df[["name", "description", "id", "attempts"]]
        return df
