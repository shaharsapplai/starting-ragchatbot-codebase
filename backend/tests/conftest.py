"""
Shared pytest fixtures for RAG chatbot tests.

Uses real ChromaDB and embeddings with existing course documents.
Only mocks the Anthropic API to avoid costs/rate limits.

Includes fixtures for:
- Unit tests (VectorStore, DocumentProcessor, etc.)
- Integration tests (RAGSystem with mocked AI)
- API tests (FastAPI test client with mocked dependencies)
"""

import os
import shutil
import sys
from dataclasses import dataclass
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_generator import AIGenerator
from document_processor import DocumentProcessor
from models import Course, CourseChunk, Lesson
from search_tools import CourseOutlineTool, CourseSearchTool, ToolManager
from vector_store import SearchResults, VectorStore

# Test configuration
TEST_CHROMA_PATH = os.path.join(os.path.dirname(__file__), "test_chroma_db")
DOCS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs"
)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
MAX_RESULTS = 5


@dataclass
class TestConfig:
    """Test configuration matching the real config structure"""

    ANTHROPIC_API_KEY: str = "test-api-key"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    EMBEDDING_MODEL: str = EMBEDDING_MODEL
    CHUNK_SIZE: int = CHUNK_SIZE
    CHUNK_OVERLAP: int = CHUNK_OVERLAP
    MAX_RESULTS: int = MAX_RESULTS
    MAX_HISTORY: int = 2
    CHROMA_PATH: str = TEST_CHROMA_PATH


@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration"""
    return TestConfig()


@pytest.fixture(scope="session")
def loaded_vector_store(test_config):
    """
    Create a VectorStore with real ChromaDB and load documents.
    Session-scoped to avoid reloading documents for each test.
    """
    # Clean up any existing test database
    if os.path.exists(TEST_CHROMA_PATH):
        shutil.rmtree(TEST_CHROMA_PATH)

    # Create vector store
    store = VectorStore(
        chroma_path=TEST_CHROMA_PATH,
        embedding_model=EMBEDDING_MODEL,
        max_results=MAX_RESULTS,
    )

    # Process and load documents
    processor = DocumentProcessor(CHUNK_SIZE, CHUNK_OVERLAP)

    if os.path.exists(DOCS_PATH):
        for filename in os.listdir(DOCS_PATH):
            if filename.endswith(".txt"):
                filepath = os.path.join(DOCS_PATH, filename)
                try:
                    course, chunks = processor.process_course_document(filepath)
                    if course:
                        store.add_course_metadata(course)
                        store.add_course_content(chunks)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")

    yield store

    # Cleanup after all tests
    if os.path.exists(TEST_CHROMA_PATH):
        shutil.rmtree(TEST_CHROMA_PATH)


@pytest.fixture
def search_tool(loaded_vector_store):
    """Create CourseSearchTool with loaded VectorStore"""
    return CourseSearchTool(loaded_vector_store)


@pytest.fixture
def tool_manager(search_tool):
    """Create ToolManager with registered tools"""
    manager = ToolManager()
    manager.register_tool(search_tool)
    return manager


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client"""
    return Mock()


def create_mock_text_response(text: str):
    """Helper to create a mock text-only response"""
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"

    text_block = Mock()
    text_block.type = "text"
    text_block.text = text

    mock_response.content = [text_block]
    return mock_response


def create_mock_tool_use_response(
    tool_name: str, tool_input: Dict[str, Any], tool_id: str = "tool_123"
):
    """Helper to create a mock tool_use response"""
    mock_response = Mock()
    mock_response.stop_reason = "tool_use"

    tool_block = Mock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.input = tool_input
    tool_block.id = tool_id

    mock_response.content = [tool_block]
    return mock_response


@pytest.fixture
def mock_text_response():
    """Factory fixture for creating mock text responses"""
    return create_mock_text_response


@pytest.fixture
def mock_tool_use_response():
    """Factory fixture for creating mock tool_use responses"""
    return create_mock_tool_use_response


@pytest.fixture
def mock_ai_generator(mock_anthropic_client, test_config):
    """Create AIGenerator with mocked client"""
    generator = AIGenerator(
        api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
    )
    generator.client = mock_anthropic_client
    return generator


