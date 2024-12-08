from openad_plugin_ds.plugin_params import CLAUSES

description = f"""Search for molecules mentioned in a defined list of patents.
When sourcing patents from a CSV or dataframe, there must be a column named "patent id" (case insensitive).

To find patent IDs, run <cmd>ds find patents ?</cmd>

{CLAUSES['save_as']}

Examples:
- <cmd>ds find molecules in patents from list ['CN108473493B','US20190023713A1']</cmd>
- <cmd>ds find molecules in patents from file 'my_patents.csv'</cmd>
- <cmd>ds find molecules in patents from dataframe my_patents_df</cmd> <soft>(Jupyter Notebook only)</soft>
"""
