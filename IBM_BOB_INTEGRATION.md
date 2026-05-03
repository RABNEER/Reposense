# IBM Bob Integration Guide 🤖

This document explains how RepoSense integrates with IBM Bob and showcases its multi-mode capabilities.

## Overview

RepoSense uses **IBM Bob's four operational modes** to provide comprehensive repository analysis:

1. **📝 Plan Mode** - Strategic analysis and planning
2. **❓ Ask Mode** - Question answering and explanations
3. **💻 Code Mode** - Code generation and modifications
4. **🔀 Orchestrator Mode** - Multi-step workflow coordination

## Architecture

```
┌─────────────────┐
│   GitHub API    │
│  (Repo Data)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ GitHub Parser   │
│ (Extract Context)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Prompt Engine   │
│ (Build Prompts) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   IBM Bob API   │
│  (AI Analysis)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI Routes │
│ (Return Results)│
└─────────────────┘
```

## Mode 1: Plan Mode 📝

**Purpose**: Analyze repository structure and create strategic onboarding guides.

### Use Cases in RepoSense

1. **Repository Analysis** (`POST /api/v1/analyze`)
   - Analyzes entire repository structure
   - Identifies tech stack and architecture
   - Creates onboarding roadmap

2. **Documentation Generation** (`POST /api/v1/export/markdown`)
   - Generates comprehensive Markdown docs
   - Structures information logically
   - Provides actionable guidance

### Implementation

```python
# backend/services/bob_client.py
async def analyze_repository(self, prompt: str) -> dict:
    """
    Analyze repository using Plan mode
    """
    response = await self._make_request(
        prompt, 
        mode="plan", 
        max_tokens=4000
    )
    return json.loads(response)
```

### Prompt Structure

```python
# backend/services/prompt_engine.py
def build_analysis_prompt(repo_context: dict) -> str:
    """
    Constructs prompt for repository analysis
    
    Includes:
    - Repository metadata (name, description, stars, language)
    - Directory structure (key folders)
    - Key file contents (README, package.json, main files)
    
    Requests:
    - Project summary
    - Tech stack identification
    - Architecture analysis
    - Key files prioritization
    - Data flow mapping
    - Onboarding steps
    - Quick win opportunities
    - Important gotchas
    """
```

### Example Response

```json
{
  "project_name": "FastAPI",
  "one_line_summary": "Modern, fast web framework for building APIs with Python",
  "tech_stack": [
    {"name": "Python", "color": "#3776ab", "category": "language"},
    {"name": "Starlette", "color": "#009688", "category": "framework"}
  ],
  "architecture_type": "ASGI Web Framework",
  "key_files": [
    {
      "path": "fastapi/main.py",
      "why_important": "Core FastAPI class definition",
      "read_order": 1
    }
  ],
  "onboarding_steps": [
    {
      "step": 1,
      "action": "Read the main FastAPI class",
      "why": "Understand the framework's core API"
    }
  ]
}
```

## Mode 2: Ask Mode ❓

**Purpose**: Answer questions about the codebase with context and references.

### Use Cases in RepoSense

1. **Q&A Chat** (`POST /api/v1/ask`)
   - Answers developer questions
   - Provides file references
   - Shows relevant code snippets
   - Maintains conversation context

### Implementation

```python
# backend/services/bob_client.py
async def answer_question(self, prompt: str) -> dict:
    """
    Answer question using Ask mode
    """
    response = await self._make_request(
        prompt,
        mode="ask",
        max_tokens=2000
    )
    return json.loads(response)
```

### Prompt Structure

```python
# backend/services/prompt_engine.py
def build_qa_prompt(repo_context: dict, question: str, chat_history: list) -> str:
    """
    Constructs Q&A prompt with context
    
    Includes:
    - Full repository context
    - Previous conversation history (last 5 messages)
    - User's current question
    
    Requests:
    - Detailed answer with file references
    - Relevant code snippets with line numbers
    - Clear explanations
    """
```

### Example Response

