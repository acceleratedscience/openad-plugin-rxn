"""Login Library for the Deepsearch Plugin"""

import os
import datetime
from datetime import datetime, timezone
import time
import requests
import jwt
import deepsearch as ds
from openad.helpers.output import output_text, output_error, output_warning, output_success
from openad.helpers.credentials import load_credentials, get_credentials, write_credentials
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY


DEFAULT_URL = "https://sds.app.accelerate.science/"
API_CONFIG_BLANK = {
    "host": "None",
    "auth": {"username": "None", "api_key": "None"},
    "verify_ssl": "False",
}


def login(cmd_pointer):
    """
    OpenAD login to Deep Search

    Parameters
    ----------
    cmd_pointer:
        The command pointer object
    plugin_name:
        Human-readable name of the plugin,
        used for logging error/success messages
    plugin_key:
        Unique key for the plugin,
        used to store login information in the command pointer object
    """

    # Check for existing credentials
    cred_file = os.path.expanduser(f"{cmd_pointer.home_dir}/deepsearch_api.cred")
    if not os.path.isfile(cred_file):
        login_reset = True
    else:
        login_reset = False

    # For debugging
    # print("$$", PLUGIN_KEY, cmd_pointer.login_settings)

    # First-time login
    first_login = False
    if PLUGIN_KEY not in cmd_pointer.login_settings["toolkits"]:
        cmd_pointer.login_settings["toolkits"].append(PLUGIN_KEY)
        cmd_pointer.login_settings["toolkits_details"].append({"type": "config_file", "session": "handle"})
        cmd_pointer.login_settings["toolkits_api"].append(None)
        cmd_pointer.login_settings["client"].append(None)
        cmd_pointer.login_settings["expiry"].append(None)
        i = cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
        first_login = True

    # Previously logged in - check if the token is still valid
    elif login_reset is False:
        now = datetime.now(timezone.utc)
        i = cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
        now = datetime.timestamp(now)
        expiry_time = cmd_pointer.login_settings["expiry"][i]

        if expiry_time is not None and expiry_time > now:
            expiry_datetime = time.strftime("%a %b %e, %G  at %R", time.localtime(expiry_time))
            return True, expiry_datetime

    # Get login credentials
    try:
        cred_config = _get_creds(cred_file, cmd_pointer)
    except Exception:  # pylint: disable=broad-except
        return False, None

    # Validate credentials input
    if cred_config["host"].strip() == "" or cred_config["host"].strip() == "None":
        cred_config["host"] = DEFAULT_URL
    if _uri_valid(cred_config["host"]) is False:
        output_error("Invalid url, try again", return_val=False)
        return False, None
    if cred_config["auth"]["username"].strip() == "":
        output_error("Invalid username, try again", return_val=False)
        return False, None
    if cred_config["auth"]["api_key"].strip() == "":
        output_error("Invalid API key, try again", return_val=False)
        return False, None

    # Login
    try:
        # Define login API
        config = ds.DeepSearchConfig(host=cred_config["host"], verify_ssl=False, auth=cred_config["auth"])
        client = ds.CpsApiClient(config)
        api = ds.CpsApi(client)

        # Store login API
        i = cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
        cmd_pointer.login_settings["toolkits_api"][i] = api
        cmd_pointer.login_settings["client"][i] = client

        # Decode jwt token
        cb = client.bearer_token_auth
        bearer = cb.bearer_token
        decoded_token = jwt.decode(bearer, options={"verify_at_hash": False, "verify_signature": False}, verify=False)

        # Extract & store expiry time from token payload
        expiry_time = decoded_token["exp"]
        cmd_pointer.login_settings["expiry"][i] = expiry_time

        # Convert expiry time to a human-readable format
        expiry_datetime = time.strftime("%a %b %e, %G  at %R", time.localtime(expiry_time))

        # Print login success message
        if login_reset is True or first_login is True:
            username = cred_config["auth"]["username"]
            output_success(
                f"Logged in to <yellow>{PLUGIN_NAME}</yellow> as <reset>{username}</reset>", return_val=False
            )

        return True, expiry_datetime

    # Login fail
    except Exception:  # pylint: disable=broad-exception-caught
        username = cred_config["auth"]["username"]
        output_error(
            f"Failed to log in to <yellow>{PLUGIN_NAME}</yellow> as <reset>{username}</reset>", return_val=False
        )
        return False, None


def reset(cmd_pointer):
    """Remove the deepsearch credentiuals file"""
    cred_file = os.path.expanduser(f"{cmd_pointer.home_dir}/deepsearch_api.cred")
    if os.path.isfile(cred_file):
        os.remove(cred_file)


def _uri_valid(url: str) -> bool:
    """Check if a URI is valid"""
    try:
        request = requests.get(url, stream=True, timeout=10)
    except:  # pylint: disable=bare-except
        return False
    if request.status_code == 200:
        return True
    else:
        return False


def _get_creds(cred_file, cmd_pointer):
    """Return existing login credentials or prompt for new ones"""
    api_config = load_credentials(cred_file)
    if api_config is None:
        output_warning("Please provide your Deep Search credentials", return_val=False)
        output_text(f"<soft>Leave this blank to use the default: {DEFAULT_URL}</soft>", return_val=False)
        api_config = API_CONFIG_BLANK.copy()
        api_config = get_credentials(
            cmd_pointer=cmd_pointer, credentials=api_config, creds_to_set=["host", "auth:username", "auth:api_key"]
        )
        write_credentials(api_config, cred_file)
    return api_config
