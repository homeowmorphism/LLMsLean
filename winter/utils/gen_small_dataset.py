import jsonlines as jsl
from random import randint
import json
from sys import argv

DATA_PATH = f"../data/"
BIG_DATA = "minif2f.jsonl"
SMALL_DATA = "mini_" + BIG_DATA
MINI_SIZE = 10  # The size of the mini dataset

lines = list(jsl.open(DATA_PATH + BIG_DATA))

argc = len(argv)
MINI_SIZE = int(argv[1])
small_data = []
while len(small_data) < MINI_SIZE:
    i = randint(0, len(lines) - 1)
    small_data.append(lines.pop(i))

with open(DATA_PATH + SMALL_DATA, "w") as f:
    f.writelines([json.dumps(x) + "\n" for x in small_data])
