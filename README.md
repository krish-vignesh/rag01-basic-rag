# 🚀 RAG01 - Basic RAG System

A Retrieval-Augmented Generation (RAG) chatbot built using LangChain, ChromaDB, HuggingFace Embeddings, and Ollama.

This project demonstrates the complete RAG pipeline from document ingestion to answer generation, evaluation, and observability.

---

## 🛠 Tech Stack

- 🦜 LangChain
- 🗄️ ChromaDB
- 🤗 HuggingFace Embeddings
- 🦙 Ollama
- 🤖 Llama 3.2
- 📊 RAGAS
- 🔍 LangSmith
- 🐍 Python

---

## ✨ Features

### 📄 Document Processing
- PDF Ingestion
- Recursive Text Chunking
- HuggingFace Embeddings
- Chroma Vector Store

### 🔎 Retrieval
- Semantic Vector Search
- MMR Retrieval Strategy
- Cross-Encoder Re-Ranking
- Top-K Candidate Retrieval (20)
- Top-5 Context Selection

### 🤖 Generation
- Local LLM using Ollama
- Llama 3.2
- Context-Aware Question Answering
- Prompt Engineering

### 📈 Evaluation
- Ground Truth Dataset Creation
- Automated Answer Generation
- RAGAS Evaluation Pipeline

### 🔍 Observability
- LangSmith Tracing
- Retrieval Inspection
- LLM Call Monitoring
- Pipeline Debugging
- Latency Analysis

### 🧪 Experiments
- Cross-Encoder Model Testing
- Retrieval + Re-Ranking Pipeline Testing

---

RAG01_BASIC_RAG/
│
├── data/
│   └── NovaTech_HR_Policy_Handbook.pdf
│
├── evaluation/
│   ├── eval_dataset.csv
│   └── eval_results.csv (ignored)
│
├── experiments/
│   ├── test_pipeline.py
│   └── test_reranker.py
│
├── src/
│   ├── ingest.py
│   ├── retrieve.py
│   ├── reranker.py
│   ├── chatbot.py
│   ├── generate_answers.py
│   └── run_ragas.py
│
├── vector_store/
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 🏗️ Current Architecture

```text
User Question
      │
      ▼
Retriever (Top 20)
      │
      ▼
Extract Chunk Text
      │
      ▼
Cross-Encoder Re-Ranker
      │
      ▼
Top 5 Relevant Chunks
      │
      ▼
Prompt Construction
      │
      ▼
Llama 3.2
      │
      ▼
Final Answer
```

---

## 🚀 Getting Started

### 1️⃣ Clone Repository

```bash
git clone <your-repository-url>
cd RAG01_BASIC_RAG
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
```

### 3️⃣ Activate Environment

```bash
venv\Scripts\activate
```

### 4️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 5️⃣ Ingest Documents

```bash
python src/ingest.py
```

### 6️⃣ Run Chatbot

```bash
python src/chatbot.py
```

---

## 📊 Evaluation Workflow

1. Create Ground Truth Dataset
2. Generate RAG Answers
3. Compare against Ground Truth
4. Evaluate using RAGAS Metrics
5. Analyze Retrieval using LangSmith
6. Improve Retrieval with Cross-Encoder Re-Ranking

---

## 🎯 Learning Outcomes

This project helped me understand:

- 📄 PDF Loading
- ✂️ Recursive Text Chunking
- 🤗 HuggingFace Embeddings
- 🗄️ Chroma Vector Database
- 🔎 Semantic Search
- ⚖️ MMR Retrieval
- 🎯 Cross-Encoder Re-Ranking
- 🧠 Prompt Construction
- 🤖 Local LLM Deployment (Ollama)
- 📊 RAGAS Evaluation
- 🔍 LangSmith Observability
- 🧪 AI Retrieval Debugging
---

## 🔮 Future Improvements

- ✅ LangSmith Integration
- ✅ Cross-Encoder Re-Ranking
- ⏳ Hybrid Search (BM25 + Vector Search)
- ⏳ Parent Document Retriever
- ⏳ Query Expansion
- ⏳ Guardrails & Hallucination Detection
- ⏳ Advanced Evaluation Dashboard
- ⏳ Agentic RAG

---

## 👨‍💻 Author

Vignesh Krishna

MBA Business Analytics | Data Science & AI Enthusiast
