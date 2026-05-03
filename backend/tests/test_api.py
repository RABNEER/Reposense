"""
API endpoint tests for RepoSense backend
Tests that can run in CI without real GitHub/Bob API access.
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
    
    def test_analyze_missing_url(self, client):
        """Test analysis without URL"""
        response = client.post(
            "/api/v1/analyze",
            json={}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAskEndpoint:
    """Tests for Q&A endpoint"""
    
    def test_ask_missing_question(self, client, sample_github_url):
        """Test Q&A without question"""
        response = client.post(
            "/api/v1/ask",
            json={"github_url": sample_github_url}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestTaskEndpoint:
    """Tests for task kickstarter endpoint"""
    
    def test_task_missing_url(self, client):
        """Test task without URL"""
        response = client.post(
            "/api/v1/task",
            json={"task_description": "Add validation"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestExportEndpoints:
    """Tests for export endpoints"""
    
    def test_export_missing_url(self, client):
        """Test export without URL"""
        response = client.post(
            "/api/v1/export/markdown",
            json={}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCORS:
    """Tests for CORS configuration"""
    
    def test_cors_headers(self, client):
        """Test CORS headers are present on preflight"""
        response = client.options(
            "/api/v1/analyze",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            }
        )
        assert response.status_code == 200


class TestErrorHandling:
    """Tests for error handling"""
    
    def test_404_endpoint(self, client):
        """Test non-existent endpoint returns 404"""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_method_not_allowed(self, client):
        """Test wrong HTTP method"""
        response = client.get("/api/v1/analyze")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    def test_invalid_json(self, client):
        """Test invalid JSON payload"""
        response = client.post(
            "/api/v1/analyze",
            data="not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

# Made with Bob
