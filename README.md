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
- Text Chunking
- Vector Embeddings
- Chroma Vector Store

### 🔎 Retrieval
- Semantic Search
- MMR Retrieval Strategy
- Context Retrieval

### 🤖 Generation
- Local LLM using Ollama
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
- Latency Analysis

---

## 📂 Project Structure

```text
RAG01_BASIC_RAG/
│
├── data/
│   └── NovaTech_HR_Policy_Handbook.pdf
│
├── evaluation/
│   ├── eval_dataset.csv
│   └── eval_results.csv (ignored)
│
├── src/
│   ├── ingest.py
│   ├── retrieve.py
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

## 🔄 RAG Pipeline

```text
User Question
      │
      ▼
Embedding Model
      │
      ▼
Chroma Vector Search
      │
      ▼
Relevant Chunks Retrieved
      │
      ▼
Prompt Construction
      │
      ▼
Llama 3.2 (Ollama)
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

1. Create evaluation dataset
2. Generate RAG answers
3. Compare against ground truth
4. Run RAGAS metrics
5. Analyze traces using LangSmith

---

## 🎯 Learning Outcomes

This project helped me understand:

- Vector Databases
- Embeddings
- Semantic Search
- Chunking Strategies
- Retrieval Techniques
- RAG Evaluation
- LangSmith Observability
- Local LLM Deployment

---

## 🔮 Future Improvements

- ✅ LangSmith Integration
- ⏳ Cross Encoder Re-Ranking
- ⏳ Hybrid Search (BM25 + Vector Search)
- ⏳ Parent Document Retriever
- ⏳ Query Expansion
- ⏳ Advanced Evaluation Dashboard

---

## 👨‍💻 Author

Vignesh Krishna

MBA Business Analytics | Data Science & AI Enthusiast
