# 🚀 RAG01 - Hybrid RAG System

A modular Retrieval-Augmented Generation (RAG) system built to understand and implement the architecture of a production-oriented hybrid RAG application.

The project progressively evolves from a Basic RAG pipeline into a Dynamic RAG application using dense retrieval, sparse retrieval, hybrid ranking, Cross-Encoder re-ranking, LLM generation, evaluation, observability, and API-based document ingestion.

---

## 🎯 Project Objective

The goal of this project is not simply to build a chatbot.

The objective is to understand the engineering architecture behind a modern RAG system and how individual components work together as a maintainable AI application.

The project currently covers:

- Document ingestion
- Local document storage
- PDF processing
- Recursive text chunking
- Metadata preservation
- Stable document and chunk identifiers
- Dense semantic retrieval
- ChromaDB vector storage
- Sparse lexical retrieval using OpenSearch BM25
- Hybrid retrieval using Reciprocal Rank Fusion (RRF)
- Cross-Encoder re-ranking
- Context construction
- NVIDIA Nemotron generation
- RAG evaluation
- LangSmith observability
- Dockerized OpenSearch infrastructure

The next phase is to transform the current working RAG pipeline into a dynamic API-based RAG application where users can upload documents and query them dynamically.

---

# 🏗️ Current Architecture

```text
                         USER QUESTION
                                │
                                ▼
                           chatbot.py
                         Query Orchestrator
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
                 ▼                             ▼
          Dense Retrieval                Sparse Retrieval
            ChromaDB                       OpenSearch
              Top 20                         BM25 Top 20
                 │                             │
                 └──────────────┬──────────────┘
                                │
                                ▼
                   Reciprocal Rank Fusion
                                │
                                ▼
                         Hybrid Ranking
                                │
                                ▼
                      Top 5 Candidates
                                │
                                ▼
                     Cross-Encoder Reranker
                                │
                                ▼
                         Final Top 5
                                │
                                ▼
                       Context Construction
                                │
                                ▼
                         Prompt Construction
                                │
                                ▼
                       NVIDIA Nemotron
                                │
                                ▼
                         Final Answer
                                │
                                ▼
                       Answer + Sources
```

---

# 📄 Document Ingestion Architecture

Documents are processed once into common `Chunk` objects.

The same chunks are then indexed into both retrieval systems.

```text
                       PDF Upload
                           │
                           ▼
                       ingest.py
                           │
                           ▼
                    Document Storage
                           │
                           ▼
                    Document Processing
                           │
                           ▼
                        Chunking
                           │
                           ▼
                     Chunk Objects
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
          ChromaDB                  OpenSearch
        Dense Index                BM25 Index
```

The important architectural principle is that the application creates the chunk identity once.

The same `chunk_id` is used across:

- Chunk objects
- ChromaDB
- OpenSearch
- RRF
- Cross-Encoder results
- Source traceability

This prevents the dense and sparse retrieval systems from treating the same logical chunk as two different documents.

---

# 🛠️ Tech Stack

## Core Technologies

- Python
- LangChain
- ChromaDB
- OpenSearch
- Docker
- HuggingFace Embeddings
- Sentence Transformers
- Reciprocal Rank Fusion
- Cross-Encoder Re-Ranking
- NVIDIA Nemotron
- FastAPI (next phase)

## Embedding Model

```text
sentence-transformers/all-MiniLM-L6-v2
```

Used for dense semantic retrieval through ChromaDB.

## Sparse Retrieval

```text
OpenSearch BM25
```

OpenSearch provides persistent inverted-index based lexical retrieval.

BM25 is useful for:

- Exact terminology
- Policy names
- Keywords
- Numbers
- Names
- Phrase-heavy queries

## Re-Ranker

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

The Cross-Encoder evaluates the relationship between the user question and each retrieved candidate.

## LLM

NVIDIA hosted inference using:

```text
nvidia/nemotron-3.5-lightning-30b-a3b
```

Current generation configuration uses a concise output limit suitable for the chatbot.

---

# ✨ Features

## 📄 Document Processing

The current system processes PDF documents using:

- PDF loading
- Recursive Character Text Splitting
- Chunk size of 750 characters
- Chunk overlap of 150 characters
- Custom `Chunk` objects
- Metadata preservation
- Document and chunk identifiers

