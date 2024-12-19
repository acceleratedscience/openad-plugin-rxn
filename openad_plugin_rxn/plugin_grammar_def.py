import pyparsing as py

l_ist = py.CaselessKeyword("list")
models = py.CaselessKeyword("models")
interpret = py.CaselessKeyword("interpret")
recipe = py.CaselessKeyword("recipe")

predict = py.CaselessKeyword("predict")
retrosynthesis = py.MatchFirst([py.CaselessKeyword("retrosynthesis"), py.CaselessKeyword("retro")])

reaction_s = py.MatchFirst([py.CaselessKeyword("reaction"), py.CaselessKeyword("reactions")])
f_rom = py.CaselessKeyword("from")
clause_no_cache = py.Optional(py.CaselessKeyword("no cache"))("no_cache")
