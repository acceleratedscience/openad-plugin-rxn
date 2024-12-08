from openad_plugin_ds.plugin_params import CLAUSES


description = f"""Scan all available Deep Search collections for a given term, to see which collections will provide relevant results. This is useful when narrowing down document collections for subsequent searches.

When formulating a search query with more than one word, wrap your query in quotes for a literal search, eg. <cmd>'"blood-brain barrier"'</cmd>, or limit the search to only scan the main text field by using <cmd>'main-text.text:("blood-brain barrier")'</cmd>.

You can use the "Collection Key" from the returned table to formulate a next query into a specific collection.
To learn more, run <cmd>ds search collection ?</cmd>.

{CLAUSES["save_as"]}

Examples:
- <cmd>ds list collections containing 'Ibuprofen'</cmd>
- <cmd>ds list collections containing '"blood-brain barrier"'</cmd>
- <cmd>ds list collections containing 'main-text.text:("power conversion efficiency" OR PCE) AND organ*'</cmd>
"""
