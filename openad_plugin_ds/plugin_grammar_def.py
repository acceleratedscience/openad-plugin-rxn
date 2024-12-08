import pyparsing as py

search = py.CaselessKeyword("search")
f_or = py.CaselessKeyword("for")
find = py.CaselessKeyword("find")
similar = py.CaselessKeyword("similar")
to = py.CaselessKeyword("to")
save = py.CaselessKeyword("save")
a_s = py.CaselessKeyword("as")
i_n = py.CaselessKeyword("in")
l_ist = py.CaselessKeyword("list")
patents = py.CaselessKeyword("patents")
f_rom = py.CaselessKeyword("from")
file = py.CaselessKeyword("file")
dataframe = py.CaselessKeyword("dataframe")
containing = py.CaselessKeyword("containing")
substructure = py.CaselessKeyword("substructure")
collection = py.CaselessKeyword("collection")
collections = py.CaselessKeyword("collections")
l_ist = py.CaselessKeyword("list")
matches = py.CaselessKeyword("matches")
a_ll = py.CaselessKeyword("all")
details = py.CaselessKeyword("details")
domain = py.CaselessKeyword("domain")
domains = py.CaselessKeyword("domains")
w_ith = py.CaselessKeyword("with")

# Search collection
clause_show = py.Optional(
    py.CaselessKeyword("show").suppress()
    + py.Suppress("(")
    + py.OneOrMore(py.CaselessKeyword("data") | py.CaselessKeyword("docs"))("show")
    + py.Suppress(")")
)
clause_estimate_only = py.Optional(py.CaselessKeyword("estimate").suppress() + py.CaselessKeyword("only").suppress())(
    "estimate_only"
)
clause_return_as_data = py.Optional(
    py.CaselessKeyword("return").suppress()
    + py.CaselessKeyword("as").suppress()
    + py.CaselessKeyword("data").suppress()
)("return_as_data")
