from openad_plugin_rxn.plugin_params import CLAUSES

description = f"""Get a molecule's retrosynthesis route prediction.


<h1>Parameters</h1>

<cmd>availability_pricing_threshold=<int></cmd>
    Maximum price in USD per g/ml of compounds. The default is no threshold (0).

<cmd>available_smiles='<smiles>.<smiles>.<smiles>'</cmd>
    List of molecules available as precursors, delimited with a period. The default is no limit.

<cmd>exclude_smiles='<smiles>.<smiles>.<smiles>'</cmd>
    List of molecules to exclude from the set of precursors, delimited with a period. The default is none.

<cmd>exclude_substructures='<smiles>.<smiles>.<smiles>'</cmd>
    List of substructures to exclude from the set of precursors, delimited with a period. The default is none.

<cmd>exclude_target_molecule=<boolean></cmd>
    Excluded target molecule. The default is True.

<cmd>fap=<float></cmd>
    Every retrosynthetic step is evaluated with the FAP, and is only retained when forward confidence is greater than the FAP value. The default is 0.6.

<cmd>max_steps=<int></cmd>
    The maximum number steps in the results. The default is 5.

<cmd>nbeams=<int></cmd>
    The maximum number of beams exploring the hypertree. The default is 10.

<cmd>pruning_steps=<int></cmd>
    The number of steps to prune a hypertree. The default is 2.

<cmd>ai_model='<model_name>'</cmd>
    What version of the retrosynthesis prediction model to use. The default is '2020-07-01'.
    To see available model versions, run <cmd>rxn list models</cmd> and look at the versions listed next to retrosynthesis-prediction-model.


<h1>Clauses</h1>

{CLAUSES["rich_output"]}

{CLAUSES["use_cache"]}

<cmd>return df</cmd>
    Return the reaction tree as a Pandas DataFrame instead of as JSON.

    
<h1>Examples</h1>

- <cmd>rxn predict retrosynthesis 'BrCCc1cccc2c(Br)c3ccccc3cc12'</cmd>
- <cmd>rxn predict retrosynthesis 'BrCCc1cccc2c(Br)c3ccccc3cc12' use cache</cmd>
- <cmd>rxn predict retrosynthesis 'BrCCc1cccc2c(Br)c3ccccc3cc12' using (max_steps=3)</cmd>
- <cmd>rxn predict retrosynthesis 'BrCCc1cccc2c(Br)c3ccccc3cc12' using (max_steps=6 ai_model='12class-tokens-2021-05-14')</cmd>
"""
