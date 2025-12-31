"""
Tests for RAGSystem query flow.

Integration tests using real VectorStore with mocked Anthropic API.
"""

import os
import sys
from dataclasses import dataclass
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_system import RAGSystem


# Helper functions (duplicated from conftest to avoid import issues)
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
    tool_name: str, tool_input: dict, tool_id: str = "tool_123"
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


class TestRAGSystemInitialization:
    """Test RAGSystem initialization and component setup"""

    def test_tool_manager_has_search_tool_registered(self, test_config):
        """RAGSystem registers CourseSearchTool"""
        with patch("rag_system.AIGenerator"):
            rag = RAGSystem(test_config)
            assert "search_course_content" in rag.tool_manager.tools

    def test_tool_manager_has_outline_tool_registered(self, test_config):
        """RAGSystem registers CourseOutlineTool"""
        with patch("rag_system.AIGenerator"):
            rag = RAGSystem(test_config)
            assert "get_course_outline" in rag.tool_manager.tools

    def test_session_manager_initialized(self, test_config):
        """RAGSystem initializes SessionManager"""
        with patch("rag_system.AIGenerator"):
            rag = RAGSystem(test_config)
            assert rag.session_manager is not None


class TestRAGSystemQuery:
    """Test RAGSystem.query() method"""

    @pytest.fixture
    def rag_system_with_mocked_ai(self, test_config, loaded_vector_store):
        """Create RAGSystem with real VectorStore but mocked AI"""
        with patch("rag_system.AIGenerator") as MockAI:
            mock_generator = Mock()
            MockAI.return_value = mock_generator

            rag = RAGSystem(test_config)
            # Replace vector store with loaded one
            rag.vector_store = loaded_vector_store
            rag.search_tool.store = loaded_vector_store
            rag.outline_tool.store = loaded_vector_store

            yield rag, mock_generator

    def test_query_returns_response_tuple(self, rag_system_with_mocked_ai):
        """query() returns (response, sources) tuple"""
        rag, mock_generator = rag_system_with_mocked_ai
        mock_generator.generate_response.return_value = "Test response"

        result = rag.query("Test question")

        assert isinstance(result, tuple)
        assert len(result) == 2
        response, sources = result
        assert isinstance(response, str)
        assert isinstance(sources, list)

    def test_query_passes_tools_to_generator(self, rag_system_with_mocked_ai):
        """query() passes tool definitions to AI generator"""
        rag, mock_generator = rag_system_with_mocked_ai
        mock_generator.generate_response.return_value = "Response"

        rag.query("Question about courses")

        # Check that tools were passed
        call_kwargs = mock_generator.generate_response.call_args[1]
        assert "tools" in call_kwargs
        assert len(call_kwargs["tools"]) == 2  # search + outline

    def test_query_passes_tool_manager(self, rag_system_with_mocked_ai):
        """query() passes tool_manager to AI generator"""
        rag, mock_generator = rag_system_with_mocked_ai
        mock_generator.generate_response.return_value = "Response"

        rag.query("Question")

        call_kwargs = mock_generator.generate_response.call_args[1]
        assert "tool_manager" in call_kwargs
        assert call_kwargs["tool_manager"] == rag.tool_manager

    def test_query_updates_session_history(self, rag_system_with_mocked_ai):
        """query() updates session history for session_id"""
        rag, mock_generator = rag_system_with_mocked_ai
        mock_generator.generate_response.return_value = "Response"

        session_id = "test-session-123"
        rag.query("Question", session_id=session_id)

        # Session should have history
        history = rag.session_manager.get_conversation_history(session_id)
        assert history is not None
        assert "Question" in history
        assert "Response" in history

    def test_query_retrieves_sources_from_tool_manager(self, rag_system_with_mocked_ai):
        """query() retrieves sources from tool_manager after response"""
        rag, mock_generator = rag_system_with_mocked_ai
        mock_generator.generate_response.return_value = "Response with sources"

        # Simulate search tool populating sources
        rag.search_tool.last_sources = [
            {"text": "Course 1 - Lesson 1", "link": "http://example.com"}
        ]

        response, sources = rag.query("Question")

        assert len(sources) == 1
        assert sources[0]["text"] == "Course 1 - Lesson 1"

    def test_query_resets_sources_after_retrieval(self, rag_system_with_mocked_ai):
        """query() resets sources after retrieving them"""
        rag, mock_generator = rag_system_with_mocked_ai
        mock_generator.generate_response.return_value = "Response"

        rag.search_tool.last_sources = [{"text": "Source", "link": None}]

        rag.query("Question")

        # Sources should be reset
        assert len(rag.search_tool.last_sources) == 0

    def test_query_includes_conversation_history(self, rag_system_with_mocked_ai):
        """query() passes conversation history for existing session"""
        rag, mock_generator = rag_system_with_mocked_ai
        mock_generator.generate_response.return_value = "Response"

        session_id = "test-session"

        # First query
        rag.query("First question", session_id=session_id)

        # Second query should include history
        rag.query("Second question", session_id=session_id)

        # Check the second call included history
        second_call = mock_generator.generate_response.call_args_list[1]
        call_kwargs = second_call[1]
        assert call_kwargs.get("conversation_history") is not None


