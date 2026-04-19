import jsonlines as jsl
import os

DATA_PATH = f'../data/'
BIG_DATA = 'miniCTX.jsonl'
SMALL_DATA = '50_' + BIG_DATA

all_theorems = list(jsl.open(DATA_PATH + BIG_DATA))
sub_theorems = list(jsl.open(DATA_PATH + SMALL_DATA))

tot = {}
sub = []
for x in all_theorems:
    tot[x['name']] = [0,0]
    if x in sub_theorems:
        sub.append(x['name'])

for test in os.listdir(DATA_PATH+'test_data/'):
    if BIG_DATA.split('mini')[1].split('.')[0] in test:
        data = list(jsl.open(DATA_PATH+'test_data/'+ test))
        for item in data:
            p = 0
            t = len(item['verification'])
            for x in item['verification']:
                if 'Pass' in x: p+=1
            if not 'name' in item.keys(): 
                print(test)
                break
            tot[item['name']][0]+=p
            tot[item['name']][1]+=t
avg = 0
savg = 0
for x in tot.keys():
    avg+= tot[x][0]/tot[x][1]
    if x in sub:
        savg += tot[x][0]/tot[x][1]
print(avg/len(all_theorems))
print(savg/50)
