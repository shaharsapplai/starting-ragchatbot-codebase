from typing import Any, Dict, List, Optional

import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Maximum sequential tool-calling rounds per query
    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Tool Selection Guide:
- **get_course_outline**: Use when users ask about:
  - Course structure or organization
  - What lessons/topics a course covers
  - Course overview or table of contents
  - "What's in [course]?" or "What does [course] cover?"
  - List of lessons in a course

- **search_course_content**: Use when users ask about:
  - Specific content or concepts within course materials
  - Detailed information from lessons
  - "How does [topic] work?" or "Explain [concept]"

Multi-Step Tool Usage:
- You may call tools sequentially when needed to gather complete information
- After receiving tool results, evaluate if an additional search would help
- Use get_course_outline first if you need to understand course structure before searching
- Example: To compare topics across courses, first get outlines, then search specific content

Tool Usage Rules:
- For course overview questions, prefer get_course_outline
- For specific content questions, prefer search_course_content
- If tool yields no results, try an alternative search or state this clearly
- Do not make redundant tool calls with identical parameters

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course-specific questions**: Use appropriate tool first, then answer
- **No meta-commentary**: Provide direct answers only

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content,
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get response from Claude
        response = self.client.messages.create(**api_params)

        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(
                response, api_params, tool_manager, tools=tools
            )

        # Return direct response
        return self._extract_text_response(response.content)

    def _handle_tool_execution(
        self,
        initial_response,
        base_params: Dict[str, Any],
        tool_manager,
        tools: Optional[List] = None,
    ) -> str:
        """
        Handle execution of tool calls with support for multiple rounds.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            tools: Tool definitions for follow-up calls (enables multi-round)

        Returns:
            Final response text after tool execution rounds
        """
        messages = base_params["messages"].copy()
        current_response = initial_response
        round_count = 0

        while round_count < self.MAX_TOOL_ROUNDS:
            # Add assistant's tool use response
            messages.append({"role": "assistant", "content": current_response.content})

            # Execute all tool calls and collect results
            tool_results = self._execute_tool_calls(
                current_response.content, tool_manager
            )

            if not tool_results:
                # No tool calls found, extract text response
                return self._extract_text_response(current_response.content)

            # Add tool results as user message
            messages.append({"role": "user", "content": tool_results})

            # Prepare next API call
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
            }

            # Include tools for follow-up calls if we haven't reached max rounds
            if tools and round_count < self.MAX_TOOL_ROUNDS - 1:
                next_params["tools"] = tools
                next_params["tool_choice"] = {"type": "auto"}

            # Get next response
            current_response = self.client.messages.create(**next_params)

            # If Claude doesn't want more tools, we're done
            if current_response.stop_reason != "tool_use":
                return self._extract_text_response(current_response.content)

            round_count += 1

        # Max rounds reached - execute final tool calls and get response without tools
        messages.append({"role": "assistant", "content": current_response.content})
        tool_results = self._execute_tool_calls(current_response.content, tool_manager)

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"],
        }

        final_response = self.client.messages.create(**final_params)
        return self._extract_text_response(final_response.content)

    def _execute_tool_calls(self, content_blocks, tool_manager) -> List[Dict]:
        """Execute tool calls from response content and return results."""
        tool_results = []
        for content_block in content_blocks:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )
                except Exception as e:
                    tool_result = f"Error executing tool: {str(e)}"

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result,
                    }
                )
        return tool_results

    def _extract_text_response(self, content_blocks) -> str:
        """Extract text content from response content blocks."""
        for block in content_blocks:
            if hasattr(block, "text"):
                return block.text
        return ""
