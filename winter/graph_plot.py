import matplotlib.pyplot as plt
from verify import *

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

if __name__ == "__main__":
    plot_time("../data/Final Tests/minif2f_opus_amend.jsonl","../data/Final Tests/minif2f_opus_pass@8.jsonl")
