# Basic RAG Proof of Concept

## Overview

This project is a simple **Retrieval-Augmented Generation (RAG)** proof of concept.

The goal is to allow a user to ask questions about a collection of documents and receive answers based on information retrieved from those documents.

Instead of relying only on the LLM's existing knowledge, the system searches the provided documents for relevant information and adds that information to the model's context before generating a response.

## Basic Architecture

```text
Documents
   ↓
Text Extraction
   ↓
Chunking
   ↓
Embeddings
   ↓
Vector Database

User Question
   ↓
Question Embedding
   ↓
Vector Search
   ↓
Relevant Chunks
   ↓
LLM Context
   ↓
Generated Answer
```

## How It Works

### 1. Document Ingestion

Documents such as PDFs or text files are loaded into the application.

The text is extracted and divided into smaller sections called **chunks**.

Example:

```text
Document
   ↓
Chunk 1
Chunk 2
Chunk 3
Chunk 4
```

Chunking makes it easier to retrieve only the information relevant to a user's question.

### 2. Embeddings

Each chunk is converted into an **embedding**.

An embedding is a numerical representation of the meaning of the text.

Text with similar meanings will generally have embeddings that are close together mathematically.

### 3. Vector Storage

The embeddings are stored inside a **vector database** along with information such as:

* Original text
* Document name
* Page number
* Chunk ID

This allows the system to quickly search for chunks that are semantically similar to a user's question.

### 4. User Query

When the user asks a question, the question is also converted into an embedding.

For example:

```text
"What is the company's vacation policy?"
```

becomes a query embedding.

### 5. Retrieval

The query embedding is compared with the stored document embeddings.

The system retrieves the most similar chunks.

For example:

```text
Top 3 Retrieved Chunks

1. Vacation Policy - Page 4
2. Employee Benefits - Page 7
3. Time Off Policy - Page 2
```

### 6. Context Construction

The retrieved chunks are added to the LLM's context.

A simplified prompt may look like:

```text
You are an assistant answering questions using the provided context.

Context:
Employees receive 15 paid vacation days each year.

Question:
How many vacation days do employees receive?

Answer:
```

### 7. Response Generation

The LLM generates an answer using the retrieved information.

Example:

```text
Employees receive 15 paid vacation days each year.
```

The system can also return the document or page where the information was retrieved.

---

## Initial POC Scope

The first version of this project will focus on a basic RAG implementation.

The POC will support:

* Loading documents
* Extracting document text
* Splitting text into chunks
* Creating embeddings
* Storing embeddings in a vector database
* Accepting user questions
* Performing semantic similarity search
* Retrieving relevant document chunks
* Providing retrieved context to an LLM
* Generating answers based on retrieved information
* Returning document sources where possible

More advanced RAG techniques can be added after the basic system is working.

---

## Possible Technology Stack

The initial implementation may use:

* **Python** — main application language
* **PyMuPDF** — PDF text extraction
* **Sentence Transformers or OpenAI Embeddings** — embedding generation
* **ChromaDB or FAISS** — vector storage and similarity search
* **OpenAI / Gemini / Claude / Local LLM** — response generation
* **Streamlit** — optional simple user interface

The exact technologies may change during development.

---

## Project Structure

A possible project structure:

```text
rag-poc/
│
├── documents/
│   ├── document1.pdf
│   └── document2.pdf
│
├── src/
│   ├── ingest.py
│   ├── chunk.py
│   ├── embeddings.py
│   ├── retrieval.py
│   └── rag.py
│
├── app.py
├── requirements.txt
└── README.md
```

### `ingest.py`

Loads documents and extracts their text.

### `chunk.py`

Splits extracted text into smaller chunks.

### `embeddings.py`

Creates embeddings for document chunks.

### `retrieval.py`

Searches the vector database for chunks relevant to the user's question.

### `rag.py`

Combines the retrieved context with the user question and sends it to the LLM.

### `app.py`

Provides the main entry point or user interface for the application.

---

## Example

A user may ask:

```text
What authentication methods are supported?
```

The application will:

```text
1. Convert the question into an embedding
2. Search the vector database
3. Retrieve the most relevant chunks
4. Add those chunks to the LLM context
5. Ask the LLM to answer the question
6. Return the answer and relevant source
```

Example response:

```text
The system supports OAuth 2.0 and multi-factor authentication.

Source:
security_policy.pdf - Page 12
```

---

## Future Improvements

After the basic RAG system is working, possible improvements include:

* Hybrid search using keyword search and vector search
* Reranking retrieved documents
* Query rewriting
* Multi-query retrieval
* Metadata filtering
* Conversational RAG
* Better chunking strategies
* Context compression
* Evaluation of retrieval quality
* Guardrails and output validation
* Agentic RAG
* Graph RAG

---

## Purpose

The purpose of this POC is not to create a production-ready RAG platform.

The goal is to demonstrate and understand the core RAG pipeline:

```text
Retrieve relevant information
        ↓
Add it to the model's context
        ↓
Generate a grounded response
```

Once this basic pipeline is working and understood, more advanced retrieval and reasoning techniques can be introduced.
