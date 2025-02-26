import os
from dotenv import load_dotenv
load_dotenv()
from langchain_nvidia_ai_endpoints import ChatNVIDIA


# r1 = ChatNVIDIA(model="deepseek-ai/deepseek-r1",
#                 api_key=os.getenv("NVIDIA_API_KEY"), 
#                 temperature=0.6,
#                 top_p=0.7,
#                 max_tokens=4096)



from langchain_openai import ChatOpenAI

r1 = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    model="deepseek/deepseek-r1",
)   