import jsonlines as jsl
from random import randint
import json

DATA_PATH = f"../data/"
BIG_DATA1 = "minif2f_opus_amend.jsonl"
BIG_DATA2 = "minif2f_opus_pass@8.jsonl"
SMALL_DATA1 = "midi_" + BIG_DATA1
SMALL_DATA2 = "midi_" + BIG_DATA2
MINI_SIZE = 80  # The size of the mini dataset

lines1 = list(jsl.open(DATA_PATH + BIG_DATA1))
lines2 = list(jsl.open(DATA_PATH + BIG_DATA2))

small_data1 = []
small_data2 = []
while len(small_data1) < MINI_SIZE:
    i = randint(0, len(lines1) - 1)
    if "Pass" not in lines1[i]["verification"][-1] and "Pass" not in lines2[i]["verification"][-1]:
        small_data1.append(lines1.pop(i))
        small_data2.append(lines2.pop(i))

with open(DATA_PATH + SMALL_DATA1, "w") as f:
    f.writelines([json.dumps(x) + "\n" for x in small_data1])

with open(DATA_PATH + SMALL_DATA2, "w") as f:
    f.writelines([json.dumps(x) + "\n" for x in small_data2])