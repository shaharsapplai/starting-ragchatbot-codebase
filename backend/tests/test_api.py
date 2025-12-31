"""
API endpoint tests for the RAG chatbot FastAPI application.

Tests the /api/query, /api/courses, and root endpoints using
a test app with mocked RAGSystem to avoid loading real documents
or making actual AI calls.

The test app is defined inline (in conftest.py fixtures) to avoid
import issues with static files that don't exist in the test environment.
"""
import pytest
from unittest.mock import Mock


@pytest.mark.api
class TestRootEndpoint:
    """Tests for the root (/) endpoint"""

    async def test_root_returns_ok_status(self, test_client):
        """Root endpoint returns status ok"""
        async with test_client as client:
            response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    async def test_root_returns_message(self, test_client):
        """Root endpoint returns informative message"""
        async with test_client as client:
            response = await client.get("/")

        data = response.json()
        assert "message" in data
        assert "RAG" in data["message"] or "running" in data["message"]


@pytest.mark.api
class TestHealthEndpoint:
    """Tests for the /health endpoint"""

    async def test_health_returns_healthy(self, test_client):
        """Health endpoint returns healthy status"""
        async with test_client as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.api
class TestQueryEndpoint:
    """Tests for the /api/query endpoint"""

    async def test_query_returns_200_on_success(self, test_client, sample_query_request):
        """Query endpoint returns 200 for valid request"""
        async with test_client as client:
            response = await client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200

    async def test_query_returns_answer_field(self, test_client, sample_query_request):
        """Query response includes answer field"""
        async with test_client as client:
            response = await client.post("/api/query", json=sample_query_request)

        data = response.json()
        assert "answer" in data
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0

    async def test_query_returns_sources_field(self, test_client, sample_query_request):
        """Query response includes sources field as list"""
        async with test_client as client:
            response = await client.post("/api/query", json=sample_query_request)

        data = response.json()
        assert "sources" in data
        assert isinstance(data["sources"], list)

    async def test_query_returns_session_id(self, test_client, sample_query_request):
        """Query response includes session_id"""
        async with test_client as client:
            response = await client.post("/api/query", json=sample_query_request)

        data = response.json()
        assert "session_id" in data
        assert isinstance(data["session_id"], str)
        assert len(data["session_id"]) > 0

    async def test_query_creates_session_when_not_provided(self, test_client):
        """New session is created when session_id is not provided"""
        request = {"query": "Test question", "session_id": None}

        async with test_client as client:
            response = await client.post("/api/query", json=request)

        data = response.json()
        assert data["session_id"] == "test-session-id"  # From mock

    async def test_query_uses_provided_session_id(self, test_client, sample_query_request_with_session):
        """Provided session_id is used in response"""
        async with test_client as client:
            response = await client.post("/api/query", json=sample_query_request_with_session)

        data = response.json()
        assert data["session_id"] == "existing-session-123"

    async def test_query_requires_query_field(self, test_client):
        """Request without query field returns 422"""
        invalid_request = {"session_id": "test"}

        async with test_client as client:
            response = await client.post("/api/query", json=invalid_request)

        assert response.status_code == 422

    async def test_query_rejects_empty_body(self, test_client):
        """Request with empty body returns 422"""
        async with test_client as client:
            response = await client.post("/api/query", json={})

        assert response.status_code == 422

    async def test_query_with_sources(self, client_with_sources):
        """Query that returns sources includes them in response"""
        request = {"query": "What is machine learning?"}

        async with client_with_sources as client:
            response = await client.post("/api/query", json=request)

        data = response.json()
        assert len(data["sources"]) == 2
        assert "ML Basics" in data["sources"][0]
        assert "AI Fundamentals" in data["sources"][1]

    async def test_query_handles_unicode(self, test_client):
        """Query handles unicode characters properly"""
        request = {"query": "What is 机器学习 (machine learning)?"}

        async with test_client as client:
            response = await client.post("/api/query", json=request)

        assert response.status_code == 200

    async def test_query_handles_long_query(self, test_client):
        """Query handles long input strings"""
        long_query = "Tell me about " + "machine learning " * 100
        request = {"query": long_query}

        async with test_client as client:
            response = await client.post("/api/query", json=request)

        assert response.status_code == 200


