# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A RAG (Retrieval-Augmented Generation) chatbot for querying course materials. Users ask questions via a web interface, and the system retrieves relevant content from a vector database before generating AI-powered answers with source citations.

## Commands

```bash
# Install dependencies
uv sync

# Run the application (starts FastAPI server at localhost:8000)
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

## Environment Setup

Requires a `.env` file in the root directory:
```
ANTHROPIC_API_KEY=your_key_here
```

## Architecture

### Data Flow
1. **Ingestion**: Course text files (`docs/`) → `document_processor.py` parses and chunks → `vector_store.py` stores in ChromaDB with embeddings
2. **Query**: User question → `app.py` → `rag_system.py` → Claude decides to search via tools → `search_tools.py` queries ChromaDB → Claude generates response with sources

### Key Components

- **`rag_system.py`**: Central orchestrator connecting document processing, vector storage, and AI generation
- **`vector_store.py`**: ChromaDB wrapper with two collections: `course_catalog` (metadata) and `course_content` (chunks)
- **`ai_generator.py`**: Claude API integration with tool-calling loop - Claude decides when to search course materials vs answer from knowledge
- **`search_tools.py`**: Tool definitions for Claude; `CourseSearchTool` handles semantic search with optional course/lesson filters
- **`session_manager.py`**: Maintains per-user conversation history (default: 2 message exchanges)

### Course Document Format
```
Course Title: [title]
Course Link: [url]
Course Instructor: [instructor]

Lesson 0: [title]
Lesson Link: [url]
[content...]

Lesson 1: [title]
[content...]
```

### Configuration (`backend/config.py`)
- Model: `claude-sonnet-4-20250514`
- Embeddings: `all-MiniLM-L6-v2`
- Chunk size: 800 chars with 100 char overlap
- ChromaDB path: `./chroma_db`
