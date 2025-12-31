"""
Tests for AIGenerator tool-calling behavior.

Uses mocked Anthropic client to test tool detection and execution flow.
"""
import pytest
from unittest.mock import Mock, patch, call


class TestAIGeneratorBasic:
    """Test basic AIGenerator functionality"""

    def test_generate_response_calls_api(self, mock_ai_generator, mock_text_response):
        """generate_response calls the Anthropic API"""
        mock_ai_generator.client.messages.create = Mock(
            return_value=mock_text_response("Hello, I can help you!")
        )

        result = mock_ai_generator.generate_response(query="Hello")

        # API should be called
        mock_ai_generator.client.messages.create.assert_called_once()

        # Result should be the response text
        assert result == "Hello, I can help you!"

    def test_generate_response_with_tools(self, mock_ai_generator, mock_text_response, tool_manager):
        """generate_response passes tools to API"""
        mock_ai_generator.client.messages.create = Mock(
            return_value=mock_text_response("Based on my knowledge...")
        )

        tools = tool_manager.get_tool_definitions()
        result = mock_ai_generator.generate_response(
            query="What is AI?",
            tools=tools
        )

        # API should be called with tools
        call_kwargs = mock_ai_generator.client.messages.create.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == tools

    def test_generate_response_with_conversation_history(self, mock_ai_generator, mock_text_response):
        """generate_response includes conversation history in system prompt"""
        mock_ai_generator.client.messages.create = Mock(
            return_value=mock_text_response("Following up on that...")
        )

        history = "User: What is AI?\nAssistant: AI is artificial intelligence."
        result = mock_ai_generator.generate_response(
            query="Tell me more",
            conversation_history=history
        )

        # System prompt should include history
        call_kwargs = mock_ai_generator.client.messages.create.call_args[1]
        assert history in call_kwargs["system"]


class TestAIGeneratorToolUse:
    """Test AIGenerator tool-use detection and handling"""

    def test_detects_tool_use_stop_reason(self, mock_ai_generator, mock_tool_use_response, mock_text_response, tool_manager):
        """Recognizes when Claude wants to use tools"""
        # First call returns tool_use, second returns text
        mock_ai_generator.client.messages.create = Mock(
            side_effect=[
                mock_tool_use_response(
                    tool_name="search_course_content",
                    tool_input={"query": "computer use"}
                ),
                mock_text_response("Here's what I found about computer use...")
            ]
        )

        result = mock_ai_generator.generate_response(
            query="Tell me about computer use",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # API should be called twice (initial + follow-up)
        assert mock_ai_generator.client.messages.create.call_count == 2

    def test_handle_tool_execution_calls_correct_tool(self, mock_ai_generator, mock_tool_use_response, mock_text_response, tool_manager):
        """Tool execution calls the correct tool with correct params"""
        tool_input = {"query": "search term", "course_name": "Test Course"}

        mock_ai_generator.client.messages.create = Mock(
            side_effect=[
                mock_tool_use_response(
                    tool_name="search_course_content",
                    tool_input=tool_input
                ),
                mock_text_response("Based on the search results...")
            ]
        )

        # Spy on tool_manager.execute_tool
        original_execute = tool_manager.execute_tool
        tool_manager.execute_tool = Mock(side_effect=original_execute)

        result = mock_ai_generator.generate_response(
            query="Search for something",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # execute_tool should be called with correct args
        tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            **tool_input
        )

    def test_tool_result_sent_in_followup_message(self, mock_ai_generator, mock_tool_use_response, mock_text_response, tool_manager):
        """Tool results are included in follow-up API call"""
        mock_ai_generator.client.messages.create = Mock(
            side_effect=[
                mock_tool_use_response(
                    tool_name="search_course_content",
                    tool_input={"query": "test"},
                    tool_id="tool_abc123"
                ),
                mock_text_response("Final response")
            ]
        )

        result = mock_ai_generator.generate_response(
            query="Test query",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Check the second API call's messages
        second_call = mock_ai_generator.client.messages.create.call_args_list[1]
        messages = second_call[1]["messages"]

        # Should have 3 messages: user, assistant (tool_use), user (tool_result)
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

        # Last message should contain tool_result
        tool_result_content = messages[2]["content"]
        assert len(tool_result_content) > 0
        assert tool_result_content[0]["type"] == "tool_result"
        assert tool_result_content[0]["tool_use_id"] == "tool_abc123"

    def test_returns_final_response_text(self, mock_ai_generator, mock_tool_use_response, mock_text_response, tool_manager):
        """After tool execution, returns the final text response"""
        expected_response = "This is the final answer based on search results."

        mock_ai_generator.client.messages.create = Mock(
            side_effect=[
                mock_tool_use_response(
                    tool_name="search_course_content",
                    tool_input={"query": "test"}
                ),
                mock_text_response(expected_response)
            ]
        )

        result = mock_ai_generator.generate_response(
            query="Test",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        assert result == expected_response

    def test_handles_multiple_tool_calls(self, mock_ai_generator, mock_text_response, tool_manager):
        """Handles multiple tool calls in a single response"""
        # Create response with two tool calls
        mock_response = Mock()
        mock_response.stop_reason = "tool_use"

        tool_block_1 = Mock()
        tool_block_1.type = "tool_use"
        tool_block_1.name = "search_course_content"
        tool_block_1.input = {"query": "topic 1"}
        tool_block_1.id = "tool_1"

        tool_block_2 = Mock()
        tool_block_2.type = "tool_use"
        tool_block_2.name = "get_course_outline"
        tool_block_2.input = {"course_name": "Test Course"}
        tool_block_2.id = "tool_2"

        mock_response.content = [tool_block_1, tool_block_2]

        mock_ai_generator.client.messages.create = Mock(
            side_effect=[
                mock_response,
                mock_text_response("Combined results from both tools...")
            ]
        )

        result = mock_ai_generator.generate_response(
            query="Complex query",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Should have two tool results in follow-up
        second_call = mock_ai_generator.client.messages.create.call_args_list[1]
        tool_results = second_call[1]["messages"][2]["content"]
        assert len(tool_results) == 2


class TestAIGeneratorAPIParams:
    """Test AIGenerator API parameter handling"""

    def test_uses_configured_model(self, mock_ai_generator, mock_text_response):
        """Uses the configured model name"""
        mock_ai_generator.client.messages.create = Mock(
            return_value=mock_text_response("Test")
        )

        mock_ai_generator.generate_response(query="Test")

        call_kwargs = mock_ai_generator.client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-20250514"

    def test_uses_configured_max_tokens(self, mock_ai_generator, mock_text_response):
        """Uses configured max_tokens"""
        mock_ai_generator.client.messages.create = Mock(
            return_value=mock_text_response("Test")
        )

        mock_ai_generator.generate_response(query="Test")

        call_kwargs = mock_ai_generator.client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 800

    def test_tool_choice_auto_when_tools_provided(self, mock_ai_generator, mock_text_response, tool_manager):
        """Sets tool_choice to auto when tools are provided"""
        mock_ai_generator.client.messages.create = Mock(
            return_value=mock_text_response("Test")
        )

        mock_ai_generator.generate_response(
            query="Test",
            tools=tool_manager.get_tool_definitions()
        )

        call_kwargs = mock_ai_generator.client.messages.create.call_args[1]
        assert call_kwargs["tool_choice"] == {"type": "auto"}
