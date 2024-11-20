import pyparsing as py

search = py.CaselessKeyword("search")
f_or = py.CaselessKeyword("for")
similar = py.CaselessKeyword("similar")
to = py.CaselessKeyword("to")
save = py.CaselessKeyword("save")
a_s = py.CaselessKeyword("as")
# subject = py.Word(py.alphanums + "_-~.:;?/|\\+<=>*@#$%&")
# subject_list = py.delimitedList(subject, delim=",")
# validate = py.CaselessKeyword("validate")
# result = py.CaselessKeyword("result")
# visualize = py.CaselessKeyword("visualize") | py.CaselessKeyword("vizualize")
