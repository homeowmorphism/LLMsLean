import matplotlib.pyplot as plt
from verify import *
import os
import seaborn as sns
import numpy as np

_MODELS = {
  "sonnet": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "opus": "claude-opus-4-5-v1:0",
  "gpt": "gpt-5.1",
  "gemini": "gemini-3-flash-preview",
  "gemini_pro": "gemini-3.1-pro-preview",
  "gemini_lite": "gemini-3.1-flash-lite-preview",
  "kimina": "Kimina-Prover-72B",
  "deepseek": "DeepSeek-Prover-V2-7B",
  "goedel": "Goedel-Prover-V2-32B",
  "qwen" : "qwen3-32b-v1:0",
  "gpt_oss" : "gpt-oss-120b-1:0"
}
_MODEL_PRICE = {
  "sonnet": 15,
  "opus": 25,
  "gpt": 10,
  "gemini": 3,
  "gemini_pro": 12,
  "gemini_lite": 1.5,
  "kimina": 0,
  "deepseek": 0,
  "goedel": 0,
  "qwen" : 0.6,
  "gpt_oss" : 0.6
}
_L_MODEL_PRICE = {
    "kimina":  2,
    "goedel":  2,
    "deepseek":  1
}
_LOCAL_MODELS = {"kimina", "deepseek", "goedel"}

def order(e):
    return e[7:]


def plot_time(input1, input2):
    gt = check_accuracy_all(input1)
    vt = check_accuracy_all(input2)
    leng = []
    for x in range(len(gt)):
        leng.append(x+1)
    plt.title("Gemini 3.1 Flash Lite Accuracy on Minif2f ")
    plt.plot(leng,gt, label="Refine@k")
    plt.plot(leng, vt, label="Pass@k")
    plt.ylabel("Accuracy % on Minif2f")
    plt.xlabel("k")
    plt.ylim([0,100])
    plt.legend()

    plt.show() 

def plot(dir):
    datas = os.listdir(dir)
    datas.sort(key=order)
    leng = []
    dataset = "CTX"
    t = "pass"
    for x in range(4):
        leng.append(x+1)
    for x in datas:
        if dataset in x and t in x:
            plt.plot(leng, check_accuracy_all(os.path.join(dir, x))[:4], label=_MODELS[x.split(f"{dataset}_")[1].split(f"_{t}")[0]])
    plt.ylabel(f"Accuracy % on Mini{dataset}")
    plt.xlabel("k")
    plt.xticks(leng)
    if t =="amend": t="refine"
    plt.title(f"Mini{dataset} Accuracy % for {t.capitalize()}@k")
    plt.ylim([0,100])
    plt.legend()
    plt.show()

def plot_times(dir):
    datas = os.listdir(dir)
    datas.sort(key=order)
    dataset = "f2f"
    t = "amend"
    all_data=[]
    labels = []
    for x in datas:
        times = []
        if dataset in x and t in x:
            if x.split(f"{dataset}_")[1].split(f"_{t}")[0] not in _LOCAL_MODELS:
                theorems = list(jsl.open(os.path.join(dir, x)))
                for y in theorems:
                    times += [i for i in y["model_time"][:4] if i != -1]
                labels.append(_MODELS[x.split(f"{dataset}_")[1].split(f"_{t}")[0]])
                all_data.append(times)

    fig, ax = plt.subplots()

    # Plot the boxplots
    ax.boxplot(all_data, labels=labels, patch_artist=True) # labels parameter sets x-axis labels

    # Add title and labels
    if t =="amend": t="refine"
    ax.set_title(f'Nonlocal Model Time Distributions for {t.capitalize()}@k on Mini{dataset}')
    ax.set_ylabel('Time')
    ax.set_xlabel('Model')

    # Display the plot
    plt.show()

