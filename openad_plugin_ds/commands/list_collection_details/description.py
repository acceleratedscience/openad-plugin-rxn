from openad_plugin_ds.plugin_params import CLAUSES

description = f"""Display the details for a collection by providing the collection name or key.

{CLAUSES["list_collections"]}

Examples:
- <cmd>ds list collection details 'Patents from USPTO'</cmd>
- <cmd>ds list collection details 'patent-uspto'</cmd>
"""
