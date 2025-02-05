import pyparsing as py

l_ist = py.CaselessKeyword("list")
models = py.CaselessKeyword("models")

interpret = py.CaselessKeyword("interpret")
recipe = py.CaselessKeyword("recipe")

reset = py.CaselessKeyword("reset")
login = py.CaselessKeyword("login")

clear = py.CaselessKeyword("clear")
cache = py.CaselessKeyword("cache")

predict = py.CaselessKeyword("predict")
retrosynthesis = py.MatchFirst([py.CaselessKeyword("retrosynthesis"), py.CaselessKeyword("retro")])

reaction_s = py.MatchFirst([py.CaselessKeyword("reaction"), py.CaselessKeyword("reactions")])
f_rom = py.CaselessKeyword("from")
# Note: we listen to use_saved for backward compatibility with the toolkits. This can be removed in the future.
clause_use_cache = py.Optional(
    py.MatchFirst([py.CaselessKeyword("use cache"), py.CaselessKeyword("use_saved")])("use_cache")
)
clause_rich_output = py.Optional(py.CaselessKeyword("rich")("rich_output"))
