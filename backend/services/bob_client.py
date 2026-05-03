"""
IBM Bob API Client
Handles all interactions with IBM Bob's API
Supports mock mode for development
"""
import asyncio
import json
import time
from typing import Optional, Any
import httpx
import structlog

from backend.config import Config

logger = structlog.get_logger()


class BobClientError(Exception):
    """Base exception for Bob client errors"""
    pass


class BobAPIError(BobClientError):
    """Error from Bob API"""
    pass


class BobTimeoutError(BobClientError):
    """Request to Bob timed out"""
    pass


class BobClient:
    """
    Client for IBM Bob API
    Handles authentication, retries, and error handling
    """
    
    def __init__(self):
        self.api_key = Config.IBM_BOB_API_KEY
        self.api_url = Config.IBM_BOB_API_URL
        self.timeout = Config.IBM_BOB_TIMEOUT
        self.max_retries = Config.IBM_BOB_MAX_RETRIES
        self.is_mock = Config.is_mock_mode()
        
        if self.is_mock:
            logger.info("bob_client_initialized", mode="mock")
        else:
            logger.info("bob_client_initialized", mode="production", api_url=self.api_url)
    
    async def _make_request(
        self,
        prompt: str,
        mode: str = "ask",
        max_tokens: int = 4000,
        temperature: float = 0.7
    ) -> str:
        """
        Make request to Bob API with retry logic
        
        Args:
            prompt: The prompt to send
            mode: Bob mode (ask, plan, code, orchestrator)
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0-1)
            
        Returns:
            Response text from Bob
            
        Raises:
            BobAPIError: If API returns error
            BobTimeoutError: If request times out
        """
        if self.is_mock:
            return self._mock_response(prompt, mode)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "mode": mode,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.info(
                        "bob_api_request",
                        attempt=attempt + 1,
                        mode=mode,
                        prompt_length=len(prompt)
                    )
                    
                    response = await client.post(
                        f"{self.api_url}/chat",
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result.get("response", result.get("content", ""))
                        
                        logger.info(
                            "bob_api_success",
                            mode=mode,
                            response_length=len(content)
                        )
                        
                        return content
                    
                    elif response.status_code == 429:
                        # Rate limit - wait and retry
                        wait_time = 2 ** attempt
                        logger.warning(
                            "bob_api_rate_limit",
                            attempt=attempt + 1,
                            wait_seconds=wait_time
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    
                    else:
                        error_msg = response.text
                        logger.error(
                            "bob_api_error",
                            status_code=response.status_code,
                            error=error_msg
                        )
                        raise BobAPIError(f"Bob API error: {response.status_code} - {error_msg}")
            
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    "bob_api_timeout",
                    attempt=attempt + 1,
                    timeout=self.timeout
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            
            except httpx.RequestError as e:
                last_error = e
                logger.error("bob_api_request_error", error=str(e), attempt=attempt + 1)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
        
        # All retries failed
        if isinstance(last_error, httpx.TimeoutException):
            raise BobTimeoutError(f"Bob API timeout after {self.max_retries} attempts")
        else:
            raise BobAPIError(f"Bob API request failed after {self.max_retries} attempts: {last_error}")
    
    def _mock_response(self, prompt: str, mode: str) -> str:
        """
        Generate mock response for development
        
        Args:
            prompt: The prompt (analyzed for context)
            mode: Bob mode
            
        Returns:
            Mock JSON response appropriate for the mode
        """
        logger.info("bob_mock_response", mode=mode, prompt_length=len(prompt))
        
        # Simulate API delay
        time.sleep(0.5)
        
        if mode == "plan" or "analysis" in prompt.lower():
            return json.dumps({
                "project_name": "Example Project",
                "one_line_summary": "A modern web application built with React and FastAPI",
                "what_it_does": "This project provides a full-stack web application template with authentication, API integration, and responsive UI. It demonstrates best practices for building scalable web applications.",
                "tech_stack": [
                    {"name": "JavaScript", "color": "#f5a623", "category": "language"},
                    {"name": "Python", "color": "#3776ab", "category": "language"},
                    {"name": "React", "color": "#61dafb", "category": "framework"},
                    {"name": "FastAPI", "color": "#009688", "category": "framework"},
                    {"name": "PostgreSQL", "color": "#336791", "category": "database"}
                ],
                "architecture_type": "Client-Server with REST API",
                "architecture_overview": "The application follows a modern client-server architecture. The frontend is a React SPA that communicates with a FastAPI backend via REST API. The backend handles business logic, database operations, and external API integrations. State management on the frontend uses React hooks and context.",
                "folder_structure": [
                    {"path": "frontend/src/", "purpose": "React application source code", "importance": "critical"},
                    {"path": "backend/", "purpose": "FastAPI server and business logic", "importance": "critical"},
                    {"path": "tests/", "purpose": "Unit and integration tests", "importance": "important"},
                    {"path": "docs/", "purpose": "Project documentation", "importance": "helpful"}
                ],
                "key_files": [
                    {
                        "path": "README.md",
                        "why_important": "Project overview and setup instructions",
                        "read_order": 1,
                        "importance": "critical"
                    },
                    {
                        "path": "backend/main.py",
                        "why_important": "FastAPI application entry point and route definitions",
                        "read_order": 2,
                        "importance": "critical"
                    },
                    {
                        "path": "frontend/src/App.jsx",
                        "why_important": "React application root component and routing",
                        "read_order": 3,
                        "importance": "critical"
                    },
                    {
                        "path": "backend/config.py",
                        "why_important": "Configuration management and environment variables",
                        "read_order": 4,
                        "importance": "important"
                    }
                ],
                "data_flow": [
                    {"step": 1, "description": "User interacts with React frontend"},
                    {"step": 2, "description": "Frontend makes HTTP request to FastAPI backend"},
                    {"step": 3, "description": "Backend validates request and processes business logic"},
                    {"step": 4, "description": "Backend queries database if needed"},
                    {"step": 5, "description": "Backend returns JSON response to frontend"},
                    {"step": 6, "description": "Frontend updates UI based on response"}
                ],
                "onboarding_steps": [
                    {
                        "step": 1,
                        "action": "Clone repository and review README",
                        "why": "Understand project purpose and requirements",
                        "code_ref": "git clone <repo-url>"
                    },
                    {
                        "step": 2,
                        "action": "Set up backend environment",
                        "why": "Install Python dependencies and configure environment",
                        "code_ref": "cd backend && pip install -r requirements.txt"
                    },
                    {
                        "step": 3,
                        "action": "Set up frontend environment",
                        "why": "Install Node.js dependencies",
                        "code_ref": "cd frontend && npm install"
                    },
                    {
                        "step": 4,
                        "action": "Start development servers",
                        "why": "Run application locally for testing",
                        "code_ref": "npm run dev (frontend) and uvicorn main:app --reload (backend)"
                    }
                ],
                "quick_wins": [
                    {
                        "title": "Add loading states to API calls",
                        "description": "Improve UX by showing loading indicators during async operations",
                        "files": ["frontend/src/components/DataTable.jsx"],
                        "complexity": "simple",
                        "impact": "medium"
                    },
                    {
                        "title": "Add input validation",
                        "description": "Validate user inputs on the frontend before API calls",
                        "files": ["frontend/src/components/Form.jsx"],
                        "complexity": "simple",
                        "impact": "high"
                    }
                ],
                "gotchas": [
                    "Environment variables must be set before running the application",
                    "Database migrations need to be run manually after pulling updates",
                    "CORS is configured for localhost:3000 only in development"
                ],
                "estimated_onboarding_minutes": 45,
                "bob_modes_used": ["Plan"]
            })
        
        elif mode == "ask" or "question" in prompt.lower():
            return json.dumps({
                "answer": "Based on the repository structure, this appears to be a full-stack web application. The frontend uses React with modern hooks and component patterns. The backend is built with FastAPI, providing RESTful endpoints. The application follows a clear separation of concerns with dedicated directories for components, services, and utilities.",
                "files_referenced": ["frontend/src/App.jsx", "backend/main.py", "README.md"],
                "code_snippets": [
                    {
                        "file": "backend/main.py",
                        "code": "@app.get('/api/health')\nasync def health_check():\n    return {'status': 'healthy'}",
                        "line_start": 15,
                        "line_end": 18
                    }
                ]
            })
        
        elif mode == "code":
            return json.dumps({
                "changes": [
                    {
                        "file": "backend/api/routes.py",
                        "change_type": "modify",
                        "diff_lines": [
                            {"type": "context", "content": "from fastapi import APIRouter, HTTPException", "line_num": 1},
                            {"type": "add", "content": "from pydantic import ValidationError", "line_num": 2},
                            {"type": "context", "content": "", "line_num": 3},
                            {"type": "context", "content": "@router.post('/users')", "line_num": 10},
                            {"type": "context", "content": "async def create_user(user: UserCreate):", "line_num": 11},
                            {"type": "add", "content": "    try:", "line_num": 12},
                            {"type": "add", "content": "        validated_user = UserCreate(**user.dict())", "line_num": 13},
                            {"type": "add", "content": "    except ValidationError as e:", "line_num": 14},
                            {"type": "add", "content": "        raise HTTPException(status_code=400, detail=str(e))", "line_num": 15}
                        ],
                        "explanation": "Added validation error handling to user creation endpoint"
                    }
                ]
            })
        
        else:  # orchestrator or default
            return json.dumps({
                "issue_title": "Add error handling to API endpoints",
                "issue_description": "Several API endpoints lack proper error handling, which could lead to unclear error messages for users",
                "issue_files": ["backend/api/routes.py", "backend/api/users.py"],
                "complexity": "moderate",
                "impact": "high",
                "implementation_plan": [
                    "Review existing error handling patterns",
                    "Add try-catch blocks to endpoints",
                    "Create custom exception classes",
                    "Add error logging",
                    "Update API documentation"
                ],
                "code_changes": [
                    {
                        "file": "backend/api/routes.py",
                        "change_type": "modify",
                        "diff_lines": [
                            {"type": "add", "content": "from fastapi import HTTPException", "line_num": 1},
                            {"type": "add", "content": "import logging", "line_num": 2}
                        ],
                        "explanation": "Added necessary imports for error handling"
                    }
                ],
                "pr_title": "feat: Add comprehensive error handling to API endpoints",
                "pr_description": "This PR adds proper error handling to all API endpoints, improving error messages and logging.",
                "junior_explanation": "We added error handling to make the API more robust. When something goes wrong, users now get clear error messages instead of generic 500 errors.",
                "bob_modes_used": ["Plan", "Ask", "Code", "Ask"]
            })
    
    async def analyze_repository(self, prompt: str) -> dict:
        """
        Analyze repository using Plan mode
        
        Args:
            prompt: Analysis prompt with repo context
            
        Returns:
            Parsed analysis dictionary
        """
        response = await self._make_request(prompt, mode="plan", max_tokens=4000)
        
        try:
            # Remove markdown code fences if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
            
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("bob_response_parse_error", error=str(e), response=response[:200])
            raise BobAPIError(f"Failed to parse Bob response as JSON: {e}")
    
    async def answer_question(self, prompt: str) -> dict:
        """
        Answer question using Ask mode
        
        Args:
            prompt: Question prompt with repo context
            
        Returns:
            Parsed answer dictionary
        """
        response = await self._make_request(prompt, mode="ask", max_tokens=2000)
        
        try:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
            
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("bob_response_parse_error", error=str(e), response=response[:200])
            raise BobAPIError(f"Failed to parse Bob response as JSON: {e}")
    
    async def generate_code(self, prompt: str) -> dict:
        """
        Generate code using Code mode
        
        Args:
            prompt: Code generation prompt
            
        Returns:
            Parsed code changes dictionary
        """
        response = await self._make_request(prompt, mode="code", max_tokens=3000)
        
        try:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
            
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("bob_response_parse_error", error=str(e), response=response[:200])
            raise BobAPIError(f"Failed to parse Bob response as JSON: {e}")
    
    async def orchestrate_workflow(self, prompt: str) -> dict:
        """
        Run full workflow using Orchestrator mode
        
        Args:
            prompt: Orchestration prompt with repo context
            
        Returns:
            Parsed workflow result dictionary
        """
        response = await self._make_request(prompt, mode="orchestrator", max_tokens=5000)
        
        try:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
            
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("bob_response_parse_error", error=str(e), response=response[:200])
            raise BobAPIError(f"Failed to parse Bob response as JSON: {e}")
    
    async def generate_documentation(self, prompt: str) -> str:
        """
        Generate markdown documentation using Plan mode
        
        Args:
            prompt: Documentation prompt
            
        Returns:
            Raw markdown string
        """
        response = await self._make_request(prompt, mode="plan", max_tokens=4000, temperature=0.5)
        
        # Remove code fences if present
        cleaned = response.strip()
        if cleaned.startswith("```markdown"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
        elif cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
        
        return cleaned


# Global client instance
_bob_client: Optional[BobClient] = None


def get_bob_client() -> BobClient:
    """
    Get or create global Bob client instance
    
    Returns:
        BobClient instance
    """
    global _bob_client
    if _bob_client is None:
        _bob_client = BobClient()
    return _bob_client

# Made with Bob
