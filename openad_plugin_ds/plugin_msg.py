from openad.helpers.output_msgs import msg as _msg

# fmt: off

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


# search_collection
"err_no_matching_collections":
    lambda search_str: f"No collections found containing <yellow>{search_str}</yellow>",
#
"success_matching_collections":
    lambda result_count, search_str: f"Found {result_count} collections containing <yellow>{search_str}</yellow>",
#
"err_runtime":
"""Your search query is too complex to run across all collections.
<yellow>The query string is passed onto the Elasticsearch engine, hence you can group your terms by wrapping them in additional double quotes.
An alternative solution is to limit your search to the main-text field only.\n
For example, instead of 'blood-brain barrier', search for:
- '"blood-brain barrier"'
- 'main-text.text:(blood-brain barrier)'</yellow>
""",


# display_all_collections
"err_no_collections_available": "No collections found... something is wrong.",


# display_collection_details
"no_collection_found_by_name": lambda collection_name_or_key: "No collection found with name of key {collection_name_or_key}",

# display_collections_for_domain
"no_collection_found_by_domain": lambda domain: "No collection found under the '{domain}' domain",




#
"success_file_saved": lambda filename: f"Successully saved <yellow>{filename}</yellow> to your workspace",
"err_rdkit_smiles": lambda err: ["Error verifying SMILES (RDKit)", err],
}


def msg(msg_name, *args):
    return _msg(msg_name, custom_messages=_messages, *args)