# Helper to get course titles from loaded docs
@pytest.fixture(scope="session")
def loaded_course_titles(loaded_vector_store):
    """Get list of course titles loaded into the store"""
    return loaded_vector_store.get_existing_course_titles()


# =============================================================================
# API Testing Fixtures
# =============================================================================

@pytest.fixture
def mock_rag_system():
    """
    Create a fully mocked RAGSystem for API tests.
    Avoids loading real documents or making AI calls.
    """
    mock_rag = Mock()
    mock_rag.query.return_value = ("This is a test response.", [])
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Test Course 1", "Test Course 2"]
    }
    mock_rag.session_manager = Mock()
    mock_rag.session_manager.create_session.return_value = "test-session-id"
    return mock_rag


@pytest.fixture
def test_app(mock_rag_system):
    """
    Create a test FastAPI app with mocked RAGSystem.

    This creates a minimal app matching the production endpoints
    without mounting static files (which don't exist in test env).
    """
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional

    # Create test app without static files
    app = FastAPI(title="Test RAG API")

    # Pydantic models matching production
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[str]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # Inject mocked RAGSystem
    rag_system = mock_rag_system

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()

            answer, sources = rag_system.query(request.query, session_id)

            # Convert source dicts to strings for response
            source_strings = []
            for src in sources:
                if isinstance(src, dict):
                    source_strings.append(src.get("text", str(src)))
                else:
                    source_strings.append(str(src))

            return QueryResponse(
                answer=answer,
                sources=source_strings,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        return {"status": "ok", "message": "RAG API is running"}

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


@pytest.fixture
def test_client(test_app):
    """
    Create an async test client for the test app.
    Uses httpx.AsyncClient with ASGITransport.
    """
    from httpx import AsyncClient, ASGITransport

    transport = ASGITransport(app=test_app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def sample_query_request():
    """Sample query request data for API tests"""
    return {
        "query": "What is machine learning?",
        "session_id": None
    }


@pytest.fixture
def sample_query_request_with_session():
    """Sample query request with existing session"""
    return {
        "query": "Tell me more about neural networks",
        "session_id": "existing-session-123"
    }


@pytest.fixture
def mock_rag_with_sources():
    """RAGSystem mock that returns sources"""
    mock_rag = Mock()
    mock_rag.query.return_value = (
        "Machine learning is a subset of AI.",
        [
            {"text": "Course: ML Basics - Lesson 1", "link": "http://example.com/ml"},
            {"text": "Course: AI Fundamentals - Lesson 3", "link": "http://example.com/ai"}
        ]
    )
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 3,
        "course_titles": ["ML Basics", "AI Fundamentals", "Deep Learning"]
    }
    mock_rag.session_manager = Mock()
    mock_rag.session_manager.create_session.return_value = "new-session-456"
    return mock_rag


@pytest.fixture
def mock_rag_error():
    """RAGSystem mock that raises errors"""
    mock_rag = Mock()
    mock_rag.query.side_effect = Exception("Database connection failed")
    mock_rag.get_course_analytics.side_effect = Exception("Analytics unavailable")
    mock_rag.session_manager = Mock()
    return mock_rag


@pytest.fixture
def test_app_with_sources(mock_rag_with_sources):
    """Test app with RAGSystem that returns sources"""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional

    app = FastAPI(title="Test RAG API")

    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[str]
        session_id: str

    rag_system = mock_rag_with_sources

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()

            answer, sources = rag_system.query(request.query, session_id)

            source_strings = []
            for src in sources:
                if isinstance(src, dict):
                    source_strings.append(src.get("text", str(src)))
                else:
                    source_strings.append(str(src))

            return QueryResponse(
                answer=answer,
                sources=source_strings,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


@pytest.fixture
def test_app_with_errors(mock_rag_error):
    """Test app with RAGSystem that raises errors"""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional

    app = FastAPI(title="Test RAG API")

    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[str]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    rag_system = mock_rag_error

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id or "default"
            answer, sources = rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


@pytest.fixture
def client_with_sources(test_app_with_sources):
    """Test client for app with sources"""
    from httpx import AsyncClient, ASGITransport

    transport = ASGITransport(app=test_app_with_sources)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def client_with_errors(test_app_with_errors):
    """Test client for app with errors"""
    from httpx import AsyncClient, ASGITransport

    transport = ASGITransport(app=test_app_with_errors)
    return AsyncClient(transport=transport, base_url="http://test")
