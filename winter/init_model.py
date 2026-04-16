from langchain.chat_models import init_chat_model, BaseChatModel

_MODELS = {
  "sonnet": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "opus": "us.anthropic.claude-opus-4-5-20251101-v1:0",
  "gpt": "gpt-5.1",
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
_BEDROCK_MODELS = {"sonnet", "opus"}
_LIMITED_MODELS = {"gemini_pro", "gemini"}
_NEBIUS_MODELS = {"nemotron", "qwen", "deepseek", "glm", "minimax", "kimi", "gpt_oss"}

_MAX_TOKENS = 2**15


def _init_nebius_model(model_id: str, temp: float) -> BaseChatModel:
    try:
        from langchain_nebius import ChatNebius
    except ImportError as exc:
        raise ImportError(
            "Nebius-backed models require `langchain-nebius`. "
            "Install the package or choose a different provider."
        ) from exc

    return ChatNebius(model=model_id, temperature=temp, max_tokens=_MAX_TOKENS)


def _init_local_model(model_id: str, temp: float) -> BaseChatModel:
    try:
        from langchain_community.llms import VLLM
    except ImportError as exc:
        raise ImportError(
            "Local prover models require `langchain-community` with VLLM support."
        ) from exc

    try:
        import torch
    except ImportError as exc:
        raise ImportError("Local prover models require `torch`.") from exc

    return VLLM(
        model=model_id,
        tensor_parallel_size=torch.cuda.device_count(),
        trust_remote_code=True,
        download_dir="/gpfs/scrubbed/lean-bench/models/",
        vllm_kwargs={
            "gpu_memory_utilization": 0.9,
        },
        temperature=temp,
        max_new_tokens=_MAX_TOKENS,
        top_p=0.95,
    )


def init_model(model_name: str, temp: float) -> BaseChatModel:
    if model_name not in _MODELS:
        raise ValueError(f"Unsupported model: {model_name}")

    model_id = _MODELS[model_name]

    if model_name in _NEBIUS_MODELS:  # Nebius Token Factory models
        llm = _init_nebius_model(model_id, temp)
    elif model_name in _LOCAL_MODELS:  # local models
        llm = _init_local_model(model_id, temp)
    elif model_name in _BEDROCK_MODELS:  # bedrock models
        llm = init_chat_model(model_id, temperature=temp, model_provider="bedrock_converse")
    elif model_name in _LIMITED_MODELS:
        llm = init_chat_model(model_id, temperature=temp, thinking_budget=4000)
    else:  # not bedrock models
        llm = init_chat_model(model_id, temperature=temp)

    return llm
