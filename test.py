import pandas as pd

data = [["A", "B", "C", "D"], ["E", "F", "G", "H"], ["I", "J", "K", "L"]]

df = pd.DataFrame(data, headers=["AAA", "BBB", "CCC", "DDD"])
print(df)
