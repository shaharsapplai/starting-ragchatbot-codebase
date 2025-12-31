"""
Shared pytest fixtures for RAG chatbot tests.

Uses real ChromaDB and embeddings with existing course documents.
Only mocks the Anthropic API to avoid costs/rate limits.
"""

import os
import shutil
import sys
from dataclasses import dataclass
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock

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
def outline_tool(loaded_vector_store):
    """Create CourseOutlineTool with loaded VectorStore"""
    return CourseOutlineTool(loaded_vector_store)


@pytest.fixture
def tool_manager(search_tool, outline_tool):
    """Create ToolManager with registered tools"""
    manager = ToolManager()
    manager.register_tool(search_tool)
    manager.register_tool(outline_tool)
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
