from openad_plugin_ds.plugin_params import CLAUSES


description = f"""Search a given collection in the Deep Search repository.


<h1>Parameters</h1>

<cmd><collection_name_or_key></cmd>
    The name or index key for a collection.
    {CLAUSES["list_collections"]}

<cmd><search_query></cmd>
    The search string to search for.
    Supports elastic search string query syntax:
        <cmd>+</cmd>  AND operation
        <cmd>|</cmd>  OR operation
        <cmd>-</cmd>  Negate a single token
        <cmd>"</cmd>  Wrap a number of tokens to signify a phrase for searching
        <cmd>*</cmd>  Prefix query when placed at the end of a term
        <cmd>()</cmd> Grouping for precedence
        <cmd>~N</cmd> Edit distance (fuzziness) when placed after a word,
           or slop amount when placed after a phrase
    More information can be found at:
    https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-simple-query-string-query.html#simple-query-string-query-notes

    
<h1>The USING clause</h1>

<cmd>slop=<integer></cmd>
    The slop amount of your elastic query. This is the maximum number of positions allowed between matching tokens. Recommended to be between 0-5, defaults to 3.
    Note that a higher slop will slow down the search process.
    Example: searching for 'power efficiency' will match 'power conversion efficiency' with a slop of 1 or higher, but not with a slop of 0.

<cmd>limit_results=<integer></cmd>
    Limit the number of results returned. Note that this does not speed up the search process.

<cmd>elastic_page_size=<integer></cmd>
    The number of records to scan in each iteration of the paginated elastic query, reflected by the progress bar.
    Defaults to 50. Increasing this number may speed up the search process but will cause the search to consume more memory.

<cmd>elastic_id=<elastic_id></cmd>
    Advanced: The elastic search engine used. This will always be 'default' for publicly available collections, but could be customized if you're running a local instance of Deep Search.


<h1>Clauses</h1>

<cmd>show (data)</cmd>
    Display structured data from within the documents.

<cmd>show (docs)</cmd>
    Display document context and preview snippet.

<cmd>show (data docs)</cmd>
    Combine both data and docs.

<cmd>estimate only</cmd>
    Determine the potential number of hits.

<cmd>save as</cmd>
    save the results as a csv file in your current workspace.


<h1>Examples</h1>

Look for documents that contain discussions on power conversion efficiency:
<cmd>ds search collection 'arxiv-abstract' for 'ide("power conversion efficiency" OR PCE) AND organ*' USING (limit_results=10 slop=0) show (docs)</cmd>

Compare result count with differenty slop amounts:
<cmd>ds search collection 'arxiv-abstract' for '"power efficiency"' USING (slop=0) estimate only</cmd>
<cmd>ds search collection 'arxiv-abstract' for '"power efficiency"' USING (slop=1) estimate only</cmd>
<cmd>ds search collection 'arxiv-abstract' for '"power efficiency"' USING (slop=5) estimate only</cmd>

Search the PubChem archive for 'Ibuprofen', display related molecules' data, the inspect molecules in the GUI.
<cmd>ds search collection 'pubchem' for 'Ibuprofen' show (data)</cmd>
<cmd>result open</cmd>

Search for patents which mention a specific SMILES molecule:
<cmd>ds search collection 'patent-uspto' for '"CC(CCO)CCCC(C)C"' show (data)</cmd>
"""

# <cmd>return as data</cmd>
#     For Notebook or API mode. Removes all styling from the Pandas DataFrame, ready for further processing.
