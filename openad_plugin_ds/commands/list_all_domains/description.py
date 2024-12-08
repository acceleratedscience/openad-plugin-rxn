from openad_plugin_ds.plugin_params import CLAUSES


description = f"""List all available Deep Search domains.

{CLAUSES["list_domains"]}

{CLAUSES["save_as"]}

Examples:
- <cmd>ds list all domains</cmd>
- <cmd>ds list all domains save as 'all_domains'</cmd>
"""
