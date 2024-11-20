from openad.helpers.output_msgs import msg as _msg

_messages = {
    "err_deepsearch": lambda err: ["There was an error calling DeepSearch", err],
    "err_patent_id": lambda err: ["Failed to load valid list from file column 'PATENT ID' or 'patent id'", err],
    "err_rdkit_smiles": lambda err: ["Error verifying SMILES (RDKit)", err],
}


def msg(msg_name, *args):
    return _msg(msg_name, custom_messages=_messages, *args)