```json
{
  "answer": "Authentication is handled by the `auth.py` middleware. It uses JWT tokens stored in HTTP-only cookies. The `verify_token()` function validates tokens on each request.",
  "files_referenced": [
    "src/middleware/auth.py",
    "src/utils/jwt.py"
  ],
  "code_snippets": [
    {
      "file": "src/middleware/auth.py",
      "code": "@app.middleware('http')\nasync def auth_middleware(request, call_next):\n    token = request.cookies.get('auth_token')\n    if token:\n        user = await verify_token(token)\n        request.state.user = user\n    return await call_next(request)",
      "line_start": 15,
      "line_end": 21
    }
  ]
}
```

## Mode 3: Code Mode 💻

**Purpose**: Generate implementation code and modifications.

### Use Cases in RepoSense

1. **Task Kickstarter** (`POST /api/v1/task`)
   - Generates implementation code
   - Creates code diffs
   - Provides file modifications

### Implementation

```python
# backend/services/bob_client.py
async def generate_code(self, prompt: str) -> dict:
    """
    Generate code using Code mode
    """
    response = await self._make_request(
        prompt,
        mode="code",
        max_tokens=3000
    )
    return json.loads(response)
```

### Prompt Structure

```python
# backend/services/prompt_engine.py
def build_code_prompt(repo_context: dict, issue: dict, plan: dict) -> str:
    """
    Constructs code generation prompt
    
    Includes:
    - Repository context
    - Issue description
    - Implementation plan
    
    Requests:
    - Code changes with diffs
    - File modifications
    - Explanations for each change
    """
```

### Example Response

```json
{
  "changes": [
    {
      "file": "src/api/users.py",
      "change_type": "modify",
      "diff_lines": [
        {"type": "context", "content": "from fastapi import APIRouter", "line_num": 1},
        {"type": "add", "content": "from pydantic import ValidationError", "line_num": 2},
        {"type": "context", "content": "", "line_num": 3},
        {"type": "add", "content": "    if not user.email:", "line_num": 15},
        {"type": "add", "content": "        raise HTTPException(400, 'Email required')", "line_num": 16}
      ],
      "explanation": "Added email validation to user creation endpoint"
    }
  ]
}
```

## Mode 4: Orchestrator Mode 🔀

**Purpose**: Coordinate multi-step workflows across different modes.

### Use Cases in RepoSense

1. **Full Task Workflow** (`POST /api/v1/task`)
   - Finds beginner-friendly issues (Ask Mode)
   - Creates implementation plan (Plan Mode)
   - Generates code (Code Mode)
   - Explains to junior developer (Ask Mode)

### Implementation

```python
# backend/routers/task.py
async def kickstart_task(request: TaskRequest) -> CodingResponse:
    """
    Orchestrates full coding workflow
    """
    # Step 1: Find issue (Ask Mode)
    issue = await bob_client.answer_question(issue_prompt)
    
    # Step 2: Create plan (Plan Mode)
    plan = await bob_client.analyze_repository(plan_prompt)
    
    # Step 3: Generate code (Code Mode)
    code = await bob_client.generate_code(code_prompt)
    
    # Step 4: Explain (Ask Mode)
    explanation = await bob_client.answer_question(explain_prompt)
    
    return CodingResponse(
        issue=issue,
        plan=plan,
        code=code,
        explanation=explanation,
        bob_modes_used=["Ask", "Plan", "Code", "Ask"]
    )
```

### Workflow Diagram

```
User Task Request
       │
       ▼
┌──────────────┐
│  Ask Mode    │ ──► Find beginner-friendly issue
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Plan Mode   │ ──► Create implementation plan
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Code Mode   │ ──► Generate code changes
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Ask Mode    │ ──► Explain to junior developer
└──────┬───────┘
       │
       ▼
  Complete Response
```

## API Configuration

### Environment Variables

```bash
# Required
IBM_BOB_API_KEY=your_api_key_here
IBM_BOB_API_URL=https://bob-api.ibm.com

# Optional
IBM_BOB_TIMEOUT=60          # Request timeout in seconds
IBM_BOB_MAX_RETRIES=3       # Number of retry attempts
```

### Mock Mode for Development

```bash
# Use mock mode without real API key
IBM_BOB_API_KEY=mock
```

Mock mode provides realistic sample responses for all modes, perfect for:
- Frontend development
- Testing
- Demos
- Development without API access

## Error Handling

### Retry Logic

