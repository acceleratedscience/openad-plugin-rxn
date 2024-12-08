from openad_plugin_ds.plugin_params import CLAUSES

description = f"""Search for molecules that are similar to the provided molecule or substructure as provided in the <cmd><smiles></cmd>.

{CLAUSES['save_as']}

Examples:
- <cmd>ds find molecules similar to CC(=CCC/C(=C/CO)/C)C</cmd>
- <cmd>ds find molecules similar to 'C1(C(=C)C([O-])C1C)=O'</cmd>
- <cmd>ds find molecules similar to CC1CCC2C1C(=O)OC=C2C save as 'similar_mols'</cmd>
- <cmd>ds find molecules similar to CC1=CCC2CC1C2(C)C save as 'similar_mols.csv'</cmd>
"""
