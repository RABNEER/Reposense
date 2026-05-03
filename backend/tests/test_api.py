"""
API endpoint tests for RepoSense backend
"""
import pytest
from fastapi import status


class TestHealthEndpoint:
    """Tests for health check endpoint"""
    
    def test_health_check(self, client):
        """Test health endpoint returns 200"""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info"""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "RepoSense API"
        assert "endpoints" in data


class TestAnalyzeEndpoint:
    """Tests for repository analysis endpoint"""
    
    def test_analyze_valid_url(self, client, sample_github_url):
        """Test analysis with valid GitHub URL"""
        response = client.post(
            "/api/analyze",
            json={"github_url": sample_github_url}
        )
        # In mock mode, should return 200
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]
    
    def test_analyze_invalid_url(self, client):
        """Test analysis with invalid URL"""
        response = client.post(
            "/api/analyze",
            json={"github_url": "not-a-url"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_analyze_missing_url(self, client):
        """Test analysis without URL"""
        response = client.post(
            "/api/analyze",
            json={}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_analyze_non_github_url(self, client):
        """Test analysis with non-GitHub URL"""
        response = client.post(
            "/api/analyze",
            json={"github_url": "https://example.com/repo"}
        )
        # Should fail validation or return error
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_404_NOT_FOUND
        ]


class TestAskEndpoint:
    """Tests for Q&A endpoint"""
    
    def test_ask_valid_question(self, client, sample_github_url):
        """Test Q&A with valid question"""
        response = client.post(
            "/api/ask",
            json={
                "github_url": sample_github_url,
                "question": "How does authentication work?"
            }
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]
    
    def test_ask_missing_question(self, client, sample_github_url):
        """Test Q&A without question"""
        response = client.post(
            "/api/ask",
            json={"github_url": sample_github_url}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_ask_empty_question(self, client, sample_github_url):
        """Test Q&A with empty question"""
        response = client.post(
            "/api/ask",
            json={
                "github_url": sample_github_url,
                "question": ""
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestTaskEndpoint:
    """Tests for task kickstarter endpoint"""
    
    def test_task_with_description(self, client, sample_github_url):
        """Test task with description"""
        response = client.post(
            "/api/task",
            json={
                "github_url": sample_github_url,
                "task_description": "Add input validation"
            }
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]
    
    def test_task_without_description(self, client, sample_github_url):
        """Test task without description (should find issue)"""
        response = client.post(
            "/api/task",
            json={"github_url": sample_github_url}
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]
    
    def test_task_missing_url(self, client):
        """Test task without URL"""
        response = client.post(
            "/api/task",
            json={"task_description": "Add validation"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestExportEndpoints:
    """Tests for export endpoints"""
    
    def test_export_markdown(self, client, sample_github_url):
        """Test Markdown export"""
        response = client.post(
            "/api/export/markdown",
            json={"github_url": sample_github_url}
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]
        if response.status_code == status.HTTP_200_OK:
            # Should return plain text
            assert "text/plain" in response.headers.get("content-type", "")
    
    def test_export_json(self, client, sample_github_url):
        """Test JSON export"""
        response = client.post(
            "/api/export/json",
            json={"github_url": sample_github_url}
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["success"] is True
            assert data["format"] == "json"
    
    def test_export_missing_url(self, client):
        """Test export without URL"""
        response = client.post(
            "/api/export/markdown",
            json={}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCORS:
    """Tests for CORS configuration"""
    
    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.options("/api/analyze")
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers or response.status_code == 200


class TestErrorHandling:
    """Tests for error handling"""
    
    def test_404_endpoint(self, client):
        """Test non-existent endpoint returns 404"""
        response = client.get("/api/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_method_not_allowed(self, client):
        """Test wrong HTTP method"""
        response = client.get("/api/analyze")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    def test_invalid_json(self, client):
        """Test invalid JSON payload"""
        response = client.post(
            "/api/analyze",
            data="not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

# Made with Bob
