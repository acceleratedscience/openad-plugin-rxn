from openad.helpers.output_msgs import msg as _msg


_messages = {
    "err_api_offline": ["RXN API not available", "You may be offline"],
    "err_login": [
        "Something went wrong logging you in to RXN",
        "<reset>Run <cmd>rxn reset</cmd> to reset your login credentials</reset>",
        "If this error persists, try removing the RXN plugin, then restart the kernel or application and reinstall the plugin.",
    ],
}


def msg(msg_name, *args):
    return _msg(msg_name, custom_messages=_messages, *args)
