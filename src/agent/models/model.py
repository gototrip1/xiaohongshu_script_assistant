from langchain.chat_models import init_chat_model

from agent.models.env_utils import QWEN3_API_KEY, QWEN3_BASE_URL, ZHIPU_API_KEY, ZHIPU_BASE_URL

qwen_llm = init_chat_model(
    model='qwen3.7-max-2026-05-17',
    model_provider='openai',
    api_key=QWEN3_API_KEY,
    base_url=QWEN3_BASE_URL,
)

zhipu_llm = init_chat_model(
    model='glm-4.7-flash',
    model_provider='openai',
    api_key=ZHIPU_API_KEY,
    base_url=ZHIPU_BASE_URL,
)
