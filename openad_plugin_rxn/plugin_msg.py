# OpenAD tools
from openad_tools.output_msgs import msg as _msg


# fmt: off
_messages = {
    "err_api_offline":
        [
            "RXN API not available",
            "You may be offline"
        ],
    "err_login":
        [
            "Something went wrong logging you in to RXN",
            "<reset>Run <cmd>rxn reset</cmd> to reset your login credentials</reset>",
            "If this error persists, try removing the RXN plugin, then restart the kernel or application and reinstall the plugin.",
        ],
}
# fmt: on


def msg(msg_name, *args):
    """
    Return a message from the messaging library.
    """
    return _msg(msg_name, custom_messages=_messages, *args)