Current NovaTech HR Policy Handbook processing:

```text
PDF
 ↓
PyPDFLoader
 ↓
Recursive Character Text Splitter
 ↓
41 Chunks
```

---

# 🗄️ Document Storage

Documents are stored through a storage abstraction rather than directly coupling the ingestion pipeline to a specific storage implementation.

Current implementation:

```text
LocalStorage
```

Current storage structure:

```text
storage/
└── <company_id>/
    └── <document_id>/
        └── <filename>.pdf
```

The storage layer is designed so that future object-storage implementations can be introduced without rewriting the ingestion workflow.

Potential future backends include:

- MinIO
- Azure Blob Storage
- Amazon S3

---

# 🔎 Retrieval Architecture

The system uses two complementary retrieval strategies.

## 1. Dense Retrieval

Dense retrieval uses:

```text
HuggingFace Embeddings
        ↓
ChromaDB
        ↓
MMR Retrieval
        ↓
Top 20
```

Dense retrieval is useful for understanding semantic similarity between the query and document content.

For example, a semantic query may retrieve relevant content even when the exact query words do not appear in the document.

---

## 2. Sparse Retrieval - OpenSearch BM25

Sparse retrieval uses:

```text
User Question
      ↓
OpenSearch
      ↓
Inverted Index
      ↓
BM25 Scoring
      ↓
Top 20
```

OpenSearch handles:

- Text analysis
- Inverted-index creation
- Term matching
- BM25 scoring
- Result ranking

The application does not manually implement BM25 or persist tokenized corpora.

This gives the project a more realistic search-engine architecture.

---

# ⚖️ Hybrid Search with RRF

Dense retrieval and BM25 produce different types of relevance scores.

Their raw scores should therefore not simply be added together.

For example:

```text
Dense score  ≠  BM25 score
```

Instead, Reciprocal Rank Fusion combines the ranked lists.

```text
                 Dense Top 20
                      │
                      │
                      ▼
                ┌───────────┐
                │    RRF    │
                └─────┬─────┘
                      ▲
                      │
                      │
                 BM25 Top 20
                      │
                      ▼
               Hybrid Ranking
```

RRF rewards chunks that appear highly in multiple retrieval systems.

The current implementation uses `chunk_id` as the identity key.

This allows the same logical chunk to accumulate relevance contributions from both retrieval methods.

---

# 🎯 Cross-Encoder Re-Ranking

The hybrid candidates produced by RRF are passed to a Cross-Encoder.

The Cross-Encoder evaluates:

```text
Question + Candidate Chunk
```

rather than independently embedding the two pieces of text.

Current pipeline:

```text
Dense Top 20
      +
BM25 Top 20
      ↓
     RRF
      ↓
 Top 5 Candidates
      ↓
Cross-Encoder
      ↓
 Final Top 5
```

The Cross-Encoder is intentionally placed after first-stage retrieval because it is more computationally expensive than Dense or BM25 retrieval.

This allows the system to use a stronger relevance model only on a small candidate set.

---

# 🤖 Generation

The final five re-ranked chunks are passed to NVIDIA Nemotron.

```text
Final Top 5 Chunks
        ↓
Context Construction
        ↓
Prompt
        ↓
NVIDIA Nemotron
        ↓
Final Answer
```

The chatbot returns:

```text
Answer
+
Source Chunks
```

Returning the source chunks makes it possible for a future API or frontend to display source information such as:

- Chunk ID
- Document ID
- Page
- Source document

---

# 🧠 Chatbot Orchestration

`src/chatbot.py` acts as the central query orchestrator.

Its responsibility is to connect the existing components without tightly coupling the chatbot to the underlying technologies.

```text
User Question
      ↓
Dense Retrieval
      ↓
BM25 Retrieval
      ↓
RRF
      ↓
Top 5
      ↓
Cross-Encoder
      ↓
Context Construction
      ↓
Nemotron
      ↓
Answer + Sources
```

The chatbot does not implement:

- Embedding generation
- BM25
- RRF
- Cross-Encoder scoring
- LLM configuration

Those responsibilities remain inside their respective modules.

---

# 📊 Evaluation

The project includes a RAG evaluation workflow using a ground-truth dataset and RAGAS.

The evaluation concept is:

