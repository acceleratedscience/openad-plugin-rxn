from openad_plugin_rxn.plugin_params import CLAUSES

description = f"""Predict the reactions of two or more molecules defined by their SMILES.

When providing reactions in a dataframe or CSV, make sure they are stored in a column named "Reactions".


<h1>Parameters</h1>

<cmd>ai_model='<model_name>'</cmd>
    Which model to use for the prodiction.
    To see a list of available models, run <cmd>rxn list models</cmd>

<cmd>topn=<int></cmd>
    Number of predictions to make per reaction. When not set, only one result will be returned.

    
<h1>Clauses</h1>

{CLAUSES["rich_output"]}

{CLAUSES["use_cache"]}

{CLAUSES["save_as"]}


<h1>Examples</h1>

- <cmd>rxn predict reaction 'BrBr.c1ccc2cc3ccccc3cc2c1CCO'</cmd>
- <cmd>rxn predict reaction 'BrBr.c1ccc2cc3ccccc3cc2c1CCO' use cache</cmd>
- <cmd>rxn predict reactions from list ['BrBr.c1ccc2cc3ccccc3cc2c1CCO', 'BrBr.c1ccc2cc3ccccc3cc2c1', 'BrBr.ABC.c1ccc2cc3ccccc3cc2c1']</cmd>
- <cmd>rxn predict reactions from list ['BrBr.c1ccc2cc3ccccc3cc2c1CCO', 'BrBr.c1ccc2cc3ccccc3cc2c1'] using (ai_model='2018-08-31' topn=3)</cmd>
- <cmd>rxn predict reactions from file 'my_reactions.csv' using (topn=5)</cmd>
- <cmd>rxn predict reactions from dataframe my_reactions_df</cmd>
"""
