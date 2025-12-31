"""
Diagnostic tests to identify the root cause of 'query failed' errors.

These tests check for common configuration and runtime issues.
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config


class TestConfiguration:
    """Test configuration settings"""

    def test_anthropic_api_key_is_set(self):
        """CRITICAL: API key must be set for queries to work"""
        api_key = config.ANTHROPIC_API_KEY

        assert api_key is not None, "ANTHROPIC_API_KEY is None"
        assert api_key != "", "ANTHROPIC_API_KEY is empty string"
        assert len(api_key) > 10, f"ANTHROPIC_API_KEY looks invalid (length: {len(api_key)})"
        # Most Anthropic keys start with 'sk-ant-'
        if not api_key.startswith('sk-ant-'):
            pytest.warns(UserWarning, "API key doesn't start with 'sk-ant-' - may be invalid")

    def test_chroma_path_exists_or_creatable(self):
        """ChromaDB path should be accessible"""
        chroma_path = config.CHROMA_PATH

        # Either exists or parent directory exists
        if os.path.exists(chroma_path):
            assert os.path.isdir(chroma_path), f"{chroma_path} exists but is not a directory"
        else:
            parent = os.path.dirname(chroma_path) or "."
            assert os.path.exists(parent), f"Parent directory {parent} doesn't exist"
            assert os.access(parent, os.W_OK), f"Parent directory {parent} is not writable"


class TestDocumentsLoaded:
    """Test that documents are properly loaded"""

    def test_docs_folder_exists(self):
        """docs/ folder should exist"""
        docs_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "docs"
        )
        assert os.path.exists(docs_path), f"docs folder not found at {docs_path}"
        assert os.path.isdir(docs_path), f"{docs_path} is not a directory"

    def test_docs_folder_has_documents(self):
        """docs/ folder should contain course documents"""
        docs_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "docs"
        )

        if not os.path.exists(docs_path):
            pytest.skip("docs folder doesn't exist")

        files = [f for f in os.listdir(docs_path) if f.endswith('.txt')]
        assert len(files) > 0, "No .txt files found in docs folder"

    def test_vector_store_has_content(self, loaded_vector_store):
        """Vector store should have courses loaded"""
        course_count = loaded_vector_store.get_course_count()
        assert course_count > 0, "No courses in vector store - documents may not be loaded"

        titles = loaded_vector_store.get_existing_course_titles()
        assert len(titles) > 0, "No course titles found in vector store"


class TestAnthropicAPIConnection:
    """Test actual connection to Anthropic API"""

    def test_anthropic_api_reachable(self):
        """Test that we can reach the Anthropic API (requires valid key)"""
        import anthropic

        api_key = config.ANTHROPIC_API_KEY
        if not api_key or api_key == "test-api-key":
            pytest.skip("No valid API key configured")

        try:
            client = anthropic.Anthropic(api_key=api_key)
            # Make a minimal API call
            response = client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            assert response is not None
            assert response.content is not None
        except anthropic.AuthenticationError:
            pytest.fail("ANTHROPIC_API_KEY is invalid - authentication failed")
        except anthropic.APIConnectionError:
            pytest.fail("Cannot connect to Anthropic API - network issue")
        except Exception as e:
            pytest.fail(f"Unexpected error connecting to Anthropic: {type(e).__name__}: {e}")