```text
Ground Truth Dataset
        ↓
RAG Pipeline
        ↓
Generated Answers
        ↓
RAGAS
        ↓
Retrieval / Generation Analysis
        ↓
Pipeline Improvement
```

Evaluation is treated as an engineering feedback loop rather than simply checking whether the chatbot produces an answer.

The evaluation workflow is kept separate from the production chatbot orchestration.

---

# 🔍 Observability

LangSmith is used to inspect and debug the RAG pipeline.

Observability helps investigate:

- Retrieval behavior
- Retrieved documents
- Re-ranking
- LLM calls
- Pipeline execution
- Latency
- Retrieval failures
- RAG pipeline behavior

The objective is to understand not only:

> "What answer did the system produce?"

but also:

> "Why did the system produce this answer?"

---

# 🧪 Experiments

The project contains focused experiments for understanding individual components.

Current experiments include:

```text
experiments/
├── compare_sparse_dense_score.py
├── test_bm25_scores.py
├── test_chatbot.py
├── test_reranker.py
└── test_rrf.py
```

These experiments are used to validate:

- Dense retrieval
- BM25 retrieval
- Dense vs BM25 overlap
- BM25 relevance scores
- RRF behavior
- Cross-Encoder re-ranking
- End-to-end chatbot generation

The experiments are intentionally kept separate from the main application code.

---

# 📁 Project Structure

```text
RAG01_BASIC_RAG/
│
├── data/
│   └── NovaTech_HR_Policy_Handbook.pdf
│
├── evaluation/
│   └── eval_dataset.csv
│
├── experiments/
│   ├── compare_sparse_dense_score.py
│   ├── test_bm25_scores.py
│   ├── test_chatbot.py
│   ├── test_reranker.py
│   └── test_rrf.py
│
├── src/
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── document.py
│   │   └── chunk.py
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   └── storage.py
│   │
│   ├── processing/
│   │   └── document_processor.py
│   │
│   ├── indexing/
│   │   ├── chroma.py
│   │   └── bm25_index.py
│   │
│   ├── retrieval/
│   │   ├── bm25.py
│   │   ├── retrieve.py
│   │   ├── rrf.py
│   │   └── reranker.py
│   │
│   ├── generation/
│   │   └── llm.py
│   │
│   ├── ingest.py
│   └── chatbot.py
│
├── vector_store/
│   └── Local ChromaDB data
│
├── docker-compose.yml
├── mapping.json
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

> Local runtime data such as `storage/`, `test_storage/`, `vector_store/`, `venv/`, and `.env` is intentionally excluded from Git.

---

# 🐳 OpenSearch Infrastructure

OpenSearch runs locally using Docker.

Current services:

```text
Docker Compose
      │
      ├── OpenSearch
      │      └── localhost:9200
      │
      └── OpenSearch Dashboards
             └── localhost:5601
```

## OpenSearch API

```text
http://localhost:9200
```

The Python application communicates with OpenSearch through `opensearch-py`.

## OpenSearch Dashboards

```text
http://localhost:5601
```

Dashboards is used for inspecting the OpenSearch index and documents.

It is a development and observability interface and is not required by the chatbot runtime.

## RAG Index

The current index is:

```text
rag_chunks
```

The mapping contains fields including:

```text
chunk_id
document_id
company_id
chunk_text
chunk_index
page
source
```

The important field types are:

```text
chunk_id       → keyword
document_id    → keyword
company_id     → keyword
chunk_text     → text
chunk_index    → integer
page           → integer
source         → keyword
```

This allows OpenSearch to use full-text search on `chunk_text` while preserving exact identifiers and metadata.

---

# 🚀 Getting Started

## 1. Clone Repository

```bash
git clone <your-repository-url>
cd RAG01_BASIC_RAG
```

---

## 2. Create Virtual Environment

```bash
python -m venv venv
```

---

## 3. Activate Environment

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

---

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 5. Configure Environment Variables

Create a `.env` file based on:

```text
.env.example
```

Configure the required NVIDIA and OpenSearch environment variables.

Never commit API keys, passwords, or other secrets to GitHub.

---

# 🐳 Start OpenSearch

Start the local OpenSearch infrastructure:

```bash
docker compose up -d
```

Verify that the containers are running:

```bash
docker ps
```

OpenSearch should be available on:

```text
https://localhost:9200
```

OpenSearch Dashboards should be available on:

```text
http://localhost:5601
```

---

# 📄 Ingest a Document

The ingestion pipeline processes a document and indexes the same chunks into both retrieval systems.

Conceptually:

```text
PDF
 ↓
