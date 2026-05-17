# Resilience Validation Integration Tests Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a robust, automated end-to-end resilience validation test suite in `backend/test_resilience.py` that verifies that the RepoSense FastAPI server successfully recovers using mock data when credentials (Watsonx or Groq) are invalid or when AI service calls fail/timeout.

**Architecture:** Use `fastapi.testclient.TestClient` against the main `app` to perform end-to-end tests. We will use standard `unittest.mock` patching to simulate credential availability, API timeouts, connection errors, and correct failover behaviors (Watsonx to Groq, and both to Mock Engine).

**Tech Stack:** Python 3, FastAPI, pytest, unittest.mock, asyncio

---

### Task 1: Create the Resilience Test Suite File and Implement Mode 1 & Mode 2 Validation Tests

Verify that empty or placeholder keys are correctly rejected, mock mode is activated, and endpoints successfully return correct mock structures on invalid keys.

**Files:**
- Create: `backend/test_resilience.py`

**Step 1: Write the failing test**

We will write `backend/test_resilience.py` containing key validation and mock fallback tests. Since the file does not exist, any run of it will fail.

```python
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import sys

# Fix Windows console encoding if needed
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from backend.server import app, FallbackToMockError
    from backend.bob_client import is_valid_key, get_ai_client
except ImportError:
    from server import app, FallbackToMockError
    from bob_client import is_valid_key, get_ai_client

client = TestClient(app)

def test_is_valid_key():
    """Verify is_valid_key logic rejects empty keys and standard placeholder strings"""
    assert is_valid_key("") is False
    assert is_valid_key("   ") is False
    assert is_valid_key("your_api_key") is False
    assert is_valid_key("placeholder_value") is False
    assert is_valid_key("project_id_placeholder") is False
    assert is_valid_key("my-real-secret-key-123") is True

def test_get_ai_client_mock_fallback():
    """Verify that get_ai_client returns None when environment keys are empty or invalid"""
    with patch.dict(os.environ, {
        "WATSONX_API_KEY": "your_api_key",
        "WATSONX_PROJECT_ID": "placeholder",
        "GROQ_API_KEY": "api_key"
    }):
        # Reloading or patching key constants
        with patch("backend.bob_client.WATSONX_API_KEY", ""), \
             patch("backend.bob_client.WATSONX_PROJECT_ID", ""), \
             patch("backend.bob_client.GROQ_API_KEY", ""):
            ai_client = get_ai_client()
            assert ai_client is None

def test_mode_1_mock_endpoints():
    """Verify that POST /api/analyze and POST /api/ask return 200 OK with mock data when no credentials exist"""
    # Ensure client is mock mode
    with patch("backend.server.is_mock_mode", return_value=True):
        # Test analyze endpoint
        response = client.post(
            "/api/analyze",
            json={"github_url": "https://github.com/facebook/react"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["project_name"] == "React"
        assert "what_it_does" in data
        assert len(data["tech_stack"]) > 0

        # Test ask endpoint
        response = client.post(
            "/api/ask",
            json={
                "github_url": "https://github.com/facebook/react",
                "question": "What is virtual DOM?",
                "history": []
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "answer" in data
        assert "virtual DOM" in data["answer"] or "React" in data["answer"]
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/test_resilience.py -v`
Expected: FAIL or error since the file is not yet created.

**Step 3: Write minimal implementation**

Create the file `backend/test_resilience.py` with the imports and the tests defined above.

**Step 4: Run test to verify it passes**

Run: `pytest backend/test_resilience.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/test_resilience.py
git commit -m "test: add mock mode and key rejection resilience tests"
```

---

### Task 2: Implement Mode 3 & Mode 4 Error/Timeout Fallback Resilience Tests

Implement tests verifying that if the primary Watsonx client fails or times out, the server attempts silent fallback to Groq. If both fail or time out, the server catches all routing exceptions and gracefully falls back to mock demo responses.

**Files:**
- Modify: `backend/test_resilience.py`

**Step 1: Write the failing test**

Add Mode 3 and Mode 4 test methods to `backend/test_resilience.py`:

```python
import asyncio

class MockWatsonxClient:
    """Mock Watsonx client to raise exceptions"""
    async def analyze(self, *args, **kwargs):
        raise RuntimeError("Watsonx Client connection timeout")
    
    async def ask(self, *args, **kwargs):
        raise RuntimeError("Watsonx Client failed")

class MockGroqClient:
    """Mock Groq client that succeeds"""
    async def analyze(self, *args, **kwargs):
        return {
            "project_name": "Groq-Analyzed React",
            "one_line_summary": "JavaScript library analyzed by Groq",
            "what_it_does": "React core onboarding guide fallback via Groq.",
            "tech_stack": [{"name": "JavaScript", "category": "language", "color": "#f5a623"}],
            "architecture_type": "Component-based",
            "folder_structure": [],
            "key_files": [],
            "data_flow": [],
            "onboarding_steps": [],
            "quick_wins": [],
            "gotchas": [],
            "estimated_onboarding_minutes": 30,
            "bob_modes_used": ["Plan"]
        }

def test_mode_3_watsonx_failover_to_groq():
    """Verify Watsonx failing with Groq fallback working yields Groq response"""
    primary_client = MockWatsonxClient()
    
    with patch("backend.server.get_configured_client", return_value=primary_client), \
         patch("backend.server.is_mock_mode", return_value=False), \
         patch("backend.server.is_valid_key", return_value=True), \
         patch("backend.server.os.getenv", return_value="dummy_groq_key"), \
         patch("backend.server.build_repo_context", return_value={"repo_name": "facebook/react"}), \
         patch("backend.groq_client.GroqClient", return_value=MockGroqClient()):
        
        response = client.post(
            "/api/analyze",
            json={"github_url": "https://github.com/facebook/react"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["project_name"] == "Groq-Analyzed React"
        assert "fallback" in response.text.lower() or "groq" in response.text.lower()

def test_mode_4_both_clients_fail_emergency_mock_fallback():
    """Verify that when both Watsonx and Groq fail, server recovers with 200 OK mock data"""
    primary_client = MockWatsonxClient()
    
    # We simulate both failing by providing an invalid/empty Groq key, forcing FallbackToMockError,
    # or by letting both raise runtime exceptions.
    with patch("backend.server.get_configured_client", return_value=primary_client), \
         patch("backend.server.is_mock_mode", return_value=False), \
         patch("backend.server.is_valid_key", return_value=False), \
         patch("backend.server.build_repo_context", return_value={"repo_name": "facebook/react"}):
         
        # Test analyze fallback
        response = client.post(
            "/api/analyze",
            json={"github_url": "https://github.com/facebook/react"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["project_name"] == "React" # Successfully recovered via get_mock_analyze_response
        
        # Test ask fallback
        response = client.post(
            "/api/ask",
            json={
                "github_url": "https://github.com/facebook/react",
                "question": "reconciliation",
                "history": []
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "answer" in data
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/test_resilience.py -v`
Expected: FAIL because these test functions are not yet in the file.

**Step 3: Write minimal implementation**

Append these test cases to `backend/test_resilience.py` and import/mock classes properly.

**Step 4: Run test to verify it passes**

Run: `pytest backend/test_resilience.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/test_resilience.py
git commit -m "test: add end-to-end failover and mock fallback resilience tests"
```