def ct_tokens(dir):
    ds = [["f2f", 'pass'],["CTX", 'pass'],["f2f", 'amend'],["CTX", 'amend']]
    
    for i, z in enumerate(ds):
        fig, ax = plt.subplots()
        datas = os.listdir(dir)
        datas.sort(key=order)
        dataset = ds[i][0]
        t = ds[i][1]

        all_data=[]
        labels = []
        for x in datas:
            times =0
            if dataset in x and t in x:
                name = x.split(f"{dataset}_")[1].split(f"_{t}")[0]
                if name not in _LOCAL_MODELS:
                    theorems = list(jsl.open(os.path.join(dir, x)))
                    acc = len(theorems)
                    for y in theorems:
                        times += sum([i for i in y["output_tokens"][:4] if i != -1])
                    
                    labels.append(_MODELS[name])
                    all_data.append(times*_MODEL_PRICE[name]/1000000/488)
                elif name in _LOCAL_MODELS:
                    theorems = list(jsl.open(os.path.join(dir, x)))
                    acc = len(theorems)
                    for y in theorems:
                        times += sum([i for i in y["model_time"][:4] if i != -1])
                    print(times)
                    labels.append(_MODELS[name])
                    all_data.append(times*_L_MODEL_PRICE[name]*0.9/3600/acc)
        
        j=int(i/2)
        i=i%2
        # Plot the boxplots
        bar = ax.bar(labels,all_data) # labels parameter sets x-axis labels

        ax.bar_label(bar)
        # Add title and labels
        if t =="amend": t="refine"
        ax.set_title(f'Model Price Per Theorem for {t.capitalize()}@4 on Mini{dataset}')
        ax.set_ylabel('Dollars/Theorem (log)')
        ax.set_xlabel('Model')
        ax.set_yscale('log')
        plt.xticks(rotation=-10)
        plt.show()
        
    

def ct_times(dir):
    datas = os.listdir(dir)
    datas.sort(key=order)
    dataset = "f2f"
    t = "pass"

    all_data=[]
    labels = []
    for x in datas:
        times =0
        if dataset in x and t in x:
            name = x.split(f"{dataset}_")[1].split(f"_{t}")[0]
            if name in _LOCAL_MODELS:
                acc = check_accuracy_all(os.path.join(dir, x))[3]*488/100
                if acc == 0 : continue
                print(acc)
                theorems = list(jsl.open(os.path.join(dir, x)))
                for y in theorems:
                    times += sum([i for i in y["model_time"][:4] if i != -1])
                print(times)
                labels.append(_MODELS[name])
                all_data.append(times*_L_MODEL_PRICE[name]*0.9/3600/acc)
    fig, ax = plt.subplots()

    # Plot the boxplots
    ax.bar(labels,all_data) # labels parameter sets x-axis labels

    # Add title and labels
    if t =="amend": t="refine"
    ax.set_title(f'Nonlocal Model Output Price Per Correct Theorem for {t.capitalize()}@4 on Mini{dataset}')
    ax.set_ylabel('Dollars/Correct Theorem')
    ax.set_xlabel('Model')
    ax.set_ylim(0, 0.175)

    # Display the plot
    plt.show()

def scatter_tokens(dir):
    datas = os.listdir(dir)
    datas.sort(key=order)
    dataset = "CTX"
    t = "amend"

    input = []
    output = []
    color = []
    for x in datas:
        if dataset in x and t in x:
            name = x.split(f"{dataset}_")[1].split(f"_{t}")[0]
            if name not in _LOCAL_MODELS:
                theorems = list(jsl.open(os.path.join(dir, x)))
                for theorem in theorems:
                    for i in range(len(theorem["output_tokens"])):
                        if "Pass" not in theorem['verification'][i]:
                            input.append(theorem['input_tokens'][i])
                            output.append(theorem['output_tokens'][i])
                            color.append('blue')
                        else:
                            input.append(theorem['input_tokens'][i])
                            output.append(theorem['output_tokens'][i])
                            color.append('red')
                            break
    plt.scatter(input, output, c=color)
    plt.xlabel('Input Tokens')
    plt.ylabel('Output Tokens')
    plt.title('Output Tokens vs. Input Tokens (Red Passed)')
    plt.show()



if __name__ == "__main__":
    ct_tokens("../data/test_data")
    #plot_time("../data/Final Tests/miniCTX_opus_amend.jsonl","../data/Final Tests/miniCTX_opus_pass@8.jsonl")