@pytest.mark.api
class TestQueryEndpointErrors:
    """Tests for error handling in /api/query endpoint"""

    async def test_query_returns_500_on_rag_error(self, client_with_errors):
        """Query returns 500 when RAGSystem raises exception"""
        request = {"query": "Test question"}

        async with client_with_errors as client:
            response = await client.post("/api/query", json=request)

        assert response.status_code == 500

    async def test_query_error_includes_detail(self, client_with_errors):
        """Error response includes detail message"""
        request = {"query": "Test question"}

        async with client_with_errors as client:
            response = await client.post("/api/query", json=request)

        data = response.json()
        assert "detail" in data
        assert "Database connection failed" in data["detail"]

    async def test_query_invalid_content_type(self, test_client):
        """Request with wrong content type returns error"""
        async with test_client as client:
            response = await client.post(
                "/api/query",
                content="query=test",
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

        assert response.status_code == 422


@pytest.mark.api
class TestCoursesEndpoint:
    """Tests for the /api/courses endpoint"""

    async def test_courses_returns_200(self, test_client):
        """Courses endpoint returns 200"""
        async with test_client as client:
            response = await client.get("/api/courses")

        assert response.status_code == 200

    async def test_courses_returns_total_courses(self, test_client):
        """Courses response includes total_courses count"""
        async with test_client as client:
            response = await client.get("/api/courses")

        data = response.json()
        assert "total_courses" in data
        assert isinstance(data["total_courses"], int)
        assert data["total_courses"] == 2  # From mock

    async def test_courses_returns_course_titles(self, test_client):
        """Courses response includes course_titles list"""
        async with test_client as client:
            response = await client.get("/api/courses")

        data = response.json()
        assert "course_titles" in data
        assert isinstance(data["course_titles"], list)
        assert len(data["course_titles"]) == 2
        assert "Test Course 1" in data["course_titles"]
        assert "Test Course 2" in data["course_titles"]

    async def test_courses_returns_500_on_error(self, client_with_errors):
        """Courses returns 500 when analytics fails"""
        async with client_with_errors as client:
            response = await client.get("/api/courses")

        assert response.status_code == 500

    async def test_courses_error_includes_detail(self, client_with_errors):
        """Courses error response includes detail"""
        async with client_with_errors as client:
            response = await client.get("/api/courses")

        data = response.json()
        assert "detail" in data
        assert "Analytics unavailable" in data["detail"]


@pytest.mark.api
class TestAPIContentTypes:
    """Tests for API content type handling"""

    async def test_query_accepts_json(self, test_client, sample_query_request):
        """Query endpoint accepts application/json"""
        async with test_client as client:
            response = await client.post(
                "/api/query",
                json=sample_query_request,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200

    async def test_query_returns_json(self, test_client, sample_query_request):
        """Query endpoint returns application/json"""
        async with test_client as client:
            response = await client.post("/api/query", json=sample_query_request)

        assert "application/json" in response.headers["content-type"]

    async def test_courses_returns_json(self, test_client):
        """Courses endpoint returns application/json"""
        async with test_client as client:
            response = await client.get("/api/courses")

        assert "application/json" in response.headers["content-type"]


@pytest.mark.api
class TestAPIMethodHandling:
    """Tests for HTTP method handling"""

    async def test_query_rejects_get(self, test_client):
        """Query endpoint rejects GET requests"""
        async with test_client as client:
            response = await client.get("/api/query")

        assert response.status_code == 405

    async def test_courses_rejects_post(self, test_client):
        """Courses endpoint rejects POST requests"""
        async with test_client as client:
            response = await client.post("/api/courses", json={})

        assert response.status_code == 405

    async def test_query_rejects_put(self, test_client):
        """Query endpoint rejects PUT requests"""
        async with test_client as client:
            response = await client.put("/api/query", json={"query": "test"})

        assert response.status_code == 405

    async def test_query_rejects_delete(self, test_client):
        """Query endpoint rejects DELETE requests"""
        async with test_client as client:
            response = await client.delete("/api/query")

        assert response.status_code == 405


@pytest.mark.api
class TestAPIResponseSchema:
    """Tests for API response schema validation"""

    async def test_query_response_has_all_required_fields(self, test_client, sample_query_request):
        """Query response contains all required fields"""
        async with test_client as client:
            response = await client.post("/api/query", json=sample_query_request)

        data = response.json()
        required_fields = ["answer", "sources", "session_id"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    async def test_courses_response_has_all_required_fields(self, test_client):
        """Courses response contains all required fields"""
        async with test_client as client:
            response = await client.get("/api/courses")

        data = response.json()
        required_fields = ["total_courses", "course_titles"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    async def test_query_sources_are_strings(self, client_with_sources):
        """Query sources are converted to strings"""
        request = {"query": "test"}

        async with client_with_sources as client:
            response = await client.post("/api/query", json=request)

        data = response.json()
        for source in data["sources"]:
            assert isinstance(source, str)


@pytest.mark.api
class TestSessionHandling:
    """Tests for session management in API"""

    async def test_different_requests_can_use_same_session(self, test_client):
        """Multiple requests can share the same session_id"""
        session_id = "shared-session"

        async with test_client as client:
            response1 = await client.post(
                "/api/query",
                json={"query": "First question", "session_id": session_id}
            )
            response2 = await client.post(
                "/api/query",
                json={"query": "Second question", "session_id": session_id}
            )

        assert response1.json()["session_id"] == session_id
        assert response2.json()["session_id"] == session_id

    async def test_null_session_id_creates_new_session(self, test_client):
        """Null session_id triggers session creation"""
        async with test_client as client:
            response = await client.post(
                "/api/query",
                json={"query": "Question", "session_id": None}
            )

        data = response.json()
        assert data["session_id"] is not None
        assert len(data["session_id"]) > 0
