import jsonlines as jsl
from random import randint
import json

DATA_PATH = f'../data/'
BIG_DATA = 'miniCTX.jsonl'
SMALL_DATA = '50_' + BIG_DATA



def gen_small_dataset(theorems, size):
    small_data = []
    while len(small_data) < size:
        i = randint(0, len(theorems) - 1)
        small_data.append(theorems.pop(i))
    return small_data

def categorize(theorems, dataset):
    cats = {}
    for x in theorems:
        cat = x['name']
        if dataset == 'f2f':
            if 'imo' in cat: cat = 'imo'
            elif 'amc12' in cat: cat = 'amc12'
            elif 'aime' in cat: cat = 'aime'
            elif 'algebra' in cat: cat = 'algebra'
            elif 'induction' in cat: cat = 'induction'
            elif 'numbertheory' in cat: cat = 'numbertheory'
        elif dataset == 'CTX':
            cat = ''
        if cat not in cats.keys():
            cats[cat] = [x]
        else: cats[cat].append(x)
    return cats

def construct_subset(cats, length):
    final = []
    for x in cats.keys():
        final += (gen_small_dataset(cats[x], round(len(cats[x]) / length * 50)))
    return final


theorems = list(jsl.open(DATA_PATH + BIG_DATA))
small_data = construct_subset(categorize(theorems, BIG_DATA.split('mini')[1].split('.')[0]), len(theorems))
with open(DATA_PATH + SMALL_DATA, "w") as f:
    f.writelines([json.dumps(x) + "\n" for x in small_data])
