"""Login procedure for the RXN plugin"""

import os
import datetime
from datetime import datetime, timezone

# OpenAD
from openad.helpers.output import output_text, output_error, output_success, output_warning
from openad.helpers.credentials import load_credentials, get_credentials, write_credentials

# Plugin
from openad_plugin_rxn.plugin_msg import msg
from openad_plugin_rxn.rxn_helper import RXNHelper
from openad_plugin_rxn.plugin_params import PLUGIN_NAME, PLUGIN_KEY
from rxn4chemistry import RXN4ChemistryWrapper


rxn_helper = RXNHelper()

API_CONFIG_BLANK = {"host": "None", "auth": {"username": "None", "api_key": "None"}, "verify_ssl": "false"}
DEFAULT_URL = "https://rxn.app.accelerate.science"

# Initialize the rxn client from the config file
# Input parameters for the example flow


def reset(cmd_pointer):
    """
    Remove login credentials to trigger authentication reset.
    """
    cred_file = os.path.expanduser(f"{cmd_pointer.home_dir}/rxn_api.cred")
    if os.path.expanduser(cred_file):
        os.remove(cred_file)


def login(cmd_pointer):
    """
    OpenAD login to RXN

    Parameters
    ----------
    cmd_pointer:
        The command pointer object
    """

    # Check for existing credentials
    cred_file = os.path.expanduser(f"{cmd_pointer.home_dir}/rxn_api.cred")

    if not os.path.isfile(cred_file):
        login_reset = True
    else:
        login_reset = False

    first_login = False  # Used primarily for Notebook mode to signal logged on only once

    # First time login in this session
    if PLUGIN_KEY not in cmd_pointer.login_settings["toolkits"]:
        first_login = True
        cmd_pointer.login_settings["toolkits"].append(PLUGIN_KEY)
        cmd_pointer.login_settings["toolkits_details"].append({"type": "config_file", "session": "handle"})
        cmd_pointer.login_settings["toolkits_api"].append(None)
        cmd_pointer.login_settings["client"].append(None)
        cmd_pointer.login_settings["expiry"].append(None)
        x = cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
        cmd_pointer.login_settings["session_vars"].append(
            rxn_helper._RXN_VARS_TEMPLATE  # pylint: disable=protected-access
        )

    # Consecutive logins - read credentials from cred_file
    elif login_reset is False:
        now = datetime.now(timezone.utc)
        x = cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
        client = cmd_pointer.login_settings["client"][cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)]
        try:
            if login_reset is True or first_login is True:
                email = client.current_user()["response"]["payload"]["email"]
                workspace = cmd_pointer.settings["workspace"]
                output_text(
                    f"<success>logging into RXN as: </success> {email}\n <success>Workspace: </success> {workspace}",
                    return_val=False,
                )
            name, prj_id = rxn_helper.get_current_project(cmd_pointer)  # pylint: disable=unused-variable
            # raise Exception("This is a test error")
        except Exception as err:  # pylint: disable=broad-exception-caught
            output_error(msg("err_login") + ["---", f"Error: {err}"], return_val=False)
            return False, None

        if name != cmd_pointer.settings["workspace"]:
            try:
                rxn_helper.sync_up_workspace_name(cmd_pointer)
            except Exception:  # pylint: disable=broad-exception-caught
                return False, None
        now = datetime.timestamp(now)
        return True, None  # No expiry on RXN Handles

    # If no authentication file, ask for authentication details and create one
    try:
        config_file = get_creds(cred_file, cmd_pointer)
    except Exception:  # pylint: disable=broad-exception-caught
        return False, None
    x = cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)

    # Fix for defaults when automating rxn cred application
    if config_file["host"].strip() == "None":
        config_file["host"] = ""

    try:
        client = RXN4ChemistryWrapper(api_key=config_file["auth"]["api_key"], base_url=config_file["host"])
        email = client.current_user()["response"]["payload"]["email"]
        if login_reset is True or first_login is True:
            workspace = cmd_pointer.settings["workspace"]
            output_success(
                f"Logged in to <yellow>{PLUGIN_NAME}</yellow> as <reset>{email}</reset>",
                return_val=False,
            )
        cmd_pointer.login_settings["toolkits_api"][x] = config_file["auth"]["api_key"]
        cmd_pointer.login_settings["client"][x] = client
        try:
            rxn_helper.sync_up_workspace_name(cmd_pointer)
        except Exception:  # pylint: disable=broad-exception-caught
            return False, None

        return True, None
    except Exception:  # pylint: disable=broad-exception-caught
        return False, None


def get_creds(cred_file, cmd_pointer):
    """
    Return existing login credentials or prompt for new ones.
    """

    api_config = load_credentials(cred_file)
    if api_config is None:
        output_warning(
            ["Please provide your RXN credentials", f"Leave this blank to use the default: {DEFAULT_URL}"],
            return_val=False,
        )
        api_config = API_CONFIG_BLANK.copy()
        api_config = get_credentials(
            cmd_pointer=cmd_pointer, credentials=api_config, creds_to_set=["host", "auth:api_key"]
        )
        write_credentials(api_config, cred_file)
    return api_config
