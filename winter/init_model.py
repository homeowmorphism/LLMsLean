from langchain.chat_models import init_chat_model, BaseChatModel
from langchain_community.llms import VLLM
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_nebius import ChatNebius
import torch;

_MODELS = {
  "sonnet": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "opus": "us.anthropic.claude-opus-4-6-v1",
  "gpt": "gpt-5.4",
  "gpt-mini":"gpt-5.4-mini",
  "gpt-nano":"gpt-5.4-nano",
  "gemini": "google_genai:gemini-3-flash-preview",
  "gemini_pro": "google_genai:gemini-3.1-pro-preview",
  "gemini_lite": "google_genai:gemini-3.1-flash-lite-preview",
  "kimina": "AI-MO/Kimina-Prover-72B",
  "deepseek7b": "deepseek-ai/DeepSeek-Prover-V2-7B",
  "goedel": "Goedel-LM/Goedel-Prover-V2-32B",
  "gpt_oss" : "openai/gpt-oss-120b",
  "leanstral" : "mistralai:labs-leanstral-2603",
  "nemotron": "nvidia/nemotron-3-super-120b-a12b",
  "qwen": "Qwen/Qwen3.5-397B-A17B",
  "deepseek": "deepseek-ai/DeepSeek-V3.2",
  "glm": "zai-org/GLM-5",
  "minimax": "MiniMaxAI/MiniMax-M2.1",
  "kimi": "moonshotai/Kimi-K2-Thinking",
}

_LOCAL_MODELS = {"kimina", "deepseek7b", "goedel"}
_BEDROCK_MODELS = {"sonnet", "opus","qwen", "gpt_oss"}
_LIMITED_MODELS = {"gemini_pro", "gemini"}
_NEBIUS_MODELS = {"nemotron", "qwen", "deepseek", "glm", "minimax", "kimi", "gpt_oss"}

_MAX_TOKENS = 2**14

def init_model(model_name: str, temp: float) -> BaseChatModel:
    assert(model_name in _MODELS)
    model_id = _MODELS[model_name]

    if model_name in _NEBIUS_MODELS:  # Nebius Token Factory models
        llm = ChatNebius(model=model_id, temperature=temp, max_tokens=_MAX_TOKENS)
    elif model_name in _LOCAL_MODELS:  # local models
        try:
            llm = VLLM(
                model=model_id,
                tensor_parallel_size=torch.cuda.device_count(),        # Number of GPUs
                trust_remote_code=True,
                download_dir="/gpfs/scrubbed/lean-bench/models/",
                vllm_kwargs={
                    "gpu_memory_utilization": 0.9,
                },
                temperature=temp,
                max_new_tokens=_MAX_TOKENS,
                top_p=0.95,
            )
        except Exception as e:
            print(e)
    elif model_name in _BEDROCK_MODELS:  # bedrock models
        llm = init_chat_model(model_id, temperature=temp, model_provider="bedrock_converse")
    elif model_name in _LIMITED_MODELS:
        llm = init_chat_model(model_id, temperature = temp, thinking_budget = 4000)
    else:  # not bedrock models
        llm = init_chat_model(model_id, temperature=temp)

    return llm
