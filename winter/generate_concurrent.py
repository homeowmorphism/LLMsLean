from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from langchain.agents import create_agent
from langfuse.langchain import CallbackHandler
import re
from tqdm import tqdm
import jsonlines as jsl
from langfuse import observe
from concurrent.futures import ThreadPoolExecutor, as_completed
from init_model import init_model
import threading
import time

# prompt stem for a new lean proof
PROMPT_STEM = """
        You are an expert in the LEAN 4 theorem prover. Your goal is to generate a correct, formalized proof in LEAN 4 for the provided theorem within the provided context.
        You may explain your reasoning concisely but output the FULL, COMPLETE formalized proof at the END of your response in a fenced code block with the prefix FINAL — for example: FINAL```lean ... ```.
        You may include a language tag such as 'lean' or 'lean4' after the opening backticks.
        Assume that all of Mathlib is imported. **DO NOT** provide your own import statements. **DO NOT** put anything except valid lean in your final proof. IMMEDIATELY stop after appending the closing ```.
        Your theorem is: """

# prompt stem for an amend
AMEND_STEM = """
        You are an expert in the LEAN 4 theorem prover. Your goal is to amend an incorrect formalized proof into a correct, formalized proof.
        You may explain your reasoning but output the full, complete formalized proof at the end of your response in a fenced code block with the prefix FINAL — for example: FINAL```lean ... ```.
        You may include a language tag such as 'lean' or 'lean4' after the opening backticks.
        Assume that all of Mathlib is imported. Do not provide your own import statements. """

# Extraction patterns tried in order (see cleanup())
_RE_FINAL     = re.compile(r"FINAL`{1,6}(?:lean4?|LEAN4?)?[ \t]*\n?([\S\s]+?)`{1,6}", re.IGNORECASE)
_RE_LEAN_TAG  = re.compile(r"```(?:lean4?|LEAN4?)\s*([\S\s]+?)```")
_RE_ANY_BLOCK = re.compile(r"```\w*\s*([\S\s]+?)```")
_RE_BARE      = re.compile(r"(?:theorem|lemma)\b[\S\s]+")

thread_local = threading.local()

def get_model(model_name, temp):
    """Helper to get or initialize the model for the current thread."""
    if not hasattr(thread_local, "model"):
        thread_local.model = init_model(model_name, temp)
    return thread_local.model

def _trim_to_theorem(snippet):
    """Strip any preamble before the first 'theorem' or 'lemma' keyword."""
    m = re.search(r"\b(?:theorem|lemma)\b", snippet)
    return snippet[m.start():].strip() if m else snippet.strip()

def cleanup(response):
    """
    Extract a Lean 4 proof from a model response using a tiered fallback strategy:
      1. Explicit FINAL``` marker (as prompted), with optional lean/lean4 language tag.
      2. Fenced code block with a lean/lean4 language tag.
      3. Any fenced code block that contains a theorem/lemma keyword.
      4. Bare theorem/lemma keyword in plain text.
    Falls back to the raw response if nothing structured is found.
    """
    # Strategy 1: explicit FINAL marker — trust it regardless of content
    matches = _RE_FINAL.findall(response)
    if matches:
        return _trim_to_theorem(max(matches, key=len))

    # Strategy 2: ```lean / ```lean4 block — accept any lean-tagged block
    # (model may return just a tactic body like `by simp` without restating the theorem)
    matches = _RE_LEAN_TAG.findall(response)
    if matches:
        return _trim_to_theorem(max(matches, key=len))

    # Strategy 3: any fenced code block containing a theorem/lemma
    for m in _RE_ANY_BLOCK.finditer(response):
        if re.search(r"\b(?:theorem|lemma)\b", m.group(1)):
            return _trim_to_theorem(m.group(1))

    # Strategy 4: bare theorem/lemma keyword in plain text
    m = _RE_BARE.search(response)
    if m:
        return m.group(0).strip()

    # Give up — return raw response and let verification report the error
    return response

@observe
def generation_started():
    return

def process_single_theorem(theorem, model_name, temp, amend):
    langfuse_handler = CallbackHandler()
    
    # initialize the model
    model = get_model(model_name, temp)
    assert(model != None)

    if 'responses' not in theorem.keys():
        theorem["responses"] = []    

    if amend:
        for x in theorem.get("verification", [""]):
            if "Pass" in x:
                theorem.setdefault("responses", []).append(theorem["responses"][-1])
                return theorem

    prompt = PROMPT_STEM + theorem["header"] + "\n" + theorem["formal_statement"]
    if amend:
        prompt = AMEND_STEM + f"""
        The incorrect proof is: {theorem["responses"][-1]}
        And the reason it is incorrect is: {theorem['verification'][-1]}
        A reminder of the theorem statement:{theorem["header"]}\n {theorem["formal_statement"]}
        """
    
    try:
        t = time.perf_counter()
        response = model.invoke(
            prompt,
            config={"callbacks": [langfuse_handler]}
        )
        t = time.perf_counter() - t

        theorem["responses"].append(cleanup(response if type(response) == str else response.text))

        theorem.setdefault("model_time", []).append(t)

        if hasattr(response, 'usage_metadata'):
            theorem.setdefault("input_tokens", [])
            theorem.setdefault("output_tokens", [])
            theorem["input_tokens"].append(response.usage_metadata["input_tokens"])
            theorem["output_tokens"].append(response.usage_metadata["output_tokens"])
    except Exception as e:
        print(e)
        # AWS Bedrock throttling: signal the caller to abort and retry later.
        # e.response is a dict for boto3 exceptions but an httpx.Response object
        # for other providers, so guard with a try/except rather than hasattr alone.
        try:
            if e.response.get('Error', {}).get('Code') == 'ThrottlingException':
                return -1
        except AttributeError:
            pass
        theorem["responses"].append("ERROR: Generation failed")
    
    return theorem

def generate_concurrent(input, output, model, temp, amend, workers=4):
    generation_started()
    load_dotenv("../.env")
    theorems = list(jsl.open(input))
    results = [None] * len(theorems)
    
    desc = f"{"Amending" if amend else "Generating"} Results"
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_index = {
            executor.submit(process_single_theorem, theorems[i], model, temp, amend): i for i in range(len(theorems))
        }

        pbar = tqdm(as_completed(future_to_index), total=len(theorems), desc=desc)
        
        count = 0
        for future in pbar:
            idx = future_to_index[future]
            result = future.result()
            if result == -1:
                if "responses" in theorems[0].keys():
                    print(f"Generation is being throttled, please wait and try again soon. Your attempt made it through {len(theorems[0]["responses"])} iterations\n To continue run: python run.py --repair {model} {model} [dataset] [workers] [loops remaining]")
                else:
                    print(f"Generation is being throttled, please wait and try again soon. Your attempt made it through 0 iterations\n To continue run: python run.py --repair {model} {model} [dataset] [workers] [loops remaining]")
                
                return -1
            results[idx] = result
            
            count += 1
            if count % 1 == 0:
                with jsl.open("../data/temp.jsonl", mode="w") as writer:
                    writer.write_all([r for r in results if r is not None])

    with jsl.open(output, mode="w") as writer:
        writer.write_all(results)
    
    return results
