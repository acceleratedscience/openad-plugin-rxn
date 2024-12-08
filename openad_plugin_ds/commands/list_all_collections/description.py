from openad_plugin_ds.plugin_params import CLAUSES


description = f"""List all available Deep Search collections.

Add the <cmd>description</cmd> clause to include a description of each collection.

{CLAUSES["save_as"]}

Examples:
- <cmd>ds list all collections</cmd>
- <cmd>ds list all collections details</cmd>
- <cmd>ds list all collections save as 'all_collections.csv'</cmd>
"""
