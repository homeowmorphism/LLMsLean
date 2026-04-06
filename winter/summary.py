import jsonlines
import os

def summarize_jsonl_by_generate(filepath):
    total_theorems = 0
    total_responses = 0
    total_generation_fail = 0
    total_empty_string = 0
    total_sorry_admit = 0
    total_uncleaned = 0

    try:
        with jsonlines.open(filepath) as reader:
            for theorem in reader:
                total_theorems += 1
                
                responses = theorem.get("responses", [])
                
                total_responses += len(responses)
                
                # Count the occurrences by checking the generated responses directly
                for raw_response in responses:
                    clean_response = raw_response.strip()
                    
                    if not clean_response:
                        total_empty_string += 1
                    elif "ERROR:" in raw_response or "Generation failed" in raw_response:
                        total_generation_fail += 1
                    elif "sorry" in clean_response or "admit" in clean_response:
                        total_sorry_admit += 1
                    if "FINAL" in raw_response or "```" in raw_response:
                        total_uncleaned += 1    

        print(f"Summary by Generation for {filepath}")
        print(f"Total Theorems                     : {total_theorems}")
        print(f"Total Responses                    : {total_responses}")
        print(f"Total Generation Fails             : {total_generation_fail}")
        print(f"Total Empty Strings                : {total_empty_string}")
        print(f"Total 'Sorry' or 'Admit'           : {total_sorry_admit}")
        print(f"Total Uncleaned Responses          : {total_uncleaned}")

    except Exception as e:
        print(f"Error reading or parsing the file: {e}")

def summarize_jsonl_by_verify(filepath):
    total_theorems = 0
    total_verifications = 0
    total_generation_fail = 0
    total_empty_string = 0
    total_verification_timeout = 0
    total_mismatch = 0
    total_fail = 0

    try:
        with jsonlines.open(filepath) as reader:
            for theorem in reader:
                total_theorems += 1
                
                responses = theorem.get("responses", [])
                verifications = theorem.get("verification", [])
                
                if len(responses) != len(verifications):
                    total_mismatch += 1
                total_verifications += len(verifications)    
                
                # Count the occurrences of specific errors across all verification attempts
                for v in verifications:
                    if "Fail" in v:
                        total_fail += 1
                    if "Generation failed" in v:
                        total_generation_fail += 1
                    elif "Empty string" in v:
                        total_empty_string += 1
                    elif "timed out" in v:
                        total_verification_timeout += 1

        print(f"Summary by Verify for {filepath}")
        print(f"Total Theorems                   : {total_theorems}")
        print(f"Total Fails                      : {total_fail}")
        print(f"Total Verifications              : {total_verifications}")
        print(f"Total Generation Fails           : {total_generation_fail}")
        print(f"Total Empty Strings              : {total_empty_string}")
        print(f"Total Verification Timeouts      : {total_verification_timeout}")
        print(f"Total Theorems with Mismatched Len : {total_mismatch}")
        print("-" * 50)

    except Exception as e:
        print(f"Error reading or parsing the file: {e}")

if __name__ == "__main__":
    target_dir = "data/Collected_Data/"
    for filename in os.listdir(target_dir):
        filepath = os.path.join(target_dir, filename)
        summarize_jsonl_by_generate(filepath)
        summarize_jsonl_by_verify(filepath)