LocalStorage
 ↓
PDF Processing
 ↓
Chunk Objects
 ├──→ ChromaDB
 └──→ OpenSearch
```

The ingestion service creates the `Chunk` objects once and uses the same `chunk_id` for both indexes.

---

# 💬 Test the RAG Chatbot

The end-to-end chatbot can currently be tested using:

```bash
python experiments/test_chatbot.py
```

The test executes:

```text
Question
   ↓
Dense Retrieval
   ↓
BM25 Retrieval
   ↓
RRF
   ↓
Top 5
   ↓
Cross-Encoder
   ↓
Context
   ↓
NVIDIA Nemotron
   ↓
Answer + Sources
```

---

# 🧪 Example Questions

The current NovaTech HR Policy Handbook can be queried with questions such as:

```text
What is the annual leave policy?
```

```text
How many days of Privilege Leave can employees carry forward?
```

```text
What is the maternity leave entitlement?
```

```text
How far in advance should planned leave be applied for?
```

---

# 🔮 Next Phase — Dynamic RAG Application

The current hybrid RAG pipeline is functional, but document ingestion is still primarily driven through the local application workflow.

The next major step is to make the system dynamic through FastAPI.

The target architecture is:

```text
                         USER
                       /      \
                      /        \
             Upload Document   Ask Question
                    │              │
                    ▼              ▼
                 FastAPI       chatbot.py
                    │              │
                    ▼              ▼
                ingest.py       Retrieval
                    │              │
                    ▼              ▼
             Document Storage      RRF
                    │              │
                    ▼              ▼
              Document Processing  Reranker
                    │              │
                    ▼              ▼
                  Chunks           LLM
                 /     \
                /       \
               ▼         ▼
          ChromaDB    OpenSearch
           Dense        BM25
```

The query pipeline will remain:

```text
User Question
      │
      ├───────────────┐
      ▼               ▼
Dense Retrieval   BM25 Retrieval
      │               │
      └───────┬───────┘
              ▼
             RRF
              │
              ▼
        Cross-Encoder
              │
              ▼
            Top 5
              │
              ▼
          Nemotron
              │
              ▼
            Answer
```

---

# 🌐 Planned API Architecture

The dynamic application is expected to expose endpoints such as:

```text
POST   /documents
POST   /query
GET    /documents
DELETE /documents/{document_id}
```

The exact API contract will be finalized during implementation.

The intended architecture is:

```text
                    FastAPI
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
        Ingestion Service   Query Service
             │                   │
             ▼                   ▼
       Storage + Indexing    Hybrid Retrieval
                                 │
                                 ▼
                                RRF
                                 │
                                 ▼
                             Reranker
                                 │
                                 ▼
                                LLM
```

---

# 🆔 Document & Chunk Identity

The system uses separate document and chunk identities.

```text
Document
   │
   ├── document_id
   ├── company_id
   ├── filename
   ├── version
   └── metadata
          │
          ▼
        Chunks
          │
          ├── chunk_id
          ├── document_id
          ├── company_id
          ├── chunk_index
          ├── page
          ├── source
          └── chunk_text
