from sentence_transformers import CrossEncoder

model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

print("Model loaded successfully!")

question = "how many sick leave are provided per year?"

chunks=[
    "Employees receive parental leave after childbirth.",
    "Employees are entitled to 12 sick leave days annually.",
    "Employees must return company assets during exit."
]


pairs = [[question, c] for c in chunks] 

scores=model.predict(pairs)

print(scores)

for chunk, score in zip(chunks, scores):
    print(f"score: {score:.4f}")
    print(chunk)
    print("-" *50)

chunk_scores = list(zip(chunks, scores))

reranked = sorted(
    chunk_scores,
    key=lambda x:x[1],
    reverse = True
)

print(reranked)