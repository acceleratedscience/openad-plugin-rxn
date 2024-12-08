from openad_plugin_ds.plugin_params import CLAUSES

description = f"""Search for molecules by substructure, as defined by the <cmd><smiles></cmd>.

{CLAUSES['save_as']}

Examples:
- <cmd>ds find molecules with substructure C1(C(=C)C([O-])C1C)=O</cmd>
- <cmd>ds find molecules with substructure 'C1=CCCCC1' save as 'my_mol'</cmd>
"""
