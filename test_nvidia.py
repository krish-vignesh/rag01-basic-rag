from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA

load_dotenv()

llm=ChatNVIDIA(
    model="nvidia/nemotron-3.5-lightning-30b-a3b",
    temperature=1.0,
        max_completion_tokens=128,
        chat_template_kwargs={
            "enable_thinking": False
        }
    
)

response = llm.invoke(
    "Explain what RAG is in two simple sentences."
)

print(response.content)