class TestRAGSystemWithRealFlow:
    """Test RAGSystem with real tool execution (mocked AI only)"""

    @pytest.fixture
    def rag_with_real_tools(self, test_config, loaded_vector_store):
        """RAGSystem with real tools but mocked AI client"""
        # Patch only the Anthropic client, not the whole AIGenerator
        with patch("anthropic.Anthropic") as MockClient:
            mock_client = Mock()
            MockClient.return_value = mock_client

            rag = RAGSystem(test_config)
            rag.vector_store = loaded_vector_store
            rag.search_tool.store = loaded_vector_store
            rag.outline_tool.store = loaded_vector_store

            yield rag, mock_client

    def test_full_flow_with_tool_use(self, rag_with_real_tools):
        """Full query flow with tool execution"""
        rag, mock_client = rag_with_real_tools

        # Mock API responses: first tool_use, then final response
        mock_client.messages.create.side_effect = [
            create_mock_tool_use_response(
                tool_name="search_course_content", tool_input={"query": "computer use"}
            ),
            create_mock_text_response(
                "Based on the search results, computer use is..."
            ),
        ]

        response, sources = rag.query("Tell me about computer use")

        # Should get final response
        assert "computer use" in response.lower()
        # Should have made 2 API calls
        assert mock_client.messages.create.call_count == 2

    def test_direct_response_without_tool(self, rag_with_real_tools):
        """Query that doesn't need tools returns direct response"""
        rag, mock_client = rag_with_real_tools

        mock_client.messages.create.return_value = create_mock_text_response(
            "Hello! I'm here to help with course materials."
        )

        response, sources = rag.query("Hello")

        assert "Hello" in response
        # Only one API call (no tool use)
        assert mock_client.messages.create.call_count == 1
        # No sources for greeting
        assert len(sources) == 0


class TestRAGSystemAnalytics:
    """Test RAGSystem analytics methods"""

    def test_get_course_analytics_returns_dict(self, test_config, loaded_vector_store):
        """get_course_analytics returns analytics dict"""
        with patch("rag_system.AIGenerator"):
            rag = RAGSystem(test_config)
            rag.vector_store = loaded_vector_store

            analytics = rag.get_course_analytics()

            assert isinstance(analytics, dict)
            assert "total_courses" in analytics
            assert "course_titles" in analytics

    def test_get_course_analytics_reflects_loaded_courses(
        self, test_config, loaded_vector_store
    ):
        """Analytics reflects actually loaded courses"""
        with patch("rag_system.AIGenerator"):
            rag = RAGSystem(test_config)
            rag.vector_store = loaded_vector_store

            analytics = rag.get_course_analytics()

            # Should match the loaded courses
            expected_count = len(loaded_vector_store.get_existing_course_titles())
            assert analytics["total_courses"] == expected_count
