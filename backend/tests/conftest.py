"""
Pytest configuration and fixtures for RepoSense backend tests
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.bob_client import BobClient
from backend.config import Config


@pytest.fixture
def client():
    """
    FastAPI test client fixture
    """
    return TestClient(app)


@pytest.fixture
def mock_bob_client(monkeypatch):
    """
    Mock Bob client for testing without real API calls
    """
    # Force mock mode
    monkeypatch.setattr(Config, "IBM_BOB_API_KEY", "mock")
    return BobClient()


@pytest.fixture
def sample_github_url():
    """
    Sample GitHub repository URL for testing
    """
    return "https://github.com/facebook/react"


@pytest.fixture
def sample_repo_context():
    """
    Sample repository context for testing
    """
    return {
        "metadata": {
            "full_name": "facebook/react",
            "description": "A declarative, efficient, and flexible JavaScript library",
            "stars": 200000,
            "language": "JavaScript",
            "license": "MIT",
            "topics": ["react", "javascript", "ui", "framework"]
        },
        "file_count": 1500,
        "directory_structure": [
            "packages/",
            "packages/react/",
            "packages/react-dom/",
            "scripts/",
            "fixtures/"
        ],
        "key_files": {
            "README.md": "# React\n\nA JavaScript library for building user interfaces",
            "package.json": '{"name": "react", "version": "18.0.0"}',
            "packages/react/index.js": "export * from './src/React';"
        }
    }


@pytest.fixture
def sample_analysis_response():
    """
    Sample analysis response from Bob
    """
    return {
        "project_name": "React",
        "one_line_summary": "A JavaScript library for building user interfaces",
        "what_it_does": "React is a declarative, efficient, and flexible JavaScript library for building user interfaces.",
        "tech_stack": [
            {"name": "JavaScript", "color": "#f5a623", "category": "language"},
            {"name": "Node.js", "color": "#22c98a", "category": "runtime"}
        ],
        "architecture_type": "Component-based UI Library",
        "architecture_overview": "React uses a component-based architecture...",
        "folder_structure": [
            {"path": "packages/", "purpose": "Core packages", "importance": "critical"},
            {"path": "scripts/", "purpose": "Build scripts", "importance": "important"}
        ],
        "key_files": [
            {
                "path": "packages/react/index.js",
                "why_important": "Main entry point",
                "read_order": 1,
                "importance": "critical"
            }
        ],
        "data_flow": [
            {"step": 1, "description": "Component renders"},
            {"step": 2, "description": "Virtual DOM updates"}
        ],
        "onboarding_steps": [
            {
                "step": 1,
                "action": "Read README.md",
                "why": "Understand project purpose",
                "code_ref": "README.md"
            }
        ],
        "quick_wins": [
            {
                "title": "Add PropTypes",
                "description": "Add type checking to components",
                "files": ["packages/react/src/Component.js"],
                "complexity": "simple",
                "impact": "medium"
            }
        ],
        "gotchas": [
            "Build process is complex",
            "Multiple package versions"
        ],
        "estimated_onboarding_minutes": 45,
        "bob_modes_used": ["Plan"]
    }


@pytest.fixture
def sample_qa_response():
    """
    Sample Q&A response from Bob
    """
    return {
        "answer": "React uses a virtual DOM to efficiently update the UI...",
        "files_referenced": ["packages/react-dom/src/client/ReactDOM.js"],
        "code_snippets": [
            {
                "file": "packages/react-dom/src/client/ReactDOM.js",
                "code": "function render(element, container) {\n  // Implementation\n}",
                "line_start": 10,
                "line_end": 12
            }
        ]
    }


@pytest.fixture
def sample_task_response():
    """
    Sample task response from Bob
    """
    return {
        "issue_title": "Add input validation",
        "issue_description": "Add validation to user input",
        "issue_files": ["src/components/Form.js"],
        "complexity": "simple",
        "impact": "high",
        "implementation_plan": [
            "Step 1: Add validation function",
            "Step 2: Apply to input handler"
        ],
        "code_changes": [
            {
                "file": "src/components/Form.js",
                "change_type": "modify",
                "diff_lines": [
                    {"type": "add", "content": "const validate = (value) => value.length > 0;", "line_num": 5}
                ],
                "explanation": "Added validation function"
            }
        ],
        "pr_title": "feat: Add input validation",
        "pr_description": "This PR adds input validation to the form component",
        "junior_explanation": "We added a validation function to check user input",
        "bob_modes_used": ["Ask", "Plan", "Code", "Ask"]
    }

# Made with Bob