```

Chunk identity is important for:

- Dense retrieval
- Sparse retrieval
- RRF
- Re-ranking
- Source traceability
- Document deletion
- Document updates
- Metadata filtering
- Multi-document retrieval
- Future multi-tenant architectures

---

# 🏛️ Architectural Principles

This project follows several engineering principles.

## 1. Separation of Responsibilities

Each component has a focused responsibility.

```text
Storage       → Store documents
Processing    → Load and chunk documents
Chroma        → Dense indexing/retrieval
OpenSearch    → Sparse indexing/retrieval
RRF           → Combine rankings
Reranker      → Improve relevance
LLM           → Generate answer
Chatbot       → Orchestrate query flow
FastAPI       → Expose application through API
```

---

## 2. Retrieval Backend Independence

The application should not become tightly coupled to OpenSearch.

OpenSearch currently provides BM25 retrieval, but the retrieval boundary should allow future replacement with systems such as:

- Elasticsearch
- Azure AI Search
- Other enterprise search platforms

The objective is to learn the architectural boundary rather than build an application that depends on one search engine.

---

## 3. One Chunk, One Identity

The same `Chunk` object is used as the source of truth before indexing into:

```text
ChromaDB
+
OpenSearch
```

This ensures both retrieval systems operate on the same logical chunk identity.

---

## 4. Local-First Development

The current system uses local infrastructure for development:

```text
ChromaDB
OpenSearch
Docker
LocalStorage
```

This allows the architecture to be developed and tested without unnecessarily consuming cloud resources.

Cloud services can be introduced deliberately when their enterprise-specific capabilities become relevant.

---

# 🛡️ Future Production Hardening

Once the dynamic RAG application is functional, the system will progressively be hardened.

## Retrieval

- Retrieval evaluation
- Metadata filtering
- Stable chunk lifecycle
- Retrieval failure handling
- Retrieval regression testing
- Hybrid retrieval optimization

## API

- Request validation
- Error handling
- Logging
- Health checks
- Authentication
- Rate limiting

## Storage

- Document lifecycle management
- Object-storage compatibility
- Versioning
- Retention policies

## RAG Reliability

- Groundedness checks
- Hallucination detection
- Guardrails
- Query validation
- Failure handling
- Empty retrieval handling

## Evaluation

- Automated evaluation
- Retrieval metrics
- Answer quality metrics
- Regression testing
- Evaluation dashboards

## Infrastructure

- Docker
- Configuration management
- Observability
- Performance monitoring
- Scalable deployment
- Secure TLS configuration

---

# 🎯 Learning Outcomes

Through this project, I am developing practical understanding of:

## RAG Engineering

- PDF ingestion
- Document processing
- Text chunking
- Embeddings
- Vector databases
- Semantic retrieval
- Sparse retrieval
- BM25
- OpenSearch
- Hybrid retrieval
- Reciprocal Rank Fusion
- Cross-Encoder re-ranking
- Prompt construction
- Context-grounded generation

## AI Engineering

- RAG pipeline design
- Modular architecture
- Retrieval optimization
- Evaluation-driven development
- Observability
- Model integration
- Retrieval debugging
- Component trade-offs
- End-to-end AI application design

## Enterprise AI Architecture

The project is progressively moving toward:

```text
Dynamic Ingestion
       ↓
Storage Abstraction
       ↓
Document Processing
       ↓
Index Management
       ↓
Hybrid Retrieval
       ↓
Re-Ranking
       ↓
Generation
       ↓
Evaluation
       ↓
Observability
       ↓
API
       ↓
Production Hardening
```

The goal is to understand how individual RAG components work together as a maintainable AI system rather than treating RAG as a single framework feature.

---

# 🗺️ Project Roadmap

```text
✅ Phase 1 — Basic RAG

   ├── PDF ingestion
   ├── Chunking
   ├── Embeddings
   ├── ChromaDB
   └── LLM generation


✅ Phase 2 — Retrieval Improvement

   ├── Dense retrieval
   ├── BM25
   ├── OpenSearch
   ├── Hybrid Search
   ├── RRF
   └── Cross-Encoder


✅ Phase 3 — Evaluation & Observability

   ├── Ground Truth Dataset
   ├── RAGAS
   └── LangSmith


🚧 Phase 4 — Dynamic RAG Application

   ├── Storage abstraction
   ├── Dynamic document ingestion
   ├── Document and chunk identity
   ├── Dynamic BM25 indexing
   ├── Dynamic vector indexing
   ├── Chatbot orchestration
   └── FastAPI


⏳ Phase 5 — Production Hardening

   ├── Error handling
   ├── Validation
   ├── Authentication
   ├── Logging
   ├── Monitoring
   ├── Evaluation automation
   └── Performance optimization


⏳ Phase 6 — Advanced RAG

   ├── Query expansion
   ├── Parent Document Retrieval
   ├── Advanced retrieval strategies
   ├── Guardrails
   └── Agentic RAG
```

---

# 👨‍💻 Author

**Vignesh Krishna**

MBA Business Analytics

Data Science & AI

Aspiring AI Engineer

---

# 📌 Project Philosophy

> Build the fundamentals first.

> Understand why each component exists.

> Implement it.

> Measure it.

> Debug it.

> Then harden it for production.

This project is intentionally developed incrementally so that every architectural component is understood before adding the next layer.