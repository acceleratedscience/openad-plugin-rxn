from openad_plugin_ds.plugin_params import CLAUSES


description = f"""List the available collections for a certain Deep Search domain, or a list of domains.

{CLAUSES["list_domains"]}

{CLAUSES["save_as"]}

Examples:
- <cmd>ds list collections for domain 'Business Insights'</cmd>
- <cmd>ds list collections for domains ['Materials Science','Scientific Literature']</cmd>
"""
