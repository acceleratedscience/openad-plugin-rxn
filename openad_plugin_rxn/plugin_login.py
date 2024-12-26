import os
from datetime import datetime, timezone

# OpenAD
from openad_plugin_rxn.plugin_msg import msg
from openad.helpers.output import output_text, output_success, output_warning, output_error
from openad.helpers.credentials import load_credentials, get_credentials, write_credentials

# Plugin
from openad_plugin_rxn.plugin_params import PLUGIN_KEY, PLUGIN_NAME
from rxn4chemistry import RXN4ChemistryWrapper


class RXNLoginManager:
    """
    Login manager for RXN
    """

    master = None
    RXN_VARS_TEMPLATE = {"current_project": None, "current_project_id": None}
    API_CONFIG_BLANK = {"host": "None", "auth": {"username": "None", "api_key": "None"}, "verify_ssl": "false"}
    DEFAULT_URL = "https://rxn.app.accelerate.science"

    def __init__(self, master, cmd_pointer):
        """
        Parameters
        ----------
        cmd_pointer:
            The command pointer object
        """
        self.master = master
        self.cmd_pointer = cmd_pointer

    def login(self):
        """Login to RXN"""

        # Check for existing credentials
        cred_file = os.path.expanduser(f"{self.cmd_pointer.home_dir}/rxn_api.cred")

        if not os.path.isfile(cred_file):
            login_reset = True
        else:
            login_reset = False

        first_login = False  # Used primarily for Notebook mode to signal logged on only once

        # First time login in this session
        if PLUGIN_KEY not in self.cmd_pointer.login_settings["toolkits"]:
            first_login = True
            self.cmd_pointer.login_settings["toolkits"].append(PLUGIN_KEY)
            self.cmd_pointer.login_settings["toolkits_details"].append({"type": "config_file", "session": "handle"})
            self.cmd_pointer.login_settings["toolkits_api"].append(None)
            self.cmd_pointer.login_settings["client"].append(None)
            self.cmd_pointer.login_settings["expiry"].append(None)
            x = self.cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
            self.cmd_pointer.login_settings["session_vars"].append(
                self.RXN_VARS_TEMPLATE  # pylint: disable=protected-access
            )

        # Consecutive logins - read credentials from cred_file
        elif login_reset is False:
            now = datetime.now(timezone.utc)
            x = self.cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
            client = self.cmd_pointer.login_settings["client"][
                self.cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
            ]
            try:
                if login_reset is True or first_login is True:
                    email = client.current_user()["response"]["payload"]["email"]
                    workspace = self.cmd_pointer.settings["workspace"]
                    output_text(
                        f"<success>logging into RXN as: </success> {email}\n <success>Workspace: </success> {workspace}",
                        return_val=False,
                    )
                name, project_id = self.master.get_current_project(self.cmd_pointer)  # pylint: disable=unused-variable
                # raise Exception("This is a test error")
            except Exception as err:  # pylint: disable=broad-exception-caught
                output_error(msg("err_login") + ["---", f"Error: {err}"], return_val=False)
                return False, None

            if name != self.cmd_pointer.settings["workspace"]:
                try:
                    self.master.sync_up_workspace_name(self.cmd_pointer)
                except Exception:  # pylint: disable=broad-exception-caught
                    return False, None
            now = datetime.timestamp(now)
            return True, None  # No expiry on RXN Handles

        # If no authentication file, ask for authentication details and create one
        try:
            config_file = self._get_creds(cred_file)
        except Exception:  # pylint: disable=broad-exception-caught
            return False, None
        x = self.cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)

        # Fix for defaults when automating rxn cred application
        if config_file["host"].strip() == "None":
            config_file["host"] = ""

        try:
            client = RXN4ChemistryWrapper(api_key=config_file["auth"]["api_key"], base_url=config_file["host"])
            email = client.current_user()["response"]["payload"]["email"]
            if login_reset is True or first_login is True:
                workspace = self.cmd_pointer.settings["workspace"]
                output_success(
                    f"Logged in to <yellow>{PLUGIN_NAME}</yellow> as <reset>{email}</reset>",
                    return_val=False,
                )
            self.cmd_pointer.login_settings["toolkits_api"][x] = config_file["auth"]["api_key"]
            self.cmd_pointer.login_settings["client"][x] = client
            try:
                self.master.sync_up_workspace_name(self.cmd_pointer)
            except Exception:  # pylint: disable=broad-exception-caught
                return False, None

            return True, None
        except Exception:  # pylint: disable=broad-exception-caught
            return False, None

    def _get_creds(self, cred_file):
        """
        Return existing login credentials or prompt for new ones.
        """

        api_config = load_credentials(cred_file)
        if api_config is None:
            output_warning(
                ["Please provide your RXN credentials", f"Leave this blank to use the default: {self.DEFAULT_URL}"],
                return_val=False,
            )
            api_config = self.API_CONFIG_BLANK.copy()
            api_config = get_credentials(
                cmd_pointer=self.cmd_pointer, credentials=api_config, creds_to_set=["host", "auth:api_key"]
            )
            write_credentials(api_config, cred_file)
        return api_config

    def reset(self):
        """
        Remove login credentials to trigger authentication reset.
        """
        cred_file = os.path.expanduser(f"{self.cmd_pointer.home_dir}/rxn_api.cred")
        if os.path.expanduser(cred_file):
            os.remove(cred_file)
