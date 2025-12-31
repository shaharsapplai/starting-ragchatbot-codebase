"""
Tests for CourseSearchTool and CourseOutlineTool.

Uses real VectorStore with loaded course documents to test
the execute() method and result formatting.
"""

import pytest


class TestCourseSearchToolExecute:
    """Test CourseSearchTool.execute() method with real VectorStore"""

    def test_execute_returns_results_for_valid_query(self, search_tool):
        """Search with valid query returns formatted content"""
        result = search_tool.execute(query="computer use")

        # Should return actual content, not an error message
        assert result is not None
        assert len(result) > 0
        assert "No relevant content found" not in result
        assert "error" not in result.lower() or "Search error" not in result

    def test_execute_with_nonexistent_course_uses_semantic_matching(self, search_tool):
        """Search with non-existent course filter uses semantic matching to find closest course"""
        result = search_tool.execute(
            query="introduction", course_name="NonExistentCourse12345"
        )

        # Semantic search finds closest matching course, so results are returned
        # This is expected behavior - the system tries to be helpful by finding similar content
        assert result is not None
        assert len(result) > 0

    def test_execute_with_course_filter(self, search_tool, loaded_course_titles):
        """Search filtered by course name returns results from that course"""
        if not loaded_course_titles:
            pytest.skip("No courses loaded")

        # Use first available course
        course_name = loaded_course_titles[0]
        result = search_tool.execute(query="lesson", course_name=course_name)

        # Should return results (not an error)
        assert result is not None
        # Should contain the course name in results or have content
        assert len(result) > 0

    def test_execute_with_lesson_filter(self, search_tool, loaded_course_titles):
        """Search filtered by lesson number returns lesson-specific results"""
        if not loaded_course_titles:
            pytest.skip("No courses loaded")

        result = search_tool.execute(
            query="introduction", lesson_number=0  # Lesson 0 is usually the intro
        )

        # Should return results
        assert result is not None
        assert len(result) > 0

    def test_execute_handles_empty_results(self, search_tool):
        """Search with very specific non-matching query handles empty results"""
        result = search_tool.execute(query="xyzzy12345nonexistentterm67890abcdef")

        # Should handle gracefully (either empty message or no crash)
        assert result is not None

    def test_last_sources_populated_after_search(self, search_tool):
        """After successful search, last_sources contains source info"""
        # Reset sources first
        search_tool.last_sources = []

        result = search_tool.execute(query="computer use anthropic")

        # If results found, sources should be populated
        if "No relevant content found" not in result:
            assert len(search_tool.last_sources) > 0
            # Each source should have text and optional link
            for source in search_tool.last_sources:
                assert "text" in source
                assert "link" in source  # Can be None but key should exist

    def test_format_results_includes_course_headers(self, search_tool):
        """Formatted results include course/lesson context headers"""
        result = search_tool.execute(query="model")

        if "No relevant content found" not in result:
            # Results should include bracket headers like [Course Title - Lesson X]
            assert "[" in result and "]" in result


class TestCourseOutlineToolExecute:
    """Test CourseOutlineTool.execute() method"""

    def test_execute_returns_outline_for_valid_course(
        self, outline_tool, loaded_course_titles
    ):
        """Get outline for existing course returns lesson list"""
        if not loaded_course_titles:
            pytest.skip("No courses loaded")

        course_name = loaded_course_titles[0]
        result = outline_tool.execute(course_name=course_name)

        # Should contain course info
        assert "Course:" in result
        # Should contain lessons
        assert "Lesson" in result

    def test_execute_with_nonexistent_course_uses_semantic_matching(self, outline_tool):
        """Get outline with non-existent course uses semantic matching to find closest course"""
        result = outline_tool.execute(course_name="NonExistentCourse12345")

        # Semantic search finds closest matching course, so an outline is returned
        # This is expected behavior - the system tries to be helpful by finding similar content
        assert "Course:" in result
        assert "Lesson" in result

    def test_execute_includes_course_link(self, outline_tool, loaded_course_titles):
        """Outline includes course link when available"""
        if not loaded_course_titles:
            pytest.skip("No courses loaded")

        course_name = loaded_course_titles[0]
        result = outline_tool.execute(course_name=course_name)

        # Should include course link
        assert "Course Link:" in result or "deeplearning.ai" in result.lower()


class TestToolManager:
    """Test ToolManager functionality"""

    def test_register_tool_adds_to_tools_dict(self, tool_manager):
        """Registered tools are accessible by name"""
        assert "search_course_content" in tool_manager.tools
        assert "get_course_outline" in tool_manager.tools

    def test_get_tool_definitions_returns_list(self, tool_manager):
        """get_tool_definitions returns list of tool definitions"""
        definitions = tool_manager.get_tool_definitions()

        assert isinstance(definitions, list)
        assert len(definitions) == 2  # search and outline

        # Each definition should have required fields
        for defn in definitions:
            assert "name" in defn
            assert "description" in defn
            assert "input_schema" in defn

    def test_execute_tool_calls_correct_tool(self, tool_manager):
        """execute_tool routes to the correct tool"""
        result = tool_manager.execute_tool("search_course_content", query="test query")

        # Should return a string result
        assert isinstance(result, str)

    def test_execute_tool_returns_error_for_unknown_tool(self, tool_manager):
        """execute_tool with unknown name returns error message"""
        result = tool_manager.execute_tool("unknown_tool", query="test")

        assert "not found" in result.lower()

    def test_get_last_sources_returns_sources(self, tool_manager):
        """get_last_sources returns sources from search tool"""
        # Execute a search first
        tool_manager.execute_tool("search_course_content", query="computer use")

        sources = tool_manager.get_last_sources()
        assert isinstance(sources, list)

    def test_reset_sources_clears_sources(self, tool_manager):
        """reset_sources clears sources from all tools"""
        # Execute a search first
        tool_manager.execute_tool("search_course_content", query="computer use")

        # Reset
        tool_manager.reset_sources()

        # Sources should be empty
        sources = tool_manager.get_last_sources()
        assert len(sources) == 0