```python
# backend/services/bob_client.py
async def _make_request(self, prompt: str, mode: str) -> str:
    """
    Makes request with automatic retry on failure
    """
    for attempt in range(self.max_retries):
        try:
            response = await client.post(...)
            if response.status_code == 200:
                return response.json()["content"]
            elif response.status_code == 429:
                # Rate limit - exponential backoff
                await asyncio.sleep(2 ** attempt)
                continue
        except httpx.TimeoutException:
            if attempt < self.max_retries - 1:
                await asyncio.sleep(1)
                continue
    raise BobAPIError("Max retries exceeded")
```

### Error Types

```python
class BobClientError(Exception):
    """Base exception for Bob client errors"""

class BobAPIError(BobClientError):
    """Error from Bob API"""

class BobTimeoutError(BobClientError):
    """Request to Bob timed out"""
```

## Performance Optimization

### Caching Strategy

```python
# Repository context cached for 5 minutes
# Reduces GitHub API calls and speeds up subsequent requests
cache = TTLCache(maxsize=100, ttl=300)

@cached(cache)
async def fetch_repo_context(github_url: str) -> dict:
    """Cached repository context fetching"""
```

### Async Operations

All Bob API calls are asynchronous:
```python
# Multiple requests can run concurrently
results = await asyncio.gather(
    bob_client.analyze_repository(prompt1),
    bob_client.answer_question(prompt2),
    bob_client.generate_code(prompt3)
)
```

## Monitoring and Logging

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

# Log all Bob API interactions
logger.info(
    "bob_api_request",
    mode="plan",
    prompt_length=len(prompt),
    attempt=1
)

logger.info(
    "bob_api_success",
    mode="plan",
    response_length=len(response),
    duration_ms=duration
)
```

### Metrics Tracked

- Request count by mode
- Response times
- Error rates
- Retry attempts
- Token usage

## Best Practices

### 1. Prompt Engineering

✅ **Do:**
- Provide complete repository context
- Use clear, specific instructions
- Request structured JSON responses
- Include examples in prompts

❌ **Don't:**
- Send incomplete context
- Use vague instructions
- Expect unstructured responses
- Omit error handling

### 2. Mode Selection

- **Plan Mode**: Strategic analysis, documentation
- **Ask Mode**: Questions, explanations, clarifications
- **Code Mode**: Implementation, modifications
- **Orchestrator Mode**: Multi-step workflows

### 3. Error Handling

```python
try:
    result = await bob_client.analyze_repository(prompt)
except BobTimeoutError:
    # Handle timeout - maybe retry with shorter prompt
    pass
except BobAPIError as e:
    # Handle API error - log and return user-friendly message
    logger.error("bob_api_error", error=str(e))
    raise HTTPException(503, "AI service temporarily unavailable")
```

## Testing

### Unit Tests

```python
# tests/test_bob_client.py
@pytest.mark.asyncio
async def test_analyze_repository_mock_mode():
    """Test analysis in mock mode"""
    client = BobClient()
    result = await client.analyze_repository(prompt)
    assert result["project_name"]
    assert result["tech_stack"]
```

### Integration Tests

```python
# tests/test_integration.py
@pytest.mark.asyncio
async def test_full_workflow():
    """Test complete analysis workflow"""
    response = await client.post(
        "/api/v1/analyze",
        json={"github_url": "https://github.com/test/repo"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"]
    assert "Plan" in data["bob_modes_used"]
```

## Hackathon Demonstration

### Key Points to Highlight

1. **Multi-Mode Usage**: Shows all 4 Bob modes in action
2. **Real-World Application**: Solves actual developer pain point
3. **Production-Ready**: Error handling, retries, logging
4. **Mock Mode**: Easy to demo without API keys
5. **Clear Integration**: Well-documented API usage

### Demo Script

1. Show repository analysis (Plan Mode)
2. Ask questions about code (Ask Mode)
3. Generate task implementation (Code Mode)
4. Show full workflow (Orchestrator Mode)
5. Highlight mode transitions in UI

## Resources

- **IBM Bob Documentation**: [Link to Bob docs]
- **API Reference**: http://localhost:8000/docs
- **Source Code**: `backend/services/bob_client.py`
- **Prompt Templates**: `backend/services/prompt_engine.py`

---

Built with ❤️ for IBM Bob Hackathon 2024