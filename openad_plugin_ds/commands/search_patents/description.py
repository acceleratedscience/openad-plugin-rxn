from openad_plugin_ds.plugin_params import CLAUSES

description = f"""Searches for patents that contain mentions of a given molecule. The queried molecule can be described by its SMILES, InChI or InChIKey.

{CLAUSES['save_as']}

Examples:
- <cmd>ds search for patents containing molecule CC(C)(c1ccccn1)C(CC(=O)O)Nc1nc(-c2c[nH]c3ncc(Cl)cc23)c(C#N)cc1F</cmd>
- <cmd>ds search for patents containing molecule 'CC(C)(c1ccccn1)C(CC(=O)O)Nc1nc(-c2c[nH]c3ncc(Cl)cc23)c(C#N)cc1F' save as 'patents'</cmd>
- <cmd>ds search for patents containing molecule InChI=1S/C24H20ClFN6O2/c1-24(2,18-5-3-4-6-28-18)19(9-20(33)34)31-23-17(26)7-13(10-27)21(32-23)16-12-30-22-15(16)8-14(25)11-29-22/h3-8,11-12,19H,9H2,1-2H3,(H,29,30)(H,31,32)(H,33,34)</cmd>
- <cmd>ds search for patents containing molecule JUPUMSRQQQUOLP-UHFFFAOYSA-N save as 'patents'</cmd>
- <cmd>ds search for patents containing molecule 'JUPUMSRQQQUOLP-UHFFFAOYSA-N'</cmd>
"""
