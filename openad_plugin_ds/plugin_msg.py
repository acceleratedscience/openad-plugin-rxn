from openad.helpers.output_msgs import msg as _msg

_messages = {
    "err_deepsearch": lambda err: ["There was an error calling Deep Search", err],
    "err_file_not_found": lambda filename: f"File '<yellow>{filename}</yellow>' does not exist",
    "err_no_patent_ids_found": lambda src_type: f"Failed to find patent ids in the provided {src_type}",
    "err_invalid_identifier": "Invalid molecule identifier",
    "err_no_patents_found": lambda result_type, identifier: f"No patents found containing {result_type}:\n<yellow>{identifier}</yellow>"
    + (
        "\n<soft>Note: The identifier was not recognized to be a SMILES or InChI so it is assumed to be an InChIKey.</soft>"
        if result_type == "InChIKey"
        else ""
    ),
    "success_patents_found": lambda result_count, result_type, identifier: f"We found {result_count} patents containing the requested {result_type}:\n<yellow>{identifier}</yellow>",
    #
    #
    "success_file_saved": lambda filename: f"Successully saved <yellow>{filename}</yellow> to your workspace",
    "err_rdkit_smiles": lambda err: ["Error verifying SMILES (RDKit)", err],
}


def msg(msg_name, *args):
    return _msg(msg_name, custom_messages=_messages, *args)
