# fmt: off
from openad.helpers.output_msgs import msg as _msg

err_runtime = """Your search query is too complex to run across all collections.
<yellow>The query string is passed onto the Elasticsearch engine, hence you can group your terms by wrapping them in additional double quotes.
An alternative solution is to limit your search to the main-text field only.\n
For example, instead of 'blood-brain barrier', search for:
- '"blood-brain barrier"'
- 'main-text.text:(blood-brain barrier)'</yellow>
"""

_messages = {
    # Shared / general
    "err_deepsearch": lambda err: ["There was an error calling Deep Search", err],
    "err_invalid_identifier": "Invalid molecule identifier",
    "err_file_not_found": lambda filename: f"File <yellow>{filename}</yellow> does not exist",

    # Find mols in patents
    "err_no_patent_ids_found": lambda src_type: f"Failed to find patent ids in the provided {src_type}",

    # Find mols similar
    "err_no_similar_mols": "No similar molecules found",

    # Find mols by substructure
    "err_no_substr_mols": "No molecules found with the provided substructure",

    # Find patents
    "success_patents_found": lambda result_count, result_type, identifier: f"We found {result_count} patents containing the requested {result_type}:\n<yellow>{identifier}</yellow>",
    "err_no_patents_found": lambda result_type, identifier: f"No patents found containing {result_type}:\n<yellow>{identifier}</yellow>"
        + (
            "\n<soft>Note: The identifier was not recognized to be a SMILES or InChI so it is assumed to be an InChIKey</soft>"
            if result_type == "InChIKey" else ""
        ),

    # List all collection
    "err_no_collections_available": "No collections found... Something is wrong",

    # List all domains
    "err_no_domains_available": "No domains found... Something is wrong",

    # List collection details
    "err_no_collection_found_by_name": lambda collection_name_or_key: f"No collection found with <yellow>{collection_name_or_key}</yellow> as name or key",

    # List collections containing
    "err_runtime": err_runtime,
    "err_no_matching_collections": lambda search_str: f"No collections found containing <yellow>{search_str}</yellow>",
    "success_matching_collections": lambda result_count, search_str: f"Found {result_count} collections containing <yellow>{search_str}</yellow>",

    # List collections for domain
    "err_no_collection_found_by_domain":
        lambda domain_list: f"No collection found under the <yellow>{domain_list[0]}</yellow> domain"
            if len(domain_list) == 1 else ("No collections found under the provided domains:\n- " + "\n- ".join(domain_list)),

    # Search collections
    "err_invalid_collection_id": "Invalid <yellow>collection_name_or_key</yellow>, please choose from the following:",
    "err_invalid_elastic_id": "Invalid <yellow>elastic_id</yellow>, please choose from the following:",
}


def msg(msg_name, *args):
    return _msg(msg_name, custom_messages=_messages, *args)
