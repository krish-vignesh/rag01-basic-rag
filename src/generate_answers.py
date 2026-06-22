
import pandas as pd
from retrieve import retrieve_docs
from retrieve import llm
from dotenv import load_dotenv #! importing load_dotenv to load environment variables from .env file
import os #! importing os to access environment variables


load_dotenv() #! loading environment variables from .env file
print("Tracing:", os.getenv("LANGSMITH_TRACING"))
print("Project:", os.getenv("LANGSMITH_PROJECT"))


df = pd.read_csv("evaluation/eval_dataset.csv")

results = []
   
for index, row in df.iterrows():
    question = row['question']
    ground_truth = row['ground_truth']

    docs = retrieve_docs(question)
    retrieved_contexts = [
    doc.page_content
    for doc in docs
    ]
    context = "\n".join(retrieved_contexts)
    prompt = f"""
    Answer the question only using the context below.

    Context:
    {retrieved_contexts}

    Question:
    {question}
    """

    response = llm.invoke(prompt)  # generating response based on user query and retrieved documents
    answer = response.content 

    results.append(
        {
            "question": question,
            "answer": answer,
            "retrieved_contexts": retrieved_contexts,
            "ground_truth": ground_truth,
            
        }
    )

results_df = pd.DataFrame(results)
print(results_df.head())
results_df.to_csv("evaluation/eval_results.csv", index=False)


df = pd.read_csv("evaluation/eval_results.csv")

print(df.shape)

print(df.columns)

print(df.iloc[0])