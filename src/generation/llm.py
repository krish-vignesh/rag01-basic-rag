from langchain_nvidia_ai_endpoints import ChatNVIDIA
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

llm = ChatNVIDIA(
    model="nvidia/nemotron-3.5-lightning-30b-a3b",
    temperature=0.2,
    max_completion_tokens=128,
    chat_template_kwargs={
        "enable_thinking": False
    }